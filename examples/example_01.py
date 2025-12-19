#!/usr/bin/env python
"""Run a test calculation on localhost using ``dummy_olcao.sh``.

Usage: ./example_01.py
"""

from pathlib import Path

import click
from aiida import cmdline, engine
from aiida.common import exceptions
from aiida.orm import Computer, InstalledCode, SinglefileData, load_code, load_computer
from aiida.plugins import CalculationFactory, DataFactory

REPO_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_DIR = Path(__file__).resolve().parent
if not (EXAMPLE_DIR / "input_files").is_dir():
    EXAMPLE_DIR = Path.cwd() / "examples"
INPUT_DIR = EXAMPLE_DIR / "input_files"
DUMMY_EXE = REPO_ROOT / "dummy_olcao.sh"


def get_or_create_local_computer(label: str = "localhost") -> Computer:
    """Return a local computer, creating it if needed."""
    try:
        return load_computer(label)
    except exceptions.NotExistent:
        workdir = Path.home() / "aiida_workdir"
        workdir.mkdir(parents=True, exist_ok=True)
        computer = Computer(
            label=label,
            hostname="localhost",
            transport_type="core.local",
            scheduler_type="core.direct",
            workdir=str(workdir),
        )
        computer.store()
        try:
            computer.configure()
        except Exception:
            pass
        return computer


def get_or_create_code(label: str = "olcao-dummy", computer_label: str = "localhost") -> InstalledCode:
    """Return a local code for the dummy OLCAO script, creating it if needed."""
    full_label = f"{label}@{computer_label}"
    try:
        return load_code(full_label)
    except exceptions.NotExistent:
        computer = get_or_create_local_computer(computer_label)
        code = InstalledCode(
            label=label,
            computer=computer,
            filepath_executable=str(DUMMY_EXE),
            default_calc_job_plugin="olcao",
        )
        code.store()
        return code


def test_run(olcao_code):
    """Run a calculation on the localhost computer."""
    if not olcao_code:
        olcao_code = get_or_create_code()

    parameters = DataFactory("olcao")({"dummy": True})
    input_file = SinglefileData(file=str(INPUT_DIR / "file1.txt"))

    inputs = {
        "code": olcao_code,
        "parameters": parameters,
        "input_file": input_file,
        "metadata": {
            "description": "Hello-world run using the dummy OLCAO executable",
            "options": {"max_wallclock_seconds": 30},
        },
    }

    result = engine.run(CalculationFactory("olcao"), **inputs)
    output_parameters = result["output_parameters"].get_dict()
    print("output_parameters:")
    print(output_parameters)


@click.command()
@cmdline.utils.decorators.with_dbenv()
@cmdline.params.options.CODE()
def cli(code):
    """Run example.

    Example usage: $ ./example_01.py --code olcao-dummy@localhost

    Alternative (creates olcao-dummy@localhost code): $ ./example_01.py

    Help: $ ./example_01.py --help
    """
    test_run(code)


if __name__ == "__main__":
    cli()  # pylint: disable=no-value-for-parameter
