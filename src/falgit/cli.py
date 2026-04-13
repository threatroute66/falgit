"""CLI interface for falgit."""

from __future__ import annotations

import sys
from datetime import datetime, timezone

import click
from falkordb import FalkorDB

from falgit.errors import FalgitError
from falgit.models.types import OpType
from falgit.repo import FalgitRepo


def _connect(host: str, port: int) -> FalkorDB:
    return FalkorDB(host=host, port=port)


@click.group()
@click.version_option(package_name="falgit")
def main():
    """Git-like version control for FalkorDB graphs."""


@main.command()
@click.argument("graph")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST", help="FalkorDB host.")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT", help="FalkorDB port.")
def init(graph: str, host: str, port: int):
    """Initialize falgit tracking on a graph."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo.init(db, graph)
        click.echo(f"Initialized falgit tracking on graph '{graph}'.")
        click.echo(f"Initial commit created with {len(repo.log())} commit(s).")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.option("-m", "--message", required=True, help="Commit message.")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def commit(graph: str, message: str, host: str, port: int):
    """Commit the current graph state."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        c = repo.commit(message)
        click.echo(f"[{c.branch} {c.commit_id}] {c.message}")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.option("--limit", default=20, type=int, help="Max commits to show.")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def log(graph: str, limit: int, host: str, port: int):
    """Show commit history."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        commits = repo.log(limit=limit)
        if not commits:
            click.echo("No commits yet.")
            return
        for c in commits:
            ts = datetime.fromtimestamp(c.timestamp, tz=timezone.utc).strftime(
                "%Y-%m-%d %H:%M:%S UTC"
            )
            snap_marker = " [snapshot]" if c.has_snapshot else ""
            click.echo(f"commit {c.commit_id}{snap_marker}")
            click.echo(f"  Branch: {c.branch}")
            click.echo(f"  Date:   {ts}")
            click.echo(f"  {c.message}")
            click.echo()
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def status(graph: str, host: str, port: int):
    """Show changes since last commit."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        s = repo.status()
        if s.is_clean:
            click.echo("Nothing changed since last commit.")
            return
        click.echo(f"Changes since last commit ({s.total_changes} total):")
        if s.added_nodes:
            click.echo(f"  Added nodes:    {len(s.added_nodes)}")
        if s.deleted_nodes:
            click.echo(f"  Deleted nodes:  {len(s.deleted_nodes)}")
        if s.modified_nodes:
            click.echo(f"  Modified nodes: {len(s.modified_nodes)}")
        if s.added_edges:
            click.echo(f"  Added edges:    {len(s.added_edges)}")
        if s.deleted_edges:
            click.echo(f"  Deleted edges:  {len(s.deleted_edges)}")
        if s.modified_edges:
            click.echo(f"  Modified edges: {len(s.modified_edges)}")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.argument("commit_a", required=False)
@click.argument("commit_b", required=False)
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def diff(graph: str, commit_a: str | None, commit_b: str | None, host: str, port: int):
    """Show differences between commits or current state."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        ops = repo.diff(commit_a, commit_b)
        if not ops:
            click.echo("No differences.")
            return
        for op in ops:
            _print_diff_op(op)
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.argument("commit_id")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def checkout(graph: str, commit_id: str, host: str, port: int):
    """Restore graph to a previous commit state."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        repo.checkout(commit_id)
        click.echo(f"Graph '{graph}' restored to commit {commit_id}.")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command("branch")
@click.argument("graph")
@click.argument("name")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def create_branch(graph: str, name: str, host: str, port: int):
    """Create a new branch."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        b = repo.branch(name)
        click.echo(f"Branch '{b.name}' created at {b.head_commit_id}.")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def branches(graph: str, host: str, port: int):
    """List all branches."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        for b in repo.list_branches():
            marker = "* " if b.is_active else "  "
            click.echo(f"{marker}{b.name} -> {b.head_commit_id or '(no commits)'}")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.argument("branch_name")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def switch(graph: str, branch_name: str, host: str, port: int):
    """Switch to a different branch."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        repo.switch(branch_name)
        click.echo(f"Switched to branch '{branch_name}'.")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("graph")
@click.argument("branch_name")
@click.option("--host", default="localhost", envvar="FALKORDB_HOST")
@click.option("--port", default=6379, type=int, envvar="FALKORDB_PORT")
def merge(graph: str, branch_name: str, host: str, port: int):
    """Merge a branch into the active branch."""
    try:
        db = _connect(host, port)
        repo = FalgitRepo(db, graph)
        result = repo.merge(branch_name)
        click.echo(
            f"Merged '{result.source_branch}' into '{result.target_branch}'."
        )
        click.echo(f"Merge commit: {result.commit.commit_id}")
        if result.auto_resolved:
            click.echo(f"Auto-resolved {result.auto_resolved} overlapping change(s).")
    except FalgitError as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


def _print_diff_op(op):
    """Pretty-print a single DiffOp."""
    symbols = {
        OpType.ADD_NODE: "+",
        OpType.DEL_NODE: "-",
        OpType.MOD_NODE: "~",
        OpType.ADD_EDGE: "+",
        OpType.DEL_EDGE: "-",
        OpType.MOD_EDGE: "~",
    }
    symbol = symbols.get(op.op, "?")
    kind = "node" if "NODE" in op.op.value else "edge"

    click.echo(f"  {symbol} [{kind}] {op.element_key}")
    if op.data:
        if "labels" in op.data:
            click.echo(f"    labels: {op.data['labels']}")
        if "rel_type" in op.data:
            click.echo(f"    type: {op.data['rel_type']}")
        if "props" in op.data:
            click.echo(f"    props: {op.data['props']}")
    if op.old_data and op.op in (OpType.MOD_NODE, OpType.MOD_EDGE):
        click.echo(f"    was:  {op.old_data.get('props', {})}")
        click.echo(f"    now:  {op.data.get('props', {}) if op.data else {}}")
