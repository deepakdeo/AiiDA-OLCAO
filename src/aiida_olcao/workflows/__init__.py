"""Workflows for OLCAO calculations.

This module provides WorkChains that orchestrate multiple OLCAO calculations.
The main workflow is :class:`OlcaoBaseWorkChain` which runs SCF followed by
one or more post-SCF calculations (DOS, bond order, optical properties, etc.).

Example
-------
>>> from aiida.engine import submit
>>> from aiida.orm import SinglefileData, load_code
>>> from aiida.plugins import WorkflowFactory
>>>
>>> OlcaoBaseWorkChain = WorkflowFactory('olcao.base')
>>> builder = OlcaoBaseWorkChain.get_builder()
>>> builder.code = load_code('olcao@hellbender')
>>> builder.skeleton = SinglefileData(file='diamond.skl')
>>> builder.kpoints = [5, 5, 5]
>>> builder.calculations = ['dos', 'bond']
>>> submit(builder)
"""

from __future__ import annotations

from aiida import orm
from aiida.common import AttributeDict
from aiida.engine import ToContext, WorkChain, calcfunction
from aiida.orm import AbstractCode
from aiida.plugins import CalculationFactory, DataFactory

# Use factories to load classes with registered entry points
# This is required for AiiDA to properly store nodes with provenance
OlcaoCalculation = CalculationFactory("olcao")
OlcaoParameters = DataFactory("olcao")

# Post-SCF calculation types (all except 'scf')
POST_SCF_TYPES = ("dos", "bond", "sybd", "optc", "pacs", "field", "force", "nlop", "sige", "loen")

# Recommended basis_pscf for each calculation type
RECOMMENDED_PSCF_BASIS = {
    "dos": "FB",  # Full basis for accurate DOS
    "bond": "MB",  # Minimal basis sufficient for bond order
    "sybd": "FB",  # Full basis for band structure
    "optc": "EB",  # Extended basis for optical properties
    "pacs": "EB",  # Extended basis for XANES
    "field": "FB",  # Full basis for charge density
    "force": "FB",  # Full basis for forces
    "nlop": "EB",  # Extended basis for nonlinear optical
    "sige": "FB",  # Full basis for sigma(E)
    "loen": "MB",  # Minimal basis for local environment
}


@calcfunction
def merge_outputs(**kwargs) -> orm.Dict:
    """Merge output parameters from multiple calculations.

    Parameters
    ----------
    kwargs : dict
        Named Dict nodes to merge (passed as keyword arguments).

    Returns
    -------
    orm.Dict
        Merged dictionary with all outputs.
    """
    merged = {}
    for name, node in kwargs.items():
        if isinstance(node, orm.Dict):
            merged[name] = node.get_dict()
    return orm.Dict(dict=merged)


class OlcaoBaseWorkChain(WorkChain):
    """AiiDA WorkChain to run OLCAO SCF followed by post-SCF calculations.

    This workflow provides a convenient way to run multiple OLCAO calculations
    on the same structure. It always starts with an SCF calculation to obtain
    the ground state, then runs any requested post-SCF calculations (DOS,
    bond order, optical properties, etc.).

    The workflow handles:

    * Running SCF first and checking convergence
    * Running multiple post-SCF calculations with appropriate settings
    * Collecting all outputs in a structured format
    """

    @classmethod
    def define(cls, spec):
        """Define the WorkChain specification."""
        super().define(spec)

        # --- Inputs ---
        spec.input(
            "code",
            valid_type=AbstractCode,
            help="The uolcao executable as an AiiDA Code.",
        )
        spec.input(
            "skeleton",
            valid_type=orm.SinglefileData,
            help="The OLCAO skeleton file (.skl).",
        )
        spec.input(
            "kpoints",
            valid_type=orm.List,
            help="K-point mesh as [a, b, c] integers.",
        )
        spec.input(
            "calculations",
            valid_type=orm.List,
            default=lambda: orm.List(list=["dos"]),
            help="List of post-SCF calculation types to run: 'dos', 'bond', 'sybd', 'optc', etc.",
        )
        spec.input(
            "basis_scf",
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str("FB"),
            help="Basis set for SCF: 'EB', 'FB', 'MB'. Default: 'FB'.",
        )
        spec.input(
            "basis_pscf",
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str("FB"),
            help="Default basis set for post-SCF. Can be overridden per calculation type.",
        )
        spec.input(
            "edge",
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str("gs"),
            help="Edge for excited state calculations: 'gs', '1s', '2p', etc. Default: 'gs'.",
        )

        # --- OLCAO-specific paths ---
        spec.input(
            "olcao_rc",
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str(OlcaoCalculation.DEFAULT_OLCAO_RC),
            help="Path to olcaorc file on remote.",
        )
        spec.input(
            "makeinput_path",
            valid_type=orm.Str,
            required=False,
            default=lambda: orm.Str(OlcaoCalculation.DEFAULT_MAKEINPUT_PATH),
            help="Path to makeinput executable on remote.",
        )

        # --- Computational options ---
        spec.input(
            "options",
            valid_type=orm.Dict,
            required=False,
            default=lambda: orm.Dict(
                dict={
                    "resources": {"num_machines": 1, "num_mpiprocs_per_machine": 1},
                    "max_wallclock_seconds": 3600,
                }
            ),
            help="Scheduler options (resources, wallclock time).",
        )

        # --- Workflow outline ---
        spec.outline(
            cls.setup,
            cls.run_scf,
            cls.inspect_scf,
            cls.run_post_scf,
            cls.results,
        )

        # --- Outputs ---
        spec.output(
            "scf_parameters",
            valid_type=orm.Dict,
            required=True,
            help="Parsed results from SCF calculation.",
        )
        spec.output_namespace(
            "post_scf_parameters",
            valid_type=orm.Dict,
            dynamic=True,
            help="Parsed results from post-SCF calculations.",
        )
        spec.output(
            "all_parameters",
            valid_type=orm.Dict,
            required=False,
            help="Merged dictionary of all calculation results.",
        )

        # --- Exit codes ---
        spec.exit_code(
            401,
            "ERROR_INVALID_CALCULATION_TYPE",
            message="Invalid calculation type requested: {calc_type}",
        )
        spec.exit_code(
            402,
            "ERROR_SCF_NOT_CONVERGED",
            message="SCF calculation did not converge.",
        )
        spec.exit_code(
            403,
            "ERROR_SCF_FAILED",
            message="SCF calculation failed with exit code {exit_status}.",
        )
        spec.exit_code(
            404,
            "ERROR_POST_SCF_FAILED",
            message="Post-SCF calculation '{calc_type}' failed with exit code {exit_status}.",
        )

    def setup(self):
        """Validate inputs and set up the workflow context."""
        self.report("Setting up OlcaoBaseWorkChain")

        # Validate requested calculation types
        requested_calcs = self.inputs.calculations.get_list()
        for calc_type in requested_calcs:
            if calc_type not in POST_SCF_TYPES:
                return self.exit_codes.ERROR_INVALID_CALCULATION_TYPE.format(calc_type=calc_type)

        # Store common settings in context
        self.ctx.kpoints = self.inputs.kpoints.get_list()
        self.ctx.basis_scf = self.inputs.basis_scf.value
        self.ctx.basis_pscf = self.inputs.basis_pscf.value
        self.ctx.edge = self.inputs.edge.value
        self.ctx.requested_calculations = requested_calcs

        # Store options
        options = self.inputs.options.get_dict()
        self.ctx.resources = options.get("resources", {"num_machines": 1})
        self.ctx.max_wallclock_seconds = options.get("max_wallclock_seconds", 3600)

        self.report(f"Will run SCF followed by: {', '.join(requested_calcs)}")

    def run_scf(self):
        """Submit the SCF calculation."""
        self.report("Submitting SCF calculation")

        # Create OlcaoParameters for SCF
        parameters = OlcaoParameters(
            {
                "kpoints": self.ctx.kpoints,
                "calculation_type": "scf",
                "basis_scf": self.ctx.basis_scf,
            }
        )

        # Build the calculation inputs
        inputs = AttributeDict(
            {
                "code": self.inputs.code,
                "skeleton": self.inputs.skeleton,
                "parameters": parameters,
                "olcao_rc": self.inputs.olcao_rc,
                "makeinput_path": self.inputs.makeinput_path,
                "metadata": {
                    "label": "scf",
                    "description": "SCF calculation from OlcaoBaseWorkChain",
                    "options": {
                        "resources": self.ctx.resources,
                        "max_wallclock_seconds": self.ctx.max_wallclock_seconds,
                    },
                },
            }
        )

        # Submit and return to context
        running = self.submit(OlcaoCalculation, **inputs)
        self.report(f"Submitted SCF calculation <{running.pk}>")

        return ToContext(scf_calc=running)

    def inspect_scf(self):
        """Check if SCF converged successfully."""
        scf_calc = self.ctx.scf_calc

        if not scf_calc.is_finished_ok:
            exit_status = scf_calc.exit_status
            self.report(f"SCF calculation failed with exit status {exit_status}")

            if exit_status == 302:
                return self.exit_codes.ERROR_SCF_NOT_CONVERGED
            return self.exit_codes.ERROR_SCF_FAILED.format(exit_status=exit_status)

        # Check convergence from output
        output_params = scf_calc.outputs.output_parameters.get_dict()
        if output_params.get("converged") is False:
            self.report("SCF did not converge according to output")
            return self.exit_codes.ERROR_SCF_NOT_CONVERGED

        self.report("SCF converged successfully")

        # Store SCF results
        self.ctx.scf_total_energy = output_params.get("total_energy")
        self.ctx.scf_fermi_energy = output_params.get("fermi_energy")

    def run_post_scf(self):
        """Submit all requested post-SCF calculations."""
        if not self.ctx.requested_calculations:
            self.report("No post-SCF calculations requested")
            return

        self.report(f"Submitting post-SCF calculations: {', '.join(self.ctx.requested_calculations)}")

        # Submit each post-SCF calculation
        calcs_to_submit = {}

        for calc_type in self.ctx.requested_calculations:
            # Determine basis_pscf for this calculation type
            # Use recommended basis if user specified default, otherwise use user's choice
            if self.ctx.basis_pscf == "FB" and calc_type in RECOMMENDED_PSCF_BASIS:
                basis_pscf = RECOMMENDED_PSCF_BASIS[calc_type]
            else:
                basis_pscf = self.ctx.basis_pscf

            # Create parameters for this calculation
            parameters = OlcaoParameters(
                {
                    "kpoints": self.ctx.kpoints,
                    "calculation_type": calc_type,
                    "basis_scf": self.ctx.basis_scf,
                    "basis_pscf": basis_pscf,
                    "edge": self.ctx.edge,
                }
            )

            # Build inputs
            inputs = AttributeDict(
                {
                    "code": self.inputs.code,
                    "skeleton": self.inputs.skeleton,
                    "parameters": parameters,
                    "olcao_rc": self.inputs.olcao_rc,
                    "makeinput_path": self.inputs.makeinput_path,
                    "metadata": {
                        "label": calc_type,
                        "description": f"{calc_type.upper()} calculation from OlcaoBaseWorkChain",
                        "options": {
                            "resources": self.ctx.resources,
                            "max_wallclock_seconds": self.ctx.max_wallclock_seconds,
                        },
                    },
                }
            )

            # Submit
            running = self.submit(OlcaoCalculation, **inputs)
            self.report(f"Submitted {calc_type.upper()} calculation <{running.pk}> with basis_pscf={basis_pscf}")
            calcs_to_submit[f"post_scf_{calc_type}"] = running

        # Return all to context
        return ToContext(**calcs_to_submit)

    def results(self):
        """Gather results from all calculations."""
        self.report("Gathering results")

        # Output SCF parameters
        self.out("scf_parameters", self.ctx.scf_calc.outputs.output_parameters)

        # Collect all outputs for merging
        all_outputs = {"scf": self.ctx.scf_calc.outputs.output_parameters}

        # Output post-SCF parameters
        for calc_type in self.ctx.requested_calculations:
            ctx_key = f"post_scf_{calc_type}"
            if ctx_key in self.ctx:
                post_calc = self.ctx[ctx_key]

                if not post_calc.is_finished_ok:
                    exit_status = post_calc.exit_status
                    self.report(f"Warning: {calc_type.upper()} failed with exit status {exit_status}")
                    # Don't fail the whole workflow, just report
                    continue

                # Output to namespace
                self.out(f"post_scf_parameters.{calc_type}", post_calc.outputs.output_parameters)
                all_outputs[calc_type] = post_calc.outputs.output_parameters

        # Create merged output
        if all_outputs:
            merged = merge_outputs(**all_outputs)
            self.out("all_parameters", merged)

        self.report("OlcaoBaseWorkChain completed successfully")
