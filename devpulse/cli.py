"""DevPulse CLI — Click-based command-line interface."""

import os
import subprocess
import sys

import click


def _gather_data():
    """Collect all data needed by dashboard/motd/prioritizer.

    Returns a tuple of (config, git_results, phase_results, blockers, tasks,
    focus_items).
    """
    from devpulse.config import load_projects
    from devpulse.git_scanner import scan_all
    from devpulse.phase_tracker import (
        compute_progress,
        extract_blockers,
        extract_tasks,
        get_phase_counts,
    )
    from devpulse.prioritizer import prioritize

    config = load_projects()

    # scan_all returns a list; convert to dict keyed by project name
    scan_list = scan_all(config)
    git_results = {}
    for scan in scan_list:
        git_results[scan["project"]] = scan

    # Build phase_results dict
    phase_results = {}
    for name, proj in config.get("projects", {}).items():
        phases = proj.get("phases", [])
        counts = get_phase_counts(phases)
        phase_results[name] = {
            "percentage": compute_progress(phases),
            "total": len(phases),
            "complete": counts.get("complete", 0),
            "in_progress": counts.get("in_progress", 0),
            "blocked": counts.get("blocked", 0),
            "not_started": counts.get("not_started", 0),
        }

    blockers = extract_blockers(config)
    tasks = extract_tasks(config)
    focus_items = prioritize(phase_results, git_results, config)

    return config, git_results, phase_results, blockers, tasks, focus_items


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx):
    """DevPulse -- Engineering Command Center.

    Run without a subcommand to launch the full dashboard.
    """
    if ctx.invoked_subcommand is None:
        ctx.invoke(dashboard)


@cli.command()
def dashboard():
    """Launch the full Rich TUI dashboard."""
    from devpulse.dashboard import render_dashboard

    config, git_results, phase_results, blockers, tasks, focus_items = (
        _gather_data()
    )

    render_dashboard(
        config=config,
        git_results=git_results,
        phase_results=phase_results,
        blockers=blockers,
        tasks=tasks,
        focus_items=focus_items,
    )


@cli.command()
def brief():
    """Show compact MOTD summary (8-10 lines)."""
    from devpulse.motd import render_motd

    config, git_results, phase_results, blockers, tasks, focus_items = (
        _gather_data()
    )

    render_motd(
        config=config,
        blockers=blockers,
        tasks=tasks,
        focus_items=focus_items,
    )


@cli.command()
def status():
    """Show git status table for all projects."""
    from rich.console import Console
    from rich.table import Table

    from devpulse.config import load_projects
    from devpulse.git_scanner import scan_all

    console = Console()
    config = load_projects()

    # scan_all returns a list; convert to dict keyed by project name
    scan_list = scan_all(config)
    git_results = {s["project"]: s for s in scan_list}

    table = Table(title="Project Git Status", border_style="bright_blue")
    table.add_column("Project", style="bold cyan")
    table.add_column("Branch", style="green")
    table.add_column("Status")
    table.add_column("Last Commit", style="dim")

    for name, proj in config.get("projects", {}).items():
        display = proj.get("display_name", name)
        scan = git_results.get(name)

        if scan is None:
            table.add_row(display, "-", "[dim]no path[/dim]", "-")
            continue

        if scan.get("error"):
            table.add_row(display, "-", f"[red]{scan['error']}[/red]", "-")
            continue

        branch = scan.get("branch", "?")

        if scan.get("clean", True):
            status_str = "[green]clean[/green]"
        else:
            parts = []
            mod = scan.get("modified", 0)
            unt = scan.get("untracked", 0)
            if mod:
                parts.append(f"{mod} modified")
            if unt:
                parts.append(f"{unt} untracked")
            status_str = f"[yellow]{', '.join(parts) or 'dirty'}[/yellow]"

        unpushed = scan.get("unpushed", 0)
        if unpushed:
            status_str += f" [red]+{unpushed} unpushed[/red]"

        last = scan.get("last_commit_msg", "") or ""
        date = scan.get("last_commit_date", "") or ""
        # Show just the date portion if ISO format
        if date and "T" in date:
            date = date.split("T")[0]
        commit_str = f"{date} {last}" if date else last
        if len(commit_str) > 50:
            commit_str = commit_str[:47] + "..."

        table.add_row(display, branch, status_str, commit_str)

    console.print()
    console.print(table)
    console.print()


@cli.command()
def phases():
    """Show phase progress bars for all projects."""
    from rich.console import Console
    from rich.table import Table

    from devpulse.config import load_projects
    from devpulse.phase_tracker import compute_progress, get_phase_counts

    console = Console()
    config = load_projects()

    table = Table(show_header=True, border_style="bright_blue", title="Phase Progress")
    table.add_column("Project", style="bold cyan", min_width=20)
    table.add_column("Progress", min_width=24)
    table.add_column("%", justify="right", min_width=5)
    table.add_column("Current Phase", min_width=30)

    for name, proj in config.get("projects", {}).items():
        display = proj.get("display_name", name)
        phases_list = proj.get("phases", [])
        pct = compute_progress(phases_list)
        counts = get_phase_counts(phases_list)

        blocked = counts.get("blocked", 0)

        bar_filled = int(pct / 5)  # 20 chars wide
        bar_empty = 20 - bar_filled

        if blocked:
            color = "red"
        elif pct >= 100:
            color = "green"
        else:
            color = "yellow"

        bar_str = f"[{color}]{'=' * bar_filled}{'.' * bar_empty}[/{color}]"

        # Find current phase
        current = ""
        for phase in phases_list:
            if phase.get("status") == "blocked":
                blocker = phase.get("blocker", "")
                current = f"[red]BLOCKED: {blocker[:30]}[/red]"
                break
            elif phase.get("status") == "in_progress":
                current = phase.get("name", "")
                break
            elif phase.get("status") == "not_started":
                current = f"[dim]{phase.get('name', '')}[/dim]"
                break

        if not current and pct >= 100:
            current = "[green]All complete[/green]"

        table.add_row(display, bar_str, f"{pct}%", current)

    console.print()
    console.print(table)
    console.print()


@cli.command()
def edit():
    """Open projects.yaml in $EDITOR."""
    config_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    yaml_path = os.path.join(config_dir, "projects.yaml")

    editor = os.environ.get("EDITOR", "vim")

    if not os.path.exists(yaml_path):
        click.echo(f"projects.yaml not found at {yaml_path}")
        sys.exit(1)

    click.echo(f"Opening {yaml_path} in {editor}...")
    subprocess.call([editor, yaml_path])


def main():
    """Entry point for python -m devpulse."""
    cli()


if __name__ == "__main__":
    main()
