#!/usr/bin/env python
"""Submit a multi-step OLCAO WorkChain for diamond to Hellbender.

This example demonstrates how to use the OlcaoBaseWorkChain to run
multiple OLCAO calculations in a single workflow submission. The
WorkChain automatically:

1. Runs SCF calculation first
2. Checks SCF convergence
3. Runs all requested post-SCF calculations (DOS, bond, etc.)
4. Collects all results with full provenance

This is more efficient than submitting individual calculations because:
- Single submission for multiple calculations
- Automatic SCF convergence checking
- Results are linked in the provenance graph
- Appropriate basis sets are used for each calculation type

Usage:
    python submit_diamond_workchain.py

Prerequisites:
    1. AiiDA profile configured with daemon running
    2. Hellbender computer set up: verdi computer setup --label hellbender ...
    3. OLCAO code registered: verdi code create core.code.installed --label olcao ...
"""

from pathlib import Path

from aiida import load_profile
from aiida.engine import submit
from aiida.orm import List, SinglefileData, Str, load_code
from aiida.plugins import WorkflowFactory

load_profile()

# Load the WorkChain class
OlcaoBaseWorkChain = WorkflowFactory("olcao.base")

# Path to skeleton file
SKELETON_PATH = Path(__file__).parent.parent / "tests" / "input_files" / "diamond.skl"


def main():
    """Submit a multi-step OLCAO workflow for diamond."""
    # Create the workflow builder
    builder = OlcaoBaseWorkChain.get_builder()

    # Set the code (adjust label if your code has a different name)
    builder.code = load_code("olcao@hellbender")

    # Set the skeleton file (structure definition)
    builder.skeleton = SinglefileData(file=str(SKELETON_PATH))

    # Set k-point mesh (applies to both SCF and post-SCF)
    builder.kpoints = List(list=[5, 5, 5])

    # Specify which calculations to run after SCF
    # Available types: 'dos', 'bond', 'sybd', 'optc', 'pacs', 'field', 'force'
    builder.calculations = List(list=["dos", "bond"])

    # Basis set for SCF (Full Basis is good for most calculations)
    builder.basis_scf = Str("FB")

    # Default post-SCF basis (the WorkChain will use recommended basis per calc type)
    # - DOS uses FB (full basis)
    # - Bond uses MB (minimal basis)
    # - Optical uses EB (extended basis)
    builder.basis_pscf = Str("FB")

    # Edge for excited state calculations (gs = ground state)
    builder.edge = Str("gs")

    # Set computational resources (apply to all calculations)
    builder.options = {
        "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
        "max_wallclock_seconds": 3600,  # 1 hour per calculation
    }

    # Optional: Set a descriptive label
    builder.metadata.label = "diamond-workchain"
    builder.metadata.description = "Diamond SCF + DOS + Bond workflow"

    # Submit the workflow
    workflow = submit(builder)
    print(f"Submitted OlcaoBaseWorkChain: PK={workflow.pk}")
    print("This workflow will run: SCF -> DOS -> Bond")
    print()
    print("Monitor with:")
    print(f"  verdi process show {workflow.pk}")
    print(f"  verdi process status {workflow.pk}")
    print()
    print("When finished, view results:")
    print("  verdi data olcao results")
    print()
    print("Access outputs programmatically:")
    print("  from aiida.orm import load_node")
    print(f"  wf = load_node({workflow.pk})")
    print("  scf_results = wf.outputs.scf_parameters.get_dict()")
    print("  dos_results = wf.outputs.post_scf_parameters.dos.get_dict()")
    print("  bond_results = wf.outputs.post_scf_parameters.bond.get_dict()")

    return workflow


if __name__ == "__main__":
    main()
