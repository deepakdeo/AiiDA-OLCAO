"""Command line interface (CLI) for the aiida-olcao plugin."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click
from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import CalcJobNode, QueryBuilder, load_node

from aiida_olcao.data import OlcaoParameters


@click.group("olcao")
def cmd_root():
    """Commands for the aiida-olcao plugin."""


@click.command("list")
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Maximum number of nodes to show.",
)
@click.option(
    "--past-days",
    type=int,
    default=None,
    help="Only show nodes created within the last N days.",
)
@with_dbenv()
def list_(limit: int, past_days: int | None):
    """List recent OlcaoParameters nodes (input parameters)."""
    filters: dict = {}
    if past_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=past_days)
        filters["ctime"] = {">=": cutoff}

    qb = QueryBuilder()
    qb.append(
        OlcaoParameters,
        filters=filters or None,
        project=["id", "ctime"],
    )
    qb.order_by({OlcaoParameters: {"ctime": "desc"}})
    qb.limit(limit)

    rows = qb.all()
    if not rows:
        click.echo("No OlcaoParameters nodes found.")
        return

    click.echo(f"{'PK':>6}  {'CTIME (UTC)':19}")
    click.echo("-" * 28)

    for pk, ctime in rows:
        ctime_str = ctime.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        click.echo(f"{pk:>6}  {ctime_str:19}")


@click.command("results")
@click.option(
    "--limit",
    type=int,
    default=20,
    show_default=True,
    help="Maximum number of calculations to show.",
)
@click.option(
    "--past-days",
    type=int,
    default=None,
    help="Only show calculations from the last N days.",
)
@click.option(
    "--all-states",
    is_flag=True,
    default=False,
    help="Show calculations in all states (including running).",
)
@with_dbenv()
def results(limit: int, past_days: int | None, all_states: bool):
    """Show a summary table of OLCAO calculation results.

    Displays PK, label, calculation type, total energy, status, and date
    for all OlcaoCalculation jobs.

    \b
    Example output:
      PK  Label        Type    Energy (Ha)      Status      Date
    ----  -----------  ------  --------------   ----------  ----------
      57  diamond-dos  dos     -45.768046       Finished    2026-01-08
    """
    filters: dict = {"attributes.process_label": "OlcaoCalculation"}

    if past_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=past_days)
        filters["ctime"] = {">=": cutoff}

    if not all_states:
        # Only show finished or failed calculations by default
        filters["attributes.process_state"] = {"in": ["finished", "excepted", "killed"]}

    qb = QueryBuilder()
    qb.append(
        CalcJobNode,
        filters=filters,
        project=["id", "label", "ctime", "attributes.process_state", "attributes.exit_status"],
        tag="calc",
    )
    qb.order_by({"calc": {"ctime": "desc"}})
    qb.limit(limit)

    rows = qb.all()
    if not rows:
        click.echo("No OLCAO calculations found.")
        if not all_states:
            click.echo("Tip: Use --all-states to include running calculations.")
        return

    # Print header
    click.echo()
    click.echo(f"{'PK':>6}  {'Label':<16}  {'Type':<6}  {'Energy (Ha)':<14}  {'Status':<12}  {'Date':<10}")
    click.echo("-" * 6 + "  " + "-" * 16 + "  " + "-" * 6 + "  " + "-" * 14 + "  " + "-" * 12 + "  " + "-" * 10)

    for pk, raw_label, ctime, process_state, exit_status in rows:
        # Get calculation details
        calc_type, energy, status = _get_calc_details(pk, process_state, exit_status)

        # Format label (truncate if needed, use skeleton name as fallback)
        display_label = raw_label if raw_label else _get_skeleton_name(pk)
        display_label = (display_label[:14] + "..") if len(display_label) > 16 else display_label

        # Format date
        date_str = ctime.strftime("%Y-%m-%d")

        # Format energy
        energy_str = f"{energy:.6f}" if energy is not None else "-"

        click.echo(f"{pk:>6}  {display_label:<16}  {calc_type:<6}  {energy_str:<14}  {status:<12}  {date_str:<10}")

    click.echo()


def _get_calc_details(pk: int, process_state: str, exit_status: int | None) -> tuple[str, float | None, str]:
    """Get calculation type, energy, and status for a calculation node.

    Parameters
    ----------
    pk : int
        Primary key of the CalcJobNode.
    process_state : str
        The process state (finished, running, etc.).
    exit_status : int or None
        The exit status code.

    Returns
    -------
    tuple[str, float | None, str]
        Calculation type, total energy, and human-readable status.
    """
    calc_type = "scf"
    energy = None
    status = process_state.capitalize() if process_state else "Unknown"

    try:
        node = load_node(pk)

        # Get calculation type from parameters
        if "parameters" in node.inputs:
            params = node.inputs.parameters.get_dict()
            calc_type = params.get("calculation_type", "scf")

        # Determine status
        if process_state == "finished":
            if exit_status == 0:
                status = "Finished"
            elif exit_status == 302:
                status = "NotConverged"
            elif exit_status == 303:
                status = "SCF Failed"
            elif exit_status == 310:
                status = "InputFailed"
            else:
                status = f"Failed({exit_status})"
        elif process_state == "excepted":
            status = "Excepted"
        elif process_state == "killed":
            status = "Killed"
        elif process_state == "running":
            status = "Running"
        elif process_state == "waiting":
            status = "Waiting"

        # Get energy from output parameters
        if "output_parameters" in node.outputs:
            output = node.outputs.output_parameters.get_dict()
            energy = output.get("total_energy")

    except Exception:
        pass

    return calc_type, energy, status


def _get_skeleton_name(pk: int) -> str:
    """Get the skeleton filename for a calculation.

    Parameters
    ----------
    pk : int
        Primary key of the CalcJobNode.

    Returns
    -------
    str
        The skeleton filename or a default string.
    """
    try:
        node = load_node(pk)
        if "skeleton" in node.inputs:
            return node.inputs.skeleton.filename or "skeleton"
    except Exception:
        pass
    return f"calc-{pk}"


@click.command("export")
@click.argument("pk", type=int)
@click.option(
    "--out",
    "outdir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory where parameters will be exported.",
)
@click.option("--subdir/--no-subdir", default=True, show_default=True, help="Export into a dedicated subfolder.")
@with_dbenv()
def export(pk: int, outdir: Path, subdir: bool):
    """Export an OlcaoParameters node to a local directory."""
    node = load_node(pk)

    if not isinstance(node, OlcaoParameters):
        raise click.ClickException(f"Node<{pk}> is not an OlcaoParameters node (got {type(node)}).")

    target = (outdir / f"olcao_parameters_{pk}") if subdir else outdir
    target.mkdir(parents=True, exist_ok=True)

    params = node.get_dict()
    if not params:
        click.echo(f"OlcaoParameters<{pk}> is empty.")
        return

    for key in sorted(params):
        click.echo(f"{key}: {params[key]}")


# Register subcommands under the group
cmd_root.add_command(list_)
cmd_root.add_command(results)
cmd_root.add_command(export)

# IMPORTANT: alias for pyproject entry point convenience
olcao = cmd_root
