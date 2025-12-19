"""Tests for calculations."""

import os

from aiida.engine import run
from aiida.orm import SinglefileData
from aiida.plugins import CalculationFactory, DataFactory

from . import TEST_DIR


def test_process(olcao_code):
    """Test running a calculation
    note this does not test that the expected outputs are created of output parsing"""

    # Prepare input parameters
    diff_parameters = DataFactory("olcao")
    parameters = diff_parameters({"ignore-case": True})

    input_file = SinglefileData(file=os.path.join(TEST_DIR, "input_files", "file1.txt"))

    # set up calculation
    inputs = {
        "code": olcao_code,
        "parameters": parameters,
        "input_file": input_file,
        "metadata": {
            "options": {"max_wallclock_seconds": 30},
        },
    }

    result = run(CalculationFactory("olcao"), **inputs)
    output_parameters = result["output_parameters"].get_dict()

    assert output_parameters["output_filename"] == "olcao.out"
    assert output_parameters["stdout_nbytes"] > 0
    assert output_parameters["stdout_nchars"] > 0
