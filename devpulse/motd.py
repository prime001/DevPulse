"""DevPulse MOTD — Compact 8-10 line summary for SSH login."""

from datetime import datetime

from rich.console import Console


def render_motd(config, blockers, tasks, ado_data, focus_items):
    """Render a compact MOTD summary to the terminal.

    Designed to be fast, minimal, and readable over SSH.
    """
    console = Console(highlight=False)

    now = datetime.now()
    day_str = now.strftime("%a %b %-d")

    project_count = len(config.get("projects", {}))
    blocked_count = len(blockers)

    # Header line
    header = f"DevPulse | {day_str} -- {project_count} projects"
    if blocked_count:
        header += f", [red]{blocked_count} blocked[/red]"
    console.print(f"[bold bright_cyan]{header}[/bold bright_cyan]")

    # Focus line: top 3 tasks
    if focus_items:
        top_tasks = [item.get("text", "") for item in focus_items[:3]]
        # Truncate each task for compact display
        short_tasks = []
        for t in top_tasks:
            short = t[:40] + "..." if len(t) > 40 else t
            short_tasks.append(short)
        focus_str = " | ".join(short_tasks)
        console.print(f"  [yellow]Focus:[/yellow] {focus_str}")
    else:
        console.print("  [dim]No focus items identified.[/dim]")

    # Blockers line
    if blockers:
        blocker_strs = []
        for b in blockers[:2]:
            proj = b.get("project", "?")
            desc = b.get("blocker", "?")
            short = desc[:35] + "..." if len(desc) > 35 else desc
            blocker_strs.append(f"[{proj}] {short}")
        console.print(f"  [red]Blockers:[/red] {' | '.join(blocker_strs)}")

    # PR alerts line
    pr_alerts = ado_data.get("pr_alerts", [])
    stale = ado_data.get("stale_prs", 0)
    if pr_alerts or stale:
        pr_parts = []
        if pr_alerts:
            pr_parts.append(f"{len(pr_alerts)} PR alert(s)")
        if stale:
            pr_parts.append(f"{stale} stale")
        console.print(f"  [yellow]PRs:[/yellow] {' | '.join(pr_parts)}")

    # Footer
    console.print(f"  [dim]Type 'devpulse' for full dashboard[/dim]")
