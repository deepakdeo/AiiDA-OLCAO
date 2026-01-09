# AiiDA-OLCAO: Complete Project Handoff

**Last Updated:** January 8, 2026  
**For:** Claude Code CLI or any fresh AI session

---

## Project Location

```
/Users/deo/UMKC_phd/OPT_DS/aiida-olcao/AiiDA-OLCAO
```

---

## Project Goal

This is an AiiDA plugin for OLCAO (Orthogonalized Linear Combination of Atomic Orbitals), a DFT code for electronic structure calculations developed at UMKC. The plugin enables:

- Automated job submission to HPC clusters
- Full data provenance tracking
- Reproducible computational workflows
- High-throughput calculation screening

---

## PART 1: CODE STATE

### Entry Points (pyproject.toml) ✅

```toml
[project.entry-points."aiida.data"]
"olcao" = "aiida_olcao.data.data:OlcaoParameters"

[project.entry-points."aiida.calculations"]
"olcao" = "aiida_olcao.calculations:OlcaoCalculation"

[project.entry-points."aiida.parsers"]
"olcao" = "aiida_olcao.parsers:OlcaoParser"

[project.entry-points."aiida.cmdline.data"]
"olcao" = "aiida_olcao.cli:olcao"
```

### Current File Status

| File | Status | Notes |
|------|--------|-------|
| `src/aiida_olcao/data/data.py` | ⚠️ Needs update | Add validation for OLCAO parameters |
| `src/aiida_olcao/calculations.py` | ⚠️ Needs update | Generic now, needs OLCAO-specific logic |
| `src/aiida_olcao/parsers.py` | ⚠️ Needs update | Basic, needs to parse OLCAO outputs |
| `src/aiida_olcao/cli.py` | ✅ Working | `verdi data olcao list/export` |
| `src/aiida_olcao/helpers.py` | ✅ Working | Filename helpers |
| `tests/test_calculations.py` | ✅ Working | Uses input_file fixture |
| `conftest.py` | ✅ Working | Uses /bin/cat for CI |
| `README.md` | ✅ Updated | OLCAO-specific content |

### What NOT to Reintroduce ⚠️

- Don't use `file1/file2` inputs — use `input_file` or `skeleton`
- Don't refer to `DiffParameters` or `DiffCalculation`
- Don't make CLI operate on CalcJobNode for `verdi data olcao`

---

## PART 2: INFRASTRUCTURE STATE (Hellbender HPC) ✅ COMPLETE

### AiiDA Configuration

```bash
# Verify with:
verdi status          # Should show all green
verdi computer list   # Should show 'hellbender'
verdi code list       # Should show 'olcao@hellbender', 'makeinput@hellbender'
```

### Hellbender Computer ✅

- **Label:** `hellbender`
- **Hostname:** `hellbender.rnet.missouri.edu`
- **Transport:** `core.ssh`
- **Scheduler:** `core.slurm`
- **Work directory:** `/home/dd9wn/data/scratch/aiida_work`
- **SSH key:** `~/.ssh/id_ed25519`
- **Username:** `dd9wn`

### OLCAO Codes ✅

| Code | PK | Path |
|------|-----|------|
| `olcao@hellbender` | 50 | `/home/dd9wn/olcao/bin/uolcao` |
| `makeinput@hellbender` | 51 | `/home/dd9wn/olcao/bin/makeinput` |

---

## PART 3: OLCAO WORKFLOW — CRITICAL DETAILS

### ⚠️ IMPORTANT: Input File Naming

**`makeinput` REQUIRES the skeleton file to be named EXACTLY `olcao.skl`**

The CalcJob must:
1. Accept any filename from user (e.g., `diamond.skl`, `my_structure.skl`)
2. Stage it to the remote as `olcao.skl`

```python
# In prepare_for_submission:
with self.inputs.skeleton.open(mode='rb') as handle:
    folder.create_file_from_filelike(handle, 'olcao.skl')  # MUST be this name
```

### ⚠️ IMPORTANT: Intermediate Files and $OLCAO_TEMP

OLCAO uses `$OLCAO_TEMP` environment variable for intermediate/checkpoint files.
Default: `/home/dd9wn/data/scratch/olcao`

**Problem:** This would scatter files outside AiiDA's control.

**Solution:** Override `$OLCAO_TEMP` in the job script to keep everything in AiiDA's sandbox:

```bash
# Prepend to job script:
source /home/dd9wn/olcao/.olcao/olcaorc
export OLCAO_TEMP="$(pwd)/olcao_scratch"
mkdir -p "$OLCAO_TEMP"
```

This ensures:
- All files stay in AiiDA's working directory
- Full provenance tracking of intermediate files
- No pollution of user's personal scratch space
- Reproducible across different users

### Two-Step Calculation Process

```
Step 1: makeinput -kp 5 5 5
        Input:  olcao.skl (MUST be this exact filename)
        Output: Creates these in current directory:
                - ./inputs/           (directory with processed inputs)
                - ./olcao.dat         (main control file)
                - ./structure.dat     (atomic positions)
                - ./kp-scf.dat        (SCF k-points)
                - ./kp-pscf.dat       (post-SCF k-points)
                - ./summary           (calculation summary)
                - ./slurm             (generated SLURM script)

Step 2: uolcao -dos (or -bond, -sybd, -optc, etc.)
        Input:  Files created by makeinput
        Output: Results files:
                - gs_*-fb.out         (main output with energies)
                - gs_enrg-fb.dat      (energy vs iteration)
                - gs_iter-fb.dat      (iteration details)
                - gs_dos-fb.t.plot    (total DOS)
                - gs_dos-fb.p.raw     (partial DOS raw data)
                - gs_scf-fb.hdf5      (HDF5 checkpoint)
                - gs_pscf-*.hdf5      (post-SCF HDF5 data)
                - ./intermediate/     (symlink to scratch, contains checkpoint files)
```

### Skeleton File Format (.skl)

```
title
<metadata - can be citation info>
end
cell
<a> <b> <c> <alpha> <beta> <gamma>    # Lattice params in Angstroms and degrees
fract <num_atoms>                      # Number of atoms, fractional coordinates
<Element> <x> <y> <z>
<Element> <x> <y> <z>
...
space <spacegroup_number>[_variant]    # e.g., 227_a, 186, 152_a
supercell <na> <nb> <nc>               # Supercell multipliers
full|prim                              # Full or primitive cell
```

**Example (diamond.skl):**
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

### makeinput Command Options

| Option | Description | Example |
|--------|-------------|---------|
| `-kp a b c` | K-point mesh for both SCF and PSCF | `-kp 5 5 5` |
| `-scfkp a b c` | K-point mesh for SCF only | `-scfkp 3 3 3` |
| `-pscfkp a b c` | K-point mesh for post-SCF only | `-pscfkp 7 7 7` |
| `-slurm` | Generate SLURM submission script | `-slurm` |
| `-q <queue>` | SLURM queue/partition | `-q general` |
| `-t <time>` | Wall time | `-t 02:00:00` |
| `-m <memory>` | Memory | `-m 10G` |
| `-n <cpus>` | Number of CPUs | `-n 4` |

### uolcao Command Options

| Flag | Calculation | Description | Default Basis |
|------|-------------|-------------|---------------|
| `-scf [basis]` | SCF only | Self-consistent field | FB |
| `-dos [edge]` | DOS | Density of states | SCF:FB, PSCF:FB |
| `-bond [edge]` | Bond order | Bond order analysis | SCF:FB, PSCF:MB |
| `-sybd [edge]` | Band structure | Symmetric band | FB |
| `-optc [edge]` | Optical | Optical properties (ε₁, ε₂, conductivity) | SCF:FB, PSCF:EB |
| `-pacs <edge>` | XANES | X-ray absorption (requires edge) | SCF:FB, PSCF:EB |
| `-field [edge]` | Field | Charge density, potential | FB |
| `-force [edge]` | Forces | Atomic forces (experimental) | FB |
| `-nlop [edge]` | Nonlinear optical | Nonlinear optical properties | SCF:FB, PSCF:EB |
| `-sige [edge]` | Sigma(E) | Optical transitions near Fermi | FB |
| `-loen` | Local environment | Bispectrum analysis | - |

**Basis options:** EB (Extended), FB (Full), MB (Minimal), NO (skip SCF)

**Edge options:** `gs` (ground state), `1s`, `2s`, `2p`, `3s`, `3p`, etc.

### Output Files to Retrieve

**Always retrieve:**
- `gs_*-fb.out` or `gs_*-eb.out` — Main output with energies
- `gs_enrg-*.dat` — Energy convergence data
- `gs_iter-*.dat` — Iteration data
- `summary` — Calculation summary
- `runtime` — Timing information

**Calculation-specific:**
| Calc Type | Additional Files |
|-----------|------------------|
| DOS | `gs_dos-*.t.plot`, `gs_dos-*.p.raw`, `gs_dos-*.loci.plot` |
| Band | `gs_sybd-*.plot`, `vdim-*.raw` |
| Optical | `gs_optc-*.t.plot`, `gs_optc-*.t.eps1.plot`, `gs_optc-*.t.eps2.plot`, `gs_optc-*.t.cond.plot` |
| Bond | `gs_bond-*.raw` |

**HDF5 files (large, optional):**
- `gs_scf-*.hdf5` — SCF checkpoint
- `gs_pscf-*.hdf5` — Post-SCF data

### OLCAO Environment Variables

```bash
$OLCAO_DIR    = /home/dd9wn/olcao           # Installation root
$OLCAO_BIN    = /home/dd9wn/olcao/bin       # Executables
$OLCAO_DATA   = /home/dd9wn/olcao/share     # Basis/potential data
$OLCAO_RC     = /home/dd9wn/olcao/.olcao    # Config directory
$OLCAO_TEMP   = /home/dd9wn/data/scratch/olcao  # Intermediate files (OVERRIDE THIS!)
$OLCAO_QUEUE  = 3                           # SLURM scheduler
```

---

## PART 4: DEVELOPMENT TASKS

### Task 1: Update OlcaoParameters ⬅️ CURRENT PRIORITY

Update `src/aiida_olcao/data/data.py`:

```python
class OlcaoParameters(orm.Dict):
    """OLCAO calculation parameters with validation."""
    
    # Parameters to validate:
    # - kpoints: list of 3 positive integers, default [1, 1, 1]
    # - kpoints_scf: optional, list of 3 positive integers (overrides kpoints for SCF)
    # - kpoints_pscf: optional, list of 3 positive integers (overrides kpoints for PSCF)
    # - calculation_type: str, one of: "scf", "dos", "bond", "sybd", "optc", "pacs", "field", "force", "nlop", "sige", "loen"
    #   default: "scf"
    # - basis_scf: str, one of "EB", "FB", "MB", default "FB"
    # - basis_pscf: str, one of "EB", "FB", "MB", default "FB"  
    # - edge: str, default "gs", can be "gs", "1s", "2s", "2p", "3s", "3p", etc.
    
    # Helper methods to implement:
    # - get_makeinput_cmdline() -> str
    #   Returns command line args for makeinput, e.g., "-kp 5 5 5" or "-scfkp 3 3 3 -pscfkp 7 7 7"
    #
    # - get_uolcao_cmdline() -> str  
    #   Returns command line args for uolcao, e.g., "-dos" or "-scf FB -bond gs"
    #
    # - validate() -> raises ValidationError if invalid
```

### Task 2: Update OlcaoCalculation

Update `src/aiida_olcao/calculations.py`:

**Inputs:**
- `code`: The OLCAO code (should point to a wrapper script, see below)
- `skeleton`: `SinglefileData` containing the .skl file
- `parameters`: `OlcaoParameters` with calculation settings

**Key implementation details:**
1. Stage skeleton file as `olcao.skl` (exact name required!)
2. The job script should:
   - Source olcaorc
   - Override `$OLCAO_TEMP` to `$(pwd)/olcao_scratch`
   - Run `makeinput` with parameters
   - Run `uolcao` with calculation type
3. Retrieve appropriate output files based on calculation type

**Simplified approach:** Create a wrapper script that runs both makeinput and uolcao:

```bash
#!/bin/bash
# olcao_wrapper.sh - runs complete OLCAO workflow
# Usage: olcao_wrapper.sh "<makeinput_args>" "<uolcao_args>"

source /home/dd9wn/olcao/.olcao/olcaorc
export OLCAO_TEMP="$(pwd)/olcao_scratch"
mkdir -p "$OLCAO_TEMP"

# Run makeinput
makeinput $1

# Run uolcao
uolcao $2
```

### Task 3: Update OlcaoParser

Update `src/aiida_olcao/parsers.py`:

Parse from `gs_*-*.out` files:
- Total energy (look for "TOTAL ENERGY")
- Fermi energy (look for "FERMI ENERGY") 
- Number of iterations
- Convergence status
- Number of atoms, electrons

Exit codes to define:
- 300: No retrieved folder
- 301: Missing output file
- 302: Calculation did not converge
- 303: SCF failed
- 310: makeinput failed (no inputs/ directory)

### Task 4: Create Integration Tests

Test with real skeleton files:
- `tests/input_files/diamond.skl`
- `tests/input_files/silicon.skl`

---

## PART 5: COMMANDS REFERENCE

### Development

```bash
hatch fmt --check    # Check formatting
hatch fmt            # Auto-fix formatting
hatch test --cover   # Run tests with coverage
rm -rf docs/build && hatch run docs:build  # Build docs
```

### AiiDA

```bash
verdi status              # Check AiiDA
verdi daemon restart      # Restart daemon
verdi computer test hellbender  # Test connection
verdi process list -a     # All processes
verdi process show <PK>   # Process details
verdi node show <PK>      # Node details
```

### Git

```bash
git status
git add -A
git commit -m "message"
git push origin main
```

---

## PART 6: EXAMPLE USAGE (Target API)

This is what we're building toward:

```python
from aiida.orm import load_code, SinglefileData
from aiida.engine import submit
from aiida.plugins import CalculationFactory, DataFactory

# Load plugin classes
OlcaoCalculation = CalculationFactory('olcao')
OlcaoParameters = DataFactory('olcao')

# Create builder
builder = OlcaoCalculation.get_builder()

# Set inputs
builder.code = load_code('olcao@hellbender')
builder.skeleton = SinglefileData('/path/to/diamond.skl')
builder.parameters = OlcaoParameters({
    'kpoints': [5, 5, 5],
    'calculation_type': 'dos',
    'basis_scf': 'FB',
    'basis_pscf': 'FB',
    'edge': 'gs'
})

# Set resources
builder.metadata.options.resources = {'num_machines': 1}
builder.metadata.options.max_wallclock_seconds = 3600

# Submit!
calc = submit(builder)
print(f'Submitted calculation: {calc.pk}')
```

---

## Contact

**Developer:** Deepak Kumar Deo  
**Email:** dd9wn@umkc.edu  
**Repository:** https://github.com/deepakdeo/AiiDA-OLCAO
