#!/usr/bin/env python
"""Plot DOS from an AiiDA OlcaoCalculation."""

import sys

import matplotlib.pyplot as plt
from aiida import load_profile
from aiida.orm import load_node

load_profile()


def plot_dos(calc_pk: int, output_file: str | None = None):
    """Plot the total DOS from an OlcaoCalculation.

    Parameters
    ----------
    calc_pk : int
        Primary key of the OlcaoCalculation node.
    output_file : str, optional
        If provided, save the plot to this file instead of displaying.
    """
    # Load the calculation node
    calc_node = load_node(calc_pk)

    # Get the retrieved folder
    retrieved = calc_node.outputs.retrieved

    # Find the DOS plot file
    dos_files = [f for f in retrieved.list_object_names() if "dos" in f.lower() and f.endswith(".t.plot")]

    if not dos_files:
        print(f"No DOS plot files found in calculation {calc_pk}")
        print(f"Available files: {retrieved.list_object_names()}")
        return

    dos_file = dos_files[0]
    print(f"Plotting DOS from: {dos_file}")

    # Read the DOS data
    energies = []
    dos_values = []

    with retrieved.open(dos_file, "r") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("ENERGY") or stripped.startswith("#"):
                continue
            parts = stripped.split()
            if len(parts) >= 2:
                try:
                    energy = float(parts[0])
                    dos = float(parts[1])
                    energies.append(energy)
                    dos_values.append(dos)
                except ValueError:
                    continue

    if not energies:
        print("No data points found in DOS file")
        return

    # Get calculation info for the title
    output_params = calc_node.outputs.output_parameters.get_dict()
    total_energy = output_params.get("total_energy", "N/A")
    num_atoms = output_params.get("num_atoms", "N/A")

    # Try to get structure name from skeleton
    try:
        skeleton_name = calc_node.inputs.skeleton.filename
    except Exception:
        skeleton_name = "Unknown"

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(energies, dos_values, "b-", linewidth=0.8)
    ax.fill_between(energies, dos_values, alpha=0.3)

    # Add a vertical line at E=0 (Fermi level is usually set to 0)
    ax.axvline(x=0, color="r", linestyle="--", linewidth=1, label="Fermi Level")

    ax.set_xlabel("Energy (eV)", fontsize=12)
    ax.set_ylabel("Total DOS (states/eV)", fontsize=12)
    ax.set_title(
        f"Density of States: {skeleton_name}\n" f"Total Energy: {total_energy:.6f} Ha | Atoms: {num_atoms}", fontsize=12
    )
    ax.legend()
    ax.grid(True, alpha=0.3)

    # Set reasonable x-limits (focus on region around Fermi level)
    ax.set_xlim(-25, 25)

    plt.tight_layout()

    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"Plot saved to: {output_file}")
    else:
        plt.show()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python plot_dos.py <calc_pk> [output_file]")
        print("Example: python plot_dos.py 57")
        print("         python plot_dos.py 57 diamond_dos.png")
        sys.exit(1)

    pk = int(sys.argv[1])
    outfile = sys.argv[2] if len(sys.argv) > 2 else None

    plot_dos(pk, outfile)
