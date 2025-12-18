"""Command line interface (CLI) for the aiida-olcao plugin."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import CalcJobNode, QueryBuilder, load_node
from aiida.plugins import CalculationFactory

ENTRY_POINT_CALC = "olcao"


def _get_olcao_process_type() -> str:
    """Get the process_type string for the OLCAO CalcJob.

    Prefer deriving it from the registered Calculation entry point.
    Fall back to 'aiida.calculations:olcao' if anything goes wrong.
    """
    fallback = f"aiida.calculations:{ENTRY_POINT_CALC}"
    try:
        cls = CalculationFactory(ENTRY_POINT_CALC)
        return getattr(cls, "process_type", fallback)
    except Exception:
        return fallback


@click.group("olcao")
def cmd_root():
    """Commands for the aiida-olcao plugin."""


@click.command("list")
@click.option("--limit", type=int, default=20, show_default=True, help="Maximum number of OLCAO CalcJobs to show.")
@click.option("--past-days", type=int, default=None, help="Only show CalcJobs created within the last N days.")
@with_dbenv()
def list_(limit: int, past_days: int | None):
    """List recent OLCAO CalcJob nodes."""
    process_type = _get_olcao_process_type()

    filters: dict = {"process_type": {"==": process_type}}
    if past_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=past_days)
        filters["ctime"] = {">=": cutoff}

    qb = QueryBuilder()
    qb.append(
        CalcJobNode,
        filters=filters,
        project=["id", "ctime", "process_state", "exit_status"],
        order_by={CalcJobNode: {"ctime": "desc"}},
        limit=limit,
    )

    rows = qb.all()
    if not rows:
        click.echo("No OLCAO CalcJobs found.")
        return

    click.echo(f"{'PK':>6}  {'CTIME (UTC)':19}  {'STATE':12}  {'EXIT':>5}")
    click.echo("-" * 52)

    for pk, ctime, state, exit_status in rows:
        ctime_str = ctime.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        state_str = str(state) if state is not None else "-"
        exit_str = str(exit_status) if exit_status is not None else "-"
        click.echo(f"{pk:>6}  {ctime_str:19}  {state_str:12}  {exit_str:>5}")


@click.command("export")
@click.argument("pk", type=int)
@click.option(
    "--out",
    "outdir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("."),
    show_default=True,
    help="Directory where retrieved files will be exported.",
)
@click.option("--subdir/--no-subdir", default=True, show_default=True, help="Export into a dedicated subfolder.")
@with_dbenv()
def export(pk: int, outdir: Path, subdir: bool):
    """Export the retrieved output files of an OLCAO CalcJob to a local directory."""
    node = load_node(pk)

    if not isinstance(node, CalcJobNode):
        raise click.ClickException(f"Node<{pk}> is not a CalcJobNode (got {type(node)}).")

    expected = _get_olcao_process_type()
    if node.process_type != expected:
        raise click.ClickException(f"Node<{pk}> is not an OLCAO CalcJob (process_type={node.process_type}).")

    try:
        retrieved = node.outputs.retrieved
    except Exception as exc:
        raise click.ClickException(f"CalcJob<{pk}> has no 'retrieved' output: {exc}") from exc

    target = (outdir / f"olcao_export_{pk}") if subdir else outdir
    target.mkdir(parents=True, exist_ok=True)

    names = retrieved.base.repository.list_object_names()
    if not names:
        click.echo(f"No files to export for CalcJob<{pk}>.")
        return

    exported = 0
    for name in names:
        dest = target / name
        dest.parent.mkdir(parents=True, exist_ok=True)

        content = retrieved.base.repository.get_object_content(name, mode="rb")
        if isinstance(content, (bytes, bytearray)):
            dest.write_bytes(content)
        else:
            dest.write_bytes(content.read())

        exported += 1

    click.echo(f"Exported {exported} file(s) to: {target.resolve()}")


# Register subcommands under the group
cmd_root.add_command(list_)
cmd_root.add_command(export)

# IMPORTANT: alias for pyproject entry point convenience
olcao = cmd_root
