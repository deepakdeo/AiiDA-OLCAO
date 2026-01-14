[![Build Status][ci-badge]][ci-link]
[![Coverage Status][cov-badge]][cov-link]
[![Docs status][docs-badge]][docs-link]
[![PyPI version][pypi-badge]][pypi-link]

# AiiDA-OLCAO

An [AiiDA](https://www.aiida.net/) plugin for running [OLCAO](https://github.com/UMKC-CPG/olcao) (Orthogonalized Linear Combination of Atomic Orbitals) calculations on HPC clusters.

## What is OLCAO?

OLCAO is a density functional theory (DFT) code for electronic structure calculations developed at the University of Missouri-Kansas City. It specializes in:

- Electronic structure calculations (SCF)
- Density of states (DOS)
- Band structure (SYBD)
- Bond order analysis (BOND)
- Optical properties (OPTC)
- X-ray absorption spectroscopy / XANES (PACS)

## What does this plugin do?

AiiDA-OLCAO integrates OLCAO into the AiiDA workflow management framework, providing:

- **Automated job submission** to HPC clusters (SLURM, PBS, etc.)
- **Full data provenance** tracking for reproducible research
- **Input validation** for OLCAO parameters
- **Output parsing** of energies, Fermi levels, convergence status, and more
- **High-throughput screening** capabilities for materials discovery

## Installation

```bash
pip install aiida-olcao

# Set up AiiDA (if not already configured)
verdi quicksetup

# Verify the plugin is installed
verdi plugin list aiida.calculations  # Should show 'olcao'
```

For development installation:

```bash
git clone https://github.com/deepakdeo/AiiDA-OLCAO.git
cd AiiDA-OLCAO
pip install -e .[pre-commit,testing]
pre-commit install
```

## Quick Start Guide

### 1. Configure Your HPC Computer

First, set up your remote computer in AiiDA. Example for Hellbender (University of Missouri):

```bash
verdi computer setup \
    --label hellbender \
    --hostname hellbender.rnet.missouri.edu \
    --transport core.ssh \
    --scheduler core.slurm \
    --work-dir /home/{username}/scratch/aiida_work \
    --mpiprocs-per-machine 1

verdi computer configure core.ssh hellbender \
    --username {your_username} \
    --key-filename ~/.ssh/id_ed25519

# Test the connection
verdi computer test hellbender
```

### 2. Register the OLCAO Code

```bash
verdi code create core.code.installed \
    --label olcao \
    --computer hellbender \
    --filepath-executable /path/to/olcao/bin/uolcao \
    --default-calc-job-plugin olcao
```

### 3. Submit a Calculation

Create a Python script (or use `examples/submit_diamond_dos.py`):

```python
from aiida import load_profile
from aiida.engine import submit
from aiida.orm import SinglefileData, load_code
from aiida.plugins import CalculationFactory, DataFactory

load_profile()

# Load plugin classes
OlcaoCalculation = CalculationFactory('olcao')
OlcaoParameters = DataFactory('olcao')

# Create the calculation
builder = OlcaoCalculation.get_builder()
builder.code = load_code('olcao@hellbender')
builder.skeleton = SinglefileData(file='/path/to/diamond.skl')
builder.parameters = OlcaoParameters({
    'kpoints': [5, 5, 5],
    'calculation_type': 'dos',
    'basis_scf': 'FB',
    'basis_pscf': 'FB',
    'edge': 'gs',
})
builder.metadata.options.resources = {'num_machines': 1}
builder.metadata.options.max_wallclock_seconds = 3600

# Submit
calc = submit(builder)
print(f'Submitted calculation: {calc.pk}')
```

Run it:

```bash
verdi daemon start  # Ensure daemon is running
python submit_diamond_dos.py
```

### 4. Monitor and Check Results

```bash
# Watch calculation progress
verdi process list -a

# View detailed status
verdi process show <PK>

# View summary table of all OLCAO calculations
verdi data olcao results

# Example output:
#     PK  Label             Type    Energy (Ha)     Status        Date
# ------  ----------------  ------  --------------  ------------  ----------
#     57  diamond-dos       dos     -45.768046      Finished      2026-01-08
#     46  silicon.skl       scf     -31.234567      Finished      2026-01-07
```

### 5. View Parsed Output

```bash
# Get the output parameters PK from process show
verdi data dict show <output_parameters_PK>

# Example output:
# {
#     "total_energy": -45.768046,
#     "total_energy_units": "Hartree",
#     "fermi_energy": 0.234567,
#     "fermi_energy_units": "Hartree",
#     "num_atoms": 2,
#     "num_electrons": 8.0,
#     "num_iterations": 12,
#     "converged": true,
#     "band_gap": 5.47,
#     "band_gap_units": "eV"
# }
```

## CLI Commands

The plugin provides several `verdi` commands:

| Command | Description |
|---------|-------------|
| `verdi data olcao results` | Show summary table of all OLCAO calculations |
| `verdi data olcao list` | List OlcaoParameters nodes |
| `verdi data olcao export <PK>` | Export parameters from a node |

### Results Command Options

```bash
verdi data olcao results --help

Options:
  --limit INTEGER    Maximum calculations to show (default: 20)
  --past-days INTEGER  Only show calculations from last N days
  --all-states       Include running/waiting calculations
```

## Supported Calculation Types

| Type | Description | Output Files |
|------|-------------|--------------|
| `scf` | Self-consistent field (ground state) | `gs_scf-*.out` |
| `dos` | Density of states | `gs_dos-*.t.plot`, `gs_dos-*.p.raw` |
| `bond` | Bond order analysis | `gs_bond-*.raw` |
| `sybd` | Symmetric band structure | `gs_sybd-*.plot` |
| `optc` | Optical properties (dielectric function) | `gs_optc-*.t.plot` |
| `pacs` | X-ray absorption (XANES) | `gs_pacs-*.plot` |
| `field` | Charge density / potential | `gs_field-*.plot` |
| `force` | Atomic forces | `gs_force-*.dat` |
| `nlop` | Nonlinear optical properties | `gs_nlop-*.plot` |
| `sige` | Optical transitions near Fermi level | `gs_sige-*.plot` |

## WorkChain: Multi-Step Workflows

For running multiple calculation types on the same structure, use the `OlcaoBaseWorkChain`. This workflow automatically chains SCF and post-SCF calculations with proper sequencing.

**Benefits:**
- **Single submission** - Submit once, run SCF + multiple post-SCF calculations
- **Automatic sequencing** - SCF runs first, post-SCF only runs if SCF converges
- **Smart basis selection** - Uses recommended basis sets for each calculation type
- **Full provenance** - All calculations linked in the AiiDA provenance graph

### WorkChain Example

```python
from aiida import load_profile
from aiida.engine import submit
from aiida.orm import List, SinglefileData, load_code
from aiida.plugins import WorkflowFactory

load_profile()

# Load the WorkChain
OlcaoBaseWorkChain = WorkflowFactory('olcao.base')

# Build the workflow
builder = OlcaoBaseWorkChain.get_builder()
builder.code = load_code('olcao@hellbender')
builder.skeleton = SinglefileData(file='diamond.skl')
builder.kpoints = List([5, 5, 5])
builder.calculations = List(['dos', 'bond', 'optc'])  # Run all three after SCF

# Submit
workflow = submit(builder)
print(f'Submitted workflow: {workflow.pk}')
```

### WorkChain Outputs

After completion, access results:

```python
from aiida.orm import load_node

wf = load_node(<workflow_pk>)
scf_results = wf.outputs.scf_parameters.get_dict()
dos_results = wf.outputs.post_scf_parameters.dos.get_dict()
bond_results = wf.outputs.post_scf_parameters.bond.get_dict()
```

## Parameter Reference

The `OlcaoParameters` data type accepts:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `kpoints` | list[int] | `[1,1,1]` | K-point mesh [a, b, c] |
| `kpoints_scf` | list[int] | - | K-points for SCF only |
| `kpoints_pscf` | list[int] | - | K-points for post-SCF only |
| `calculation_type` | str | `'scf'` | Type of calculation (see above) |
| `basis_scf` | str | `'FB'` | SCF basis: `'EB'`, `'FB'`, `'MB'` |
| `basis_pscf` | str | `'FB'` | Post-SCF basis |
| `edge` | str | `'gs'` | Edge for excited states: `'gs'`, `'1s'`, `'2p'`, etc. |

## Skeleton File Format

OLCAO uses `.skl` skeleton files to define the structure:

```
title
Diamond structure
end
cell
3.56679 3.56679 3.56679 90.0 90.0 90.0
fract 1
C 0.00000 0.00000 0.00000
space 227_a
supercell 1 1 1
full
```

**Format explanation:**
- `title` / `end`: Structure name/description block
- `cell`: Lattice parameters (a, b, c in Angstroms; alpha, beta, gamma in degrees)
- `fract N`: Number of atoms, using fractional coordinates
- `Element x y z`: Atom positions
- `space`: Space group (e.g., `227_a` for diamond Fd-3m)
- `supercell`: Supercell multipliers
- `full` or `prim`: Use full or primitive cell

## Exit Codes

The parser returns these exit codes:

| Code | Name | Description |
|------|------|-------------|
| 0 | Success | Calculation completed successfully |
| 300 | `ERROR_NO_RETRIEVED_FOLDER` | Retrieved folder not found |
| 301 | `ERROR_MISSING_OUTPUT_FILE` | Output file not found |
| 302 | `ERROR_NOT_CONVERGED` | SCF did not converge |
| 303 | `ERROR_SCF_FAILED` | SCF calculation failed |
| 310 | `ERROR_MAKEINPUT_FAILED` | makeinput preprocessing failed |

## Examples

The `examples/` directory contains ready-to-use scripts:

| Script | Description |
|--------|-------------|
| `submit_diamond_dos.py` | Submit a DOS calculation |
| `submit_diamond_bond.py` | Submit a bond order calculation |
| `submit_diamond_optc.py` | Submit an optical properties calculation |
| `submit_diamond_workchain.py` | Submit a multi-step workflow (SCF + DOS + Bond) |
| `plot_dos.py` | Plot DOS from a completed calculation |

### Running an Example

```bash
cd examples

# Submit a single calculation
python submit_diamond_dos.py

# Submit a multi-step workflow
python submit_diamond_workchain.py

# Plot results from a completed DOS calculation
python plot_dos.py <calc_pk>
python plot_dos.py <calc_pk> output.png  # Save to file
```

## Documentation

- [AiiDA Documentation](https://aiida.readthedocs.io/)
- [AiiDA-OLCAO Docs](https://aiida-olcao.readthedocs.io/)
- [OLCAO Source Code](https://github.com/UMKC-CPG/olcao)

## Development

```bash
# Run tests
hatch test

# Run tests with coverage
hatch test --cover

# Check code formatting
hatch fmt --check

# Build documentation
hatch run docs:build
```

## License

MIT

## Contact

Deepak Kumar Deo - dd9wn@umkc.edu

University of Missouri-Kansas City, Computational Physics Group

[ci-badge]: https://github.com/deepakdeo/AiiDA-OLCAO/actions/workflows/ci.yml/badge.svg?branch=main
[ci-link]: https://github.com/deepakdeo/AiiDA-OLCAO/actions/workflows/ci.yml
[cov-badge]: https://coveralls.io/repos/github/deepakdeo/AiiDA-OLCAO/badge.svg?branch=main
[cov-link]: https://coveralls.io/github/deepakdeo/AiiDA-OLCAO?branch=main
[docs-badge]: https://readthedocs.org/projects/aiida-olcao/badge
[docs-link]: https://aiida-olcao.readthedocs.io/
[pypi-badge]: https://badge.fury.io/py/AiiDA-OLCAO.svg
[pypi-link]: https://badge.fury.io/py/AiiDA-OLCAO
