"""Command line interface (CLI) for the aiida-olcao plugin."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import click

from aiida.cmdline.utils.decorators import with_dbenv
from aiida.orm import QueryBuilder, load_node

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
    help="Maximum number of OLCAO parameter nodes to show.",
)
@click.option(
    "--past-days",
    type=int,
    default=None,
    help="Only show parameter nodes created within the last N days.",
)
@with_dbenv()
def list_(limit: int, past_days: int | None):
    """List recent OLCAO parameter nodes."""
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
        click.echo("No OLCAO parameter nodes found.")
        return

    click.echo(f"{'PK':>6}  {'CTIME (UTC)':19}")
    click.echo("-" * 28)

    for pk, ctime in rows:
        ctime_str = ctime.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        click.echo(f"{pk:>6}  {ctime_str:19}")


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
    """Export an OLCAO parameter node to a local directory."""
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
cmd_root.add_command(export)

# IMPORTANT: alias for pyproject entry point convenience
olcao = cmd_root
