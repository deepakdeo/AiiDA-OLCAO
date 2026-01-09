"""Parser for OLCAO calculations.

This parser extracts results from OLCAO output files including:
- Total energy
- Fermi energy
- Number of SCF iterations
- Convergence status
- Number of atoms and electrons
"""

from __future__ import annotations

import fnmatch
import re
from typing import Any

from aiida import orm
from aiida.engine import ExitCode
from aiida.parsers.parser import Parser


def _read_file_content(repo, filename: str) -> tuple[str, int]:
    """Read a file from the repository as text.

    Parameters
    ----------
    repo : Repository
        The AiiDA repository object.
    filename : str
        Name of the file to read.

    Returns
    -------
    tuple[str, int]
        The file content as text and the number of bytes.
    """
    data = repo.get_object_content(filename, mode="rb")
    if isinstance(data, str):
        return data, len(data.encode("utf-8", errors="replace"))
    nbytes = len(data)
    text = data.decode("utf-8", errors="replace")
    return text, nbytes


def _find_output_files(retrieved_names: list[str]) -> list[str]:
    """Find OLCAO output files matching ``gs_*-*.out`` pattern.

    Parameters
    ----------
    retrieved_names : list[str]
        List of retrieved file names.

    Returns
    -------
    list[str]
        List of matching output file names.
    """
    pattern = "gs_*-*.out"
    return [name for name in retrieved_names if fnmatch.fnmatch(name, pattern)]


def _parse_olcao_output(text: str) -> dict[str, Any]:
    """Parse OLCAO output file content.

    Parameters
    ----------
    text : str
        The output file content.

    Returns
    -------
    dict[str, Any]
        Dictionary containing parsed values.
    """
    results: dict[str, Any] = {}

    # Extract total energy (various formats)
    # Pattern: "TOTAL ENERGY = -123.456789" or "TOTAL_ENERGY = -123.456789"
    total_energy_match = re.search(
        r"\bTOTAL[\s_]+ENERGY\s*[=:]\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
        text,
        re.IGNORECASE,
    )
    if total_energy_match:
        try:
            results["total_energy"] = float(total_energy_match.group(1))
            results["total_energy_units"] = "Hartree"
        except ValueError:
            pass

    # Extract Fermi energy
    # Pattern: "FERMI ENERGY = 0.123456" or "Fermi energy: 0.123456"
    fermi_match = re.search(
        r"\bFERMI[\s_]+ENERGY\s*[=:]\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
        text,
        re.IGNORECASE,
    )
    if fermi_match:
        try:
            results["fermi_energy"] = float(fermi_match.group(1))
            results["fermi_energy_units"] = "Hartree"
        except ValueError:
            pass

    # Extract number of atoms
    # Pattern: "Number of atoms: 8" or "NUM_ATOMS = 8"
    atoms_match = re.search(
        r"(?:NUM(?:BER)?[\s_]*(?:OF)?[\s_]*ATOMS|ATOMS)\s*[=:]\s*(\d+)",
        text,
        re.IGNORECASE,
    )
    if atoms_match:
        try:
            results["num_atoms"] = int(atoms_match.group(1))
        except ValueError:
            pass

    # Extract number of electrons
    # Pattern: "Number of electrons: 48.0" or "NUM_ELECTRONS = 48"
    electrons_match = re.search(
        r"(?:NUM(?:BER)?[\s_]*(?:OF)?[\s_]*ELECTRONS|ELECTRONS)\s*[=:]\s*([-+]?\d+(?:\.\d+)?)",
        text,
        re.IGNORECASE,
    )
    if electrons_match:
        try:
            results["num_electrons"] = float(electrons_match.group(1))
        except ValueError:
            pass

    # Extract number of SCF iterations
    # Look for iteration numbers and find the maximum
    iteration_matches = re.findall(r"\bITER(?:ATION)?[\s_]*[=:#]?\s*(\d+)", text, re.IGNORECASE)
    if iteration_matches:
        try:
            results["num_iterations"] = max(int(i) for i in iteration_matches)
        except ValueError:
            pass

    # Check convergence status
    # Look for convergence indicators (check negative cases first)
    if re.search(r"\bNOT\s+CONVERGED\b", text, re.IGNORECASE):
        results["converged"] = False
    elif re.search(r"\bCONVERGENCE\s+NOT\s+(?:REACHED|ACHIEVED)\b", text, re.IGNORECASE):
        results["converged"] = False
    elif re.search(r"\b(?:SCF\s+)?CONVERGED\b", text, re.IGNORECASE):
        results["converged"] = True
    elif re.search(r"\bCONVERGENCE\s+(?:REACHED|ACHIEVED)\b", text, re.IGNORECASE):
        results["converged"] = True

    # Extract band gap if present
    gap_match = re.search(
        r"\bBAND[\s_]*GAP\s*[=:]\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)",
        text,
        re.IGNORECASE,
    )
    if gap_match:
        try:
            results["band_gap"] = float(gap_match.group(1))
            results["band_gap_units"] = "eV"
        except ValueError:
            pass

    # Check for errors
    error_patterns = [
        r"ERROR\s*:",
        r"FATAL\s+ERROR",
        r"SCF\s+FAILED",
        r"CALCULATION\s+FAILED",
    ]
    for pattern in error_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            results["has_error"] = True
            # Extract error message context
            error_match = re.search(rf"({pattern}.*?)(?:\n\n|\Z)", text, re.IGNORECASE | re.DOTALL)
            if error_match:
                results["error_message"] = error_match.group(1)[:500]  # Limit length
            break

    return results


class OlcaoParser(Parser):
    """Parser for OLCAO calculation results.

    Parses output files from OLCAO calculations to extract:
    - Total energy
    - Fermi energy
    - Number of SCF iterations
    - Convergence status
    - Number of atoms and electrons
    - Band gap (if available)
    """

    def parse(self, **kwargs: Any) -> ExitCode | None:
        """Parse the retrieved files from an OLCAO calculation.

        Returns
        -------
        ExitCode or None
            An exit code if parsing failed, None if successful.
        """
        # Get retrieved folder
        try:
            retrieved = self.retrieved
        except Exception:
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # Get list of retrieved files
        repo = retrieved.base.repository
        retrieved_names = list(repo.list_object_names())

        results: dict[str, Any] = {
            "retrieved_files": sorted(retrieved_names),
        }

        # Check if makeinput failed (no inputs/ directory would mean no output)
        # This is indicated by missing essential output files
        output_files = _find_output_files(retrieved_names)

        if not output_files:
            # No OLCAO output files found
            # Check if this might be a makeinput failure
            if "summary" not in retrieved_names and "olcao.dat" not in retrieved_names:
                results["parser_warnings"] = ["No OLCAO output files found - makeinput may have failed"]
                self.out("output_parameters", orm.Dict(dict=results))
                return self.exit_codes.ERROR_MAKEINPUT_FAILED

            results["parser_warnings"] = ["No gs_*-*.out files found"]
            self.out("output_parameters", orm.Dict(dict=results))
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILE

        # Parse the main output file (first one found)
        main_output = sorted(output_files)[0]
        results["output_file"] = main_output

        try:
            text, nbytes = _read_file_content(repo, main_output)
            results["output_size_bytes"] = nbytes
        except Exception as exc:
            results["parser_error"] = f"Failed to read {main_output}: {exc}"
            self.out("output_parameters", orm.Dict(dict=results))
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILE

        # Parse the output content
        parsed = _parse_olcao_output(text)
        results.update(parsed)

        # Also try to parse the summary file if present
        if "summary" in retrieved_names:
            try:
                summary_text, _ = _read_file_content(repo, "summary")
                summary_parsed = _parse_olcao_output(summary_text)
                # Only add values not already present
                for key, value in summary_parsed.items():
                    if key not in results:
                        results[key] = value
            except Exception:
                pass  # Summary parsing is optional

        # Store the results
        self.out("output_parameters", orm.Dict(dict=results))

        # Determine exit code based on results
        if results.get("has_error"):
            return self.exit_codes.ERROR_SCF_FAILED

        if results.get("converged") is False:
            return self.exit_codes.ERROR_NOT_CONVERGED

        return None
