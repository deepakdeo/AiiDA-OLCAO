#!/usr/bin/env python
"""Plot Density of States (DOS) from a completed AiiDA OlcaoCalculation.

This script retrieves DOS data from a finished OLCAO calculation and creates
a publication-quality plot showing the total density of states versus energy.

Features:
    - Reads gs_dos-*.t.plot file from AiiDA retrieved outputs
    - Plots Energy (eV) vs Total DOS (states/eV)
    - Shows Fermi level as a vertical dashed line at E=0
    - Displays total energy, Fermi energy, and atom count in title
    - Supports saving to file (PNG, PDF, SVG) or interactive display

Usage:
    python plot_dos.py <calc_pk> [output_file]

Arguments:
    calc_pk      Primary key (PK) of the OlcaoCalculation node
    output_file  Optional: Save plot to this file (e.g., dos.png, dos.pdf)
                 If not provided, displays plot interactively

Examples:
    # Display DOS plot interactively
    python plot_dos.py 57

    # Save DOS plot to PNG file
    python plot_dos.py 57 diamond_dos.png

    # Save as PDF for publication
    python plot_dos.py 57 diamond_dos.pdf

Prerequisites:
    1. A completed OlcaoCalculation with calculation_type='dos'
    2. matplotlib installed (pip install matplotlib)
    3. AiiDA profile loaded

Notes:
    - The DOS file format is: ENERGY(eV)  TOTAL_DOS  [PARTIAL_DOS...]
    - Energy is shifted so Fermi level is at E=0
    - X-axis is limited to [-25, 25] eV by default (adjustable in code)
"""

from __future__ import annotations

import sys

import matplotlib.pyplot as plt
from aiida import load_profile
from aiida.orm import load_node

load_profile()


def plot_dos(calc_pk: int, output_file: str | None = None) -> None:
    """Plot the total DOS from an OlcaoCalculation.

    Reads the DOS data from the retrieved folder of a completed OLCAO
    calculation and creates a plot of total density of states versus energy.

    Parameters
    ----------
    calc_pk : int
        Primary key of the OlcaoCalculation node.
    output_file : str, optional
        If provided, save the plot to this file instead of displaying.
        Supported formats: PNG, PDF, SVG, EPS (determined by extension).

    Raises
    ------
    SystemExit
        If the calculation has no DOS output files.
    """
    # Load the calculation node
    print(f"Loading calculation PK={calc_pk}...")
    calc_node = load_node(calc_pk)

    # Verify this is a finished calculation
    if hasattr(calc_node, "process_state"):
        print(f"Process state: {calc_node.process_state}")

    # Get the retrieved folder containing output files
    try:
        retrieved = calc_node.outputs.retrieved
    except AttributeError:
        print(f"Error: Calculation {calc_pk} has no retrieved outputs.")
        print("Make sure the calculation has finished successfully.")
        sys.exit(1)

    # Find the DOS plot file (format: gs_dos-*.t.plot)
    all_files = retrieved.list_object_names()
    dos_files = [f for f in all_files if "dos" in f.lower() and f.endswith(".t.plot")]

    if not dos_files:
        print(f"Error: No DOS plot files (gs_dos-*.t.plot) found in calculation {calc_pk}")
        print(f"Available files: {sorted(all_files)}")
        print("\nHint: Make sure calculation_type='dos' was used.")
        sys.exit(1)

    dos_file = dos_files[0]
    print(f"Reading DOS data from: {dos_file}")

    # Parse the DOS data file
    # Format: ENERGY(eV)  TOTAL_DOS  [PARTIAL_DOS columns...]
    energies: list[float] = []
    dos_values: list[float] = []

    with retrieved.open(dos_file, "r") as f:
        for raw_line in f:
            stripped = raw_line.strip()
            # Skip empty lines and headers
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
        print("Error: No data points found in DOS file")
        print("The file may be empty or have an unexpected format.")
        sys.exit(1)

    print(f"Loaded {len(energies)} data points")
    print(f"Energy range: [{min(energies):.2f}, {max(energies):.2f}] eV")

    # Get calculation metadata for the plot title
    output_params = calc_node.outputs.output_parameters.get_dict()
    total_energy = output_params.get("total_energy")
    fermi_energy = output_params.get("fermi_energy")
    num_atoms = output_params.get("num_atoms", "N/A")

    # Get structure name from skeleton file
    try:
        skeleton_name = calc_node.inputs.skeleton.filename
    except AttributeError:
        skeleton_name = f"Calculation {calc_pk}"

    # Create the plot
    fig, ax = plt.subplots(figsize=(10, 6))

    # Plot DOS curve with fill
    ax.plot(energies, dos_values, "b-", linewidth=0.8, label="Total DOS")
    ax.fill_between(energies, dos_values, alpha=0.3, color="blue")

    # Add vertical line at Fermi level (E=0 in OLCAO output)
    ax.axvline(x=0, color="r", linestyle="--", linewidth=1.5, label="Fermi Level (E=0)")

    # Configure axes
    ax.set_xlabel("Energy (eV)", fontsize=12)
    ax.set_ylabel("Total DOS (states/eV)", fontsize=12)

    # Build title with calculation info
    title_lines = [f"Density of States: {skeleton_name}"]
    info_parts = []
    if total_energy is not None:
        info_parts.append(f"E_total = {total_energy:.6f} Ha")
    if fermi_energy is not None:
        info_parts.append(f"E_Fermi = {fermi_energy:.6f} Ha")
    if num_atoms != "N/A":
        info_parts.append(f"Atoms: {num_atoms}")
    if info_parts:
        title_lines.append(" | ".join(info_parts))

    ax.set_title("\n".join(title_lines), fontsize=11)

    # Add legend and grid
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3, linestyle="-", linewidth=0.5)

    # Set reasonable x-limits focusing on region around Fermi level
    # Adjust these values if you need to see a wider/narrower range
    ax.set_xlim(-25, 25)

    # Ensure y-axis starts at 0
    ax.set_ylim(bottom=0)

    plt.tight_layout()

    # Save or display
    if output_file:
        plt.savefig(output_file, dpi=150, bbox_inches="tight")
        print(f"Plot saved to: {output_file}")
    else:
        print("Displaying plot (close window to exit)...")
        plt.show()


def main() -> None:
    """Command-line entry point."""
    if len(sys.argv) < 2:
        print(__doc__)
        print("\nError: Missing required argument <calc_pk>")
        sys.exit(1)

    try:
        pk = int(sys.argv[1])
    except ValueError:
        print(f"Error: Invalid PK '{sys.argv[1]}' - must be an integer")
        sys.exit(1)

    outfile = sys.argv[2] if len(sys.argv) > 2 else None

    plot_dos(pk, outfile)


if __name__ == "__main__":
    main()
