#!/usr/bin/env python
"""Example: Submit a diamond DOS calculation to Hellbender.

This script demonstrates how to submit an OLCAO calculation using
the AiiDA-OLCAO plugin.

Prerequisites:
    - AiiDA configured with 'hellbender' computer
    - Code 'olcao@hellbender' registered (points to uolcao)
    - AiiDA daemon running: verdi daemon start

Usage:
    python submit_diamond_dos.py
"""

from pathlib import Path

from aiida import load_profile
from aiida.engine import submit
from aiida.orm import SinglefileData, load_code
from aiida.plugins import CalculationFactory, DataFactory

# Load the default AiiDA profile
load_profile()

# Load plugin classes
OlcaoCalculation = CalculationFactory("olcao")
OlcaoParameters = DataFactory("olcao")

# Path to skeleton file
SKELETON_FILE = Path(__file__).parent.parent / "tests" / "input_files" / "diamond.skl"


def main():
    """Submit a diamond DOS calculation."""
    # Load the OLCAO code (uolcao executable on Hellbender)
    code = load_code("olcao@hellbender")

    # Create the builder
    builder = OlcaoCalculation.get_builder()

    # Set the code
    builder.code = code

    # Load the skeleton file
    builder.skeleton = SinglefileData(file=str(SKELETON_FILE))

    # Set calculation parameters
    builder.parameters = OlcaoParameters(
        {
            "kpoints": [5, 5, 5],  # 5x5x5 k-point mesh
            "calculation_type": "dos",  # Density of states
            "basis_scf": "FB",  # Full basis for SCF
            "basis_pscf": "FB",  # Full basis for post-SCF
            "edge": "gs",  # Ground state
        }
    )

    # Set computational resources
    builder.metadata.options.resources = {
        "num_machines": 1,
        "num_mpiprocs_per_machine": 1,
    }
    builder.metadata.options.max_wallclock_seconds = 3600  # 1 hour

    # Optional: Add description and label
    builder.metadata.description = "Diamond DOS calculation with 5x5x5 k-points"
    builder.metadata.label = "diamond-dos"

    # Submit the calculation
    calc_node = submit(builder)
    print(f"Submitted calculation: {calc_node.pk}")
    print(f"UUID: {calc_node.uuid}")
    print()
    print("Monitor with:")
    print(f"  verdi process show {calc_node.pk}")
    print("  verdi process list -a")

    return calc_node


if __name__ == "__main__":
    main()
