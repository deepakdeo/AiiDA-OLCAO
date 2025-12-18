"""Helper utilities for the ``aiida-olcao`` plugin."""

from __future__ import annotations

from typing import Final

# These filenames are used inside the calculation sandbox folder.
DEFAULT_INPUT_FILENAME: Final[str] = 'olcao.in'
DEFAULT_OUTPUT_FILENAME: Final[str] = 'olcao.out'


def get_input_filename() -> str:
    """Return the input filename used in the sandbox.

    We keep this in a small helper to make it easy to change later without
    having to hunt through calculation/parser code.
    """

    return DEFAULT_INPUT_FILENAME


def get_output_filename() -> str:
    """Return the output filename produced by the OLCAO executable."""

    return DEFAULT_OUTPUT_FILENAME
