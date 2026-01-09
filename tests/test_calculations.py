"""Tests for OlcaoCalculation."""

import os

from aiida.common import folders
from aiida.orm import SinglefileData, Str
from aiida.plugins import CalculationFactory, DataFactory

from . import TEST_DIR


def test_olcao_calculation_inputs(olcao_code):
    """Test that OlcaoCalculation accepts valid inputs and validates them."""
    olcao_calculation_cls = CalculationFactory("olcao")
    olcao_parameters_cls = DataFactory("olcao")

    # Create valid OLCAO parameters
    parameters = olcao_parameters_cls(
        {
            "kpoints": [5, 5, 5],
            "calculation_type": "dos",
            "basis_scf": "FB",
            "basis_pscf": "FB",
            "edge": "gs",
        }
    )

    # Create skeleton file input
    skeleton = SinglefileData(file=os.path.join(TEST_DIR, "input_files", "diamond.skl"))

    # Build inputs dict
    inputs = {
        "code": olcao_code,
        "skeleton": skeleton,
        "parameters": parameters,
        "olcao_rc": Str("/path/to/test/olcaorc"),
        "makeinput_path": Str("/path/to/test/makeinput"),
        "metadata": {
            "options": {
                "max_wallclock_seconds": 3600,
                "resources": {"num_machines": 1},
            },
        },
    }

    # Create builder and validate inputs
    builder = olcao_calculation_cls.get_builder()
    builder._update(inputs)

    # Verify the inputs are set correctly
    assert builder.code == olcao_code
    assert builder.skeleton == skeleton
    assert builder.parameters == parameters


def test_prepare_for_submission(olcao_code):
    """Test that prepare_for_submission creates correct files and CalcInfo."""
    olcao_calculation_cls = CalculationFactory("olcao")
    olcao_parameters_cls = DataFactory("olcao")

    # Create valid OLCAO parameters
    parameters = olcao_parameters_cls(
        {
            "kpoints": [3, 3, 3],
            "calculation_type": "scf",
            "basis_scf": "FB",
        }
    )

    # Create skeleton file input
    skeleton = SinglefileData(file=os.path.join(TEST_DIR, "input_files", "diamond.skl"))

    # Build inputs
    inputs = {
        "code": olcao_code,
        "skeleton": skeleton,
        "parameters": parameters,
        "olcao_rc": Str("/test/olcaorc"),
        "makeinput_path": Str("/test/makeinput"),
        "metadata": {
            "options": {
                "max_wallclock_seconds": 3600,
                "resources": {"num_machines": 1},
            },
        },
    }

    # Create a CalcJob instance to test prepare_for_submission
    calc = olcao_calculation_cls(inputs=inputs)

    # Create a temporary folder for staging
    with folders.SandboxFolder() as folder:
        calcinfo = calc.prepare_for_submission(folder)

        # Check that olcao.skl was created (skeleton staged with correct name)
        assert folder.get_content_list() == ["olcao.skl"]

        # Check the skeleton file content
        with folder.open("olcao.skl", "r") as f:
            content = f.read()
            assert "Diamond structure" in content
            assert "3.56679" in content

        # Check calcinfo structure
        assert calcinfo.prepend_text is not None
        assert "source /test/olcaorc" in calcinfo.prepend_text
        assert "/test/makeinput -kp 3 3 3" in calcinfo.prepend_text
        assert "OLCAO_TEMP" in calcinfo.prepend_text

        # Check code info
        assert len(calcinfo.codes_info) == 1
        codeinfo = calcinfo.codes_info[0]
        assert codeinfo.cmdline_params == ["-scf", "FB"]

        # Check retrieve list includes common files
        assert "gs_*-*.out" in calcinfo.retrieve_list
        assert "summary" in calcinfo.retrieve_list


def test_parameters_cmdline_generation():
    """Test that OlcaoParameters generates correct command lines."""
    olcao_parameters_cls = DataFactory("olcao")

    # Test basic kpoints
    params = olcao_parameters_cls({"kpoints": [5, 5, 5]})
    assert params.get_makeinput_cmdline() == "-kp 5 5 5"
    assert params.get_uolcao_cmdline() == "-scf FB"  # default

    # Test DOS calculation
    params = olcao_parameters_cls(
        {
            "kpoints": [7, 7, 7],
            "calculation_type": "dos",
        }
    )
    assert params.get_makeinput_cmdline() == "-kp 7 7 7"
    assert params.get_uolcao_cmdline() == "-dos"

    # Test separate SCF and PSCF k-points
    params = olcao_parameters_cls(
        {
            "kpoints_scf": [3, 3, 3],
            "kpoints_pscf": [9, 9, 9],
            "calculation_type": "bond",
        }
    )
    assert params.get_makeinput_cmdline() == "-scfkp 3 3 3 -pscfkp 9 9 9"
    assert params.get_uolcao_cmdline() == "-bond"

    # Test PACS with edge
    params = olcao_parameters_cls(
        {
            "kpoints": [5, 5, 5],
            "calculation_type": "pacs",
            "edge": "1s",
        }
    )
    assert params.get_uolcao_cmdline() == "-pacs 1s"


def test_parameters_validation():
    """Test that OlcaoParameters validates inputs correctly."""
    import pytest
    from aiida.common.exceptions import ValidationError

    olcao_parameters_cls = DataFactory("olcao")

    # Valid parameters should not raise
    params = olcao_parameters_cls(
        {
            "kpoints": [5, 5, 5],
            "calculation_type": "dos",
            "basis_scf": "FB",
            "edge": "gs",
        }
    )
    params.validate()  # Should not raise

    # Invalid calculation type
    params = olcao_parameters_cls({"calculation_type": "invalid"})
    with pytest.raises(ValidationError, match="Invalid calculation_type"):
        params.validate()

    # Invalid kpoints (not 3 elements)
    params = olcao_parameters_cls({"kpoints": [5, 5]})
    with pytest.raises(ValidationError, match="must have exactly 3 elements"):
        params.validate()

    # Invalid kpoints (negative)
    params = olcao_parameters_cls({"kpoints": [5, 5, -1]})
    with pytest.raises(ValidationError, match="must be a positive integer"):
        params.validate()

    # Invalid basis
    params = olcao_parameters_cls({"basis_scf": "INVALID"})
    with pytest.raises(ValidationError, match="Invalid basis_scf"):
        params.validate()
