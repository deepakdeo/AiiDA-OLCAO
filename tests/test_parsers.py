"""Tests for OlcaoParser."""

from aiida_olcao.parsers import _find_output_files, _parse_olcao_output


def test_find_output_files():
    """Test finding OLCAO output files by pattern."""
    retrieved_names = [
        "gs_scf-fb.out",
        "gs_dos-fb.out",
        "summary",
        "olcao.dat",
        "structure.dat",
        "random.txt",
    ]

    output_files = _find_output_files(retrieved_names)
    assert len(output_files) == 2
    assert "gs_scf-fb.out" in output_files
    assert "gs_dos-fb.out" in output_files
    assert "summary" not in output_files


def test_find_output_files_empty():
    """Test when no output files match the pattern."""
    retrieved_names = ["summary", "olcao.dat"]
    output_files = _find_output_files(retrieved_names)
    assert len(output_files) == 0


def test_parse_total_energy():
    """Test parsing total energy from output."""
    text = """
    OLCAO Calculation Output
    TOTAL ENERGY = -123.456789
    FERMI ENERGY = 0.123456
    """
    results = _parse_olcao_output(text)
    assert results["total_energy"] == -123.456789
    assert results["total_energy_units"] == "Hartree"


def test_parse_total_energy_underscore():
    """Test parsing total energy with underscore format."""
    text = "TOTAL_ENERGY = -99.8765"
    results = _parse_olcao_output(text)
    assert results["total_energy"] == -99.8765


def test_parse_fermi_energy():
    """Test parsing Fermi energy from output."""
    text = "FERMI ENERGY = 0.234567"
    results = _parse_olcao_output(text)
    assert results["fermi_energy"] == 0.234567
    assert results["fermi_energy_units"] == "Hartree"


def test_parse_num_atoms():
    """Test parsing number of atoms."""
    text = "NUMBER OF ATOMS = 8"
    results = _parse_olcao_output(text)
    assert results["num_atoms"] == 8


def test_parse_num_electrons():
    """Test parsing number of electrons."""
    text = "NUM_ELECTRONS = 48.0"
    results = _parse_olcao_output(text)
    assert results["num_electrons"] == 48.0


def test_parse_iterations():
    """Test parsing number of iterations."""
    text = """
    ITERATION 1: energy = -100.0
    ITERATION 2: energy = -110.0
    ITERATION 3: energy = -115.0
    ITERATION 4: energy = -115.5
    SCF CONVERGED
    """
    results = _parse_olcao_output(text)
    assert results["num_iterations"] == 4
    assert results["converged"] is True


def test_parse_not_converged():
    """Test parsing non-convergence status."""
    text = """
    ITERATION 100: energy = -100.0
    NOT CONVERGED
    """
    results = _parse_olcao_output(text)
    assert results["converged"] is False


def test_parse_band_gap():
    """Test parsing band gap."""
    text = "BAND GAP = 1.234"
    results = _parse_olcao_output(text)
    assert results["band_gap"] == 1.234
    assert results["band_gap_units"] == "eV"


def test_parse_error_detection():
    """Test error detection in output."""
    text = """
    Starting calculation...
    ERROR: SCF failed to converge after 100 iterations
    Calculation aborted.
    """
    results = _parse_olcao_output(text)
    assert results["has_error"] is True
    assert "error_message" in results


def test_parse_scf_failed():
    """Test SCF FAILED detection."""
    text = "SCF FAILED: convergence not achieved"
    results = _parse_olcao_output(text)
    assert results["has_error"] is True


def test_parse_empty_output():
    """Test parsing empty output returns empty dict."""
    results = _parse_olcao_output("")
    assert results == {}


def test_parse_complete_output():
    """Test parsing a complete OLCAO-like output."""
    text = """
    ===============================================
    OLCAO Calculation for Diamond
    ===============================================

    NUMBER OF ATOMS = 2
    NUM_ELECTRONS = 8.0

    SCF Iteration History:
    ITERATION 1: energy = -11.234567
    ITERATION 2: energy = -11.345678
    ITERATION 3: energy = -11.356789
    ITERATION 4: energy = -11.357890

    SCF CONVERGED after 4 iterations

    TOTAL ENERGY = -11.357890
    FERMI ENERGY = 0.456789
    BAND GAP = 5.47

    ===============================================
    """
    results = _parse_olcao_output(text)

    assert results["num_atoms"] == 2
    assert results["num_electrons"] == 8.0
    assert results["num_iterations"] == 4
    assert results["converged"] is True
    assert results["total_energy"] == -11.357890
    assert results["fermi_energy"] == 0.456789
    assert results["band_gap"] == 5.47
