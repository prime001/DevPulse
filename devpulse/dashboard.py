"""DevPulse Full Rich TUI Dashboard."""

from datetime import datetime

from rich.console import Console
from rich.columns import Columns
from rich.panel import Panel
from rich.table import Table
from rich.text import Text


def _build_projects_table(config, git_results):
    """Build the PROJECTS section table."""
    table = Table(
        show_header=True,
        header_style="bold white",
        border_style="bright_blue",
        expand=True,
        pad_edge=True,
    )
    table.add_column("Project", style="bold cyan", ratio=2)
    table.add_column("Branch", style="green", ratio=2)
    table.add_column("Status", ratio=2)
    table.add_column("Info", style="dim", ratio=2)

    for name, proj in config.get("projects", {}).items():
        display = proj.get("display_name", name)
        scan = git_results.get(name)

        if scan is None:
            table.add_row(display, "-", "[dim]no repo path[/dim]", "")
            continue

        if scan.get("error"):
            table.add_row(display, "-", f"[red]{scan['error']}[/red]", "")
            continue

        branch = scan.get("branch") or "?"

        # Status column
        if scan.get("clean", True):
            status_str = "[green]clean[/green]"
        else:
            parts = []
            mod = scan.get("modified", 0)
            unt = scan.get("untracked", 0)
            if mod:
                parts.append(f"{mod} modified")
            if unt:
                parts.append(f"{unt} new")
            status_str = f"[yellow]{', '.join(parts) or 'dirty'}[/yellow]"

        # Info column: unpushed + last commit
        info_parts = []
        unpushed = scan.get("unpushed", 0)
        if unpushed:
            info_parts.append(f"[red]{unpushed} unpushed[/red]")

        last_msg = scan.get("last_commit_msg") or ""
        if last_msg:
            short = last_msg[:35] + "..." if len(last_msg) > 35 else last_msg
            info_parts.append(short)

        table.add_row(display, branch, status_str, " | ".join(info_parts))

    return table


def _build_phases_table(config, phase_results):
    """Build the PHASES section with progress bars."""
    table = Table(
        show_header=True,
        header_style="bold white",
        border_style="bright_blue",
        expand=True,
    )
    table.add_column("Project", style="bold cyan", min_width=18)
    table.add_column("Progress", min_width=24)
    table.add_column("%", justify="right", min_width=4)
    table.add_column("Current Phase", min_width=30)

    for name, proj in config.get("projects", {}).items():
        display = proj.get("display_name", name)
        phases_list = proj.get("phases", [])
        progress = phase_results.get(name, {})

        pct = progress.get("percentage", 0)
        blocked = progress.get("blocked", 0)

        bar_width = 20
        bar_filled = int(pct / (100 / bar_width)) if bar_width else 0
        bar_filled = min(bar_filled, bar_width)
        bar_empty = bar_width - bar_filled

        if blocked:
            color = "red"
        elif pct == 100:
            color = "green"
        else:
            color = "yellow"

        bar_str = f"[{color}]{'=' * bar_filled}{'.' * bar_empty}[/{color}]"

        # Determine current phase label
        current = ""
        for phase in phases_list:
            st = phase.get("status", "not_started")
            if st == "blocked":
                blocker = phase.get("blocker", "unknown")
                current = f"[bold red]BLOCKED:[/bold red] [red]{blocker[:35]}[/red]"
                break
            elif st == "in_progress":
                current = f"[yellow]{phase.get('name', '')}[/yellow]"
                break
            elif st == "not_started":
                current = f"[dim]{phase.get('name', '')} (not started)[/dim]"
                break

        if not current and pct == 100:
            current = "[green]All phases complete[/green]"

        table.add_row(display, bar_str, f"{pct}%", current)

    return table


def _build_focus_section(focus_items):
    """Build the FOCUS TODAY section."""
    if not focus_items:
        return Text("  No focus items identified.", style="dim")

    lines = []
    for i, item in enumerate(focus_items[:8], 1):
        text = item.get("text", "")
        source = item.get("source", "")
        reason = item.get("priority_reason", "")

        if reason and "blocker" in reason.lower():
            style = "bold red"
        elif reason and "quick" in reason.lower():
            style = "bold green"
        else:
            style = "white"

        source_tag = f" [dim]({source})[/dim]" if source else ""
        lines.append(f"  [{style}]{i}. {text}[/{style}]{source_tag}")

    return Text.from_markup("\n".join(lines))


def _build_blockers_section(blockers):
    """Build the BLOCKERS section."""
    if not blockers:
        return Text("  No active blockers.", style="green")

    lines = []
    for b in blockers:
        project = b.get("project", "?")
        blocker = b.get("blocker", "?")
        lines.append(f"  [bold red][{project}][/bold red] [red]{blocker}[/red]")

    return Text.from_markup("\n".join(lines))


def _build_pr_section(ado_data):
    """Build the PR ALERTS section."""
    pr_alerts = ado_data.get("pr_alerts", [])
    stale = ado_data.get("stale_prs", 0)

    if not pr_alerts and not stale:
        return Text("  (connect ADO Analyzer for PR data)", style="dim italic")

    lines = []
    for alert in pr_alerts[:5]:
        lines.append(f"  [yellow]{alert}[/yellow]")

    if stale:
        lines.append(f"  [dim]{stale} stale PR(s) detected[/dim]")

    return Text.from_markup("\n".join(lines)) if lines else Text(
        "  (connect ADO Analyzer for PR data)", style="dim italic"
    )


def render_dashboard(config, git_results, phase_results, blockers, tasks, ado_data, focus_items):
    """Render the full DevPulse dashboard to the terminal."""
    console = Console()

    # Header
    now = datetime.now()
    date_str = now.strftime("%A, %B %-d, %Y")
    project_count = len(config.get("projects", {}))
    blocked_count = sum(1 for p in phase_results.values() if p.get("blocked", 0) > 0)

    header_text = f"DevPulse -- {date_str}  |  {project_count} projects"
    if blocked_count:
        header_text += f", [red]{blocked_count} blocked[/red]"

    console.print()
    console.print(
        Panel(
            Text.from_markup(f"[bold bright_white]{header_text}[/bold bright_white]"),
            border_style="bright_blue",
            expand=True,
        )
    )

    # PROJECTS
    projects_table = _build_projects_table(config, git_results)
    console.print(
        Panel(
            projects_table,
            title="[bold bright_white]PROJECTS[/bold bright_white]",
            border_style="bright_blue",
            expand=True,
        )
    )

    # PHASES
    phases_table = _build_phases_table(config, phase_results)
    console.print(
        Panel(
            phases_table,
            title="[bold bright_white]PHASES[/bold bright_white]",
            border_style="bright_blue",
            expand=True,
        )
    )

    # FOCUS TODAY
    focus_content = _build_focus_section(focus_items)
    console.print(
        Panel(
            focus_content,
            title="[bold bright_white]FOCUS TODAY[/bold bright_white]",
            border_style="bright_cyan",
            expand=True,
        )
    )

    # Two-column layout: BLOCKERS + PR ALERTS
    blockers_content = _build_blockers_section(blockers)
    pr_content = _build_pr_section(ado_data)

    blockers_panel = Panel(
        blockers_content,
        title="[bold bright_white]BLOCKERS[/bold bright_white]",
        border_style="red",
        expand=True,
    )
    pr_panel = Panel(
        pr_content,
        title="[bold bright_white]PR ALERTS[/bold bright_white]",
        border_style="yellow",
        expand=True,
    )

    console.print(Columns([blockers_panel, pr_panel], expand=True, equal=True))
    console.print()
