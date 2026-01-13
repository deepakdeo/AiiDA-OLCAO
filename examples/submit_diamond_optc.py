#!/usr/bin/env python
"""Submit an optical properties calculation for diamond to Hellbender.

This example demonstrates how to run an optical properties calculation
using the AiiDA-OLCAO plugin. Optical calculations compute the
dielectric function and related optical properties.

Usage:
    python submit_diamond_optc.py

Prerequisites:
    1. AiiDA profile configured with daemon running
    2. Hellbender computer set up: verdi computer setup --label hellbender ...
    3. OLCAO code registered: verdi code create core.code.installed --label olcao ...
"""

from pathlib import Path

from aiida import load_profile
from aiida.engine import submit
from aiida.orm import SinglefileData, load_code
from aiida.plugins import CalculationFactory, DataFactory

load_profile()

# Load plugin classes
OlcaoCalculation = CalculationFactory("olcao")
OlcaoParameters = DataFactory("olcao")

# Path to skeleton file
SKELETON_PATH = Path(__file__).parent.parent / "tests" / "input_files" / "diamond.skl"


def main():
    """Submit an optical properties calculation for diamond."""
    # Create the calculation builder
    builder = OlcaoCalculation.get_builder()

    # Set the code (adjust label if your code has a different name)
    builder.code = load_code("olcao@hellbender")

    # Set the skeleton file (structure definition)
    builder.skeleton = SinglefileData(file=str(SKELETON_PATH))

    # Set calculation parameters for optical properties
    # - calculation_type: "optc" for optical calculation
    # - kpoints: k-point mesh for Brillouin zone sampling
    # - basis_scf: "FB" (full basis) for SCF calculation
    # - basis_pscf: "EB" (extended basis) for accurate optical properties
    # - edge: "gs" for ground state
    builder.parameters = OlcaoParameters(
        {
            "kpoints": [5, 5, 5],
            "calculation_type": "optc",
            "basis_scf": "FB",
            "basis_pscf": "EB",
            "edge": "gs",
        }
    )

    # Set computational resources
    builder.metadata.options.resources = {"num_machines": 1}
    builder.metadata.options.max_wallclock_seconds = 7200  # 2 hours (optical can be slower)

    # Optional: Set a descriptive label
    builder.metadata.label = "diamond-optc"
    builder.metadata.description = "Optical properties calculation of diamond structure"

    # Submit the calculation
    calc = submit(builder)
    print(f"Submitted optical properties calculation: PK={calc.pk}")
    print(f"Monitor with: verdi process show {calc.pk}")
    print("View results: verdi data olcao results")

    return calc


if __name__ == "__main__":
    main()
