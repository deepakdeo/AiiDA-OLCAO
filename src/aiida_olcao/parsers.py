"""Parser for the ``aiida-olcao`` CalcJob.

Robust minimal parser that:
- locates the main stdout output file (from node option `output_filename`)
- stores basic metadata (filename, byte size, decoded char size)
- extracts TOTAL_ENERGY if present (supports TOTAL ENERGY or TOTAL_ENERGY)
- records a small error excerpt if output appears to contain an error
"""

from __future__ import annotations

import re
from typing import Any, Dict, Optional, Tuple

from aiida import orm
from aiida.engine import ExitCode
from aiida.parsers.parser import Parser

from .helpers import get_output_filename


def _read_text_from_repository(repo, name: str) -> Tuple[str, int]:
    """Read a repository object as text, returning (text, nbytes).

    Decodes as UTF-8 with replacement so parsing never crashes on encoding issues.
    """
    data = repo.get_object_content(name, mode="rb")
    if isinstance(data, str):
        # Some backends may already return text
        return data, len(data.encode("utf-8", errors="replace"))
    nbytes = len(data)
    text = data.decode("utf-8", errors="replace")
    return text, nbytes


def _extract_total_energy(text: str) -> Optional[float]:
    """Extract TOTAL_ENERGY from output text if present."""
    energy_re = re.compile(
        r"\bTOTAL[\s_]+ENERGY\b\s*=\s*([-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?)"
    )
    m = energy_re.search(text)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _error_excerpt(text: str, needle: str = "error", window: int = 120) -> Optional[str]:
    """Return a short excerpt around the first occurrence of `needle` (case-insensitive)."""
    lower = text.lower()
    idx = lower.find(needle.lower())
    if idx == -1:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + window)
    return text[start:end]


class OlcaoParser(Parser):
    """Parser for :class:`~aiida_olcao.calculations.OlcaoCalculation`."""

    def parse(self, **kwargs: Any) -> ExitCode | None:
        # 1) Retrieved folder must exist
        try:
            retrieved = self.retrieved
        except Exception:  # pragma: no cover
            return self.exit_codes.ERROR_NO_RETRIEVED_FOLDER

        # 2) Determine expected output filename from the node (truth) or helper default
        output_filename = self.node.get_option("output_filename") or get_output_filename()

        # 3) List retrieved objects reliably
        repo = retrieved.base.repository
        retrieved_names = repo.list_object_names()

        if output_filename not in retrieved_names:
            # Provide context: what *was* retrieved?
            self.out(
                "output_parameters",
                orm.Dict(
                    dict={
                        "output_filename": output_filename,
                        "retrieved_names": sorted(retrieved_names),
                        "parser_warnings": ["missing_expected_output_file"],
                    }
                ),
            )
            return self.exit_codes.ERROR_MISSING_OUTPUT_FILE

        # 4) Read and decode output safely
        text, nbytes = _read_text_from_repository(repo, output_filename)

        results: Dict[str, Any] = {
            "output_filename": output_filename,
            "stdout_nbytes": nbytes,
            "stdout_nchars": len(text),
        }

        # 5) Basic error sniffing (non-fatal, but useful)
        excerpt = _error_excerpt(text, "error", window=200)
        if excerpt is not None:
            results["error_excerpt"] = excerpt

        # 6) Parse total energy if present
        total_energy = _extract_total_energy(text)
        if total_energy is not None:
            results["total_energy"] = total_energy

        self.out("output_parameters", orm.Dict(dict=results))
        return None

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.exit_code(
            300,
            "ERROR_NO_RETRIEVED_FOLDER",
            message="The retrieved folder could not be accessed.",
        )
        spec.exit_code(
            301,
            "ERROR_MISSING_OUTPUT_FILE",
            message="The expected output file was not retrieved.",
        )
