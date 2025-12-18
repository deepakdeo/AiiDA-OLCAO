"""Calculation job plugin for OLCAO (minimal but robust)."""

from __future__ import annotations

from typing import Any

from aiida import orm
from aiida.common import CalcInfo, CodeInfo
from aiida.engine import CalcJob
from aiida.orm import AbstractCode

from .data.data import OlcaoParameters  # safest import (no reliance on __init__.py exports)
from .helpers import get_input_filename, get_output_filename


class OlcaoCalculation(CalcJob):
    """AiiDA CalcJob plugin to run the OLCAO code."""

    @classmethod
    def define(cls, spec):
        super().define(spec)

        # --- Inputs ---
        spec.input(
            "code",
            valid_type=AbstractCode,
            help="The OLCAO executable as an AiiDA Code (InstalledCode/PortableCode/etc.).",
        )
        spec.input(
            "input_file",
            valid_type=orm.SinglefileData,
            help="The OLCAO input file to be provided to the executable via STDIN.",
        )
        spec.input(
            "parameters",
            valid_type=OlcaoParameters,
            required=False,
            help="Optional OLCAO parameters as an OlcaoParameters node (queryable + provenance tracked).",
        )

        # --- Parser ---
        spec.input("metadata.options.parser_name", valid_type=str, default="olcao")

        # --- Filenames ---
        spec.input("metadata.options.input_filename", valid_type=str, default=get_input_filename())
        spec.input("metadata.options.output_filename", valid_type=str, default=get_output_filename())

        # --- REQUIRED for CalcJob validation (set safe defaults) ---
        # Without this, engine.run(builder) fails unless the user sets resources explicitly.
        spec.input(
            "metadata.options.resources",
            valid_type=dict,
            default={"num_machines": 1, "num_mpiprocs_per_machine": 1},
            help="Scheduler resources. Defaults to 1 machine, 1 MPI proc.",
        )
        spec.input(
            "metadata.options.max_wallclock_seconds",
            valid_type=int,
            default=3600,
            help="Maximum wallclock time in seconds.",
        )

        # --- Scheduler stdout/stderr (optional convenience) ---
        spec.input("metadata.options.scheduler_stdout", valid_type=str, default="_scheduler-stdout.txt")
        spec.input("metadata.options.scheduler_stderr", valid_type=str, default="_scheduler-stderr.txt")
        spec.input(
            "metadata.options.retrieve_scheduler_output",
            valid_type=bool,
            default=False,  # safest default: don't fail if scheduler files aren't present
            help="If True, also retrieve scheduler stdout/stderr files.",
        )

        # --- Extra retrieval hooks (extension point) ---
        spec.input(
            "metadata.options.additional_retrieve_list",
            valid_type=(list, tuple),
            required=False,
            help="Extra files/folders to retrieve (in addition to the main output).",
        )

        # --- Outputs ---
        spec.output(
            "output_parameters",
            valid_type=orm.Dict,
            help="Parsed results extracted from the OLCAO output.",
        )

    def prepare_for_submission(self, folder):
        """Create input files and instructions to run the code."""
        # IMPORTANT:
        # Use `self.node.get_option(...)` to read the *actual* stored options.
        # This is more robust than relying on `self.inputs.metadata.options.get(...)`.
        input_filename = self.node.get_option("input_filename") or get_input_filename()
        output_filename = self.node.get_option("output_filename") or get_output_filename()

        scheduler_stdout = self.node.get_option("scheduler_stdout") or "_scheduler-stdout.txt"
        scheduler_stderr = self.node.get_option("scheduler_stderr") or "_scheduler-stderr.txt"
        retrieve_scheduler_output = bool(self.node.get_option("retrieve_scheduler_output") or False)

        additional_retrieve_raw: Any = self.node.get_option("additional_retrieve_list") or []
        if additional_retrieve_raw is None:
            additional_retrieve = []
        elif isinstance(additional_retrieve_raw, (list, tuple)):
            additional_retrieve = list(additional_retrieve_raw)
        else:
            raise ValueError("metadata.options.additional_retrieve_list must be a list/tuple (or omitted).")

        # Basic content validation (keep it simple and strict for now)
        for item in additional_retrieve:
            if not isinstance(item, (str, tuple)):
                raise ValueError(
                    "Each element of additional_retrieve_list must be a string (filename) "
                    "or a tuple in AiiDA-supported retrieve_list format."
                )

        # Stage the provided input file into the sandbox
        with self.inputs.input_file.open(mode="rb") as handle:
            folder.create_file_from_filelike(handle, input_filename)

        codeinfo = CodeInfo()
        codeinfo.code_uuid = self.inputs.code.uuid
        codeinfo.stdin_name = input_filename
        codeinfo.stdout_name = output_filename

        calcinfo = CalcInfo()
        calcinfo.codes_info = [codeinfo]

        # Build retrieve list (unique, stable order)
        retrieve_list: list[Any] = [output_filename]

        if retrieve_scheduler_output:
            retrieve_list.extend([scheduler_stdout, scheduler_stderr])

        retrieve_list.extend(additional_retrieve)

        # Deduplicate while preserving order
        seen = set()
        unique_retrieve_list: list[Any] = []
        for item in retrieve_list:
            key = item if isinstance(item, str) else repr(item)
            if key not in seen:
                seen.add(key)
                unique_retrieve_list.append(item)

        calcinfo.retrieve_list = unique_retrieve_list
        return calcinfo
