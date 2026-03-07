"""DevPulse MOTD — Compact summary for SSH login."""

from datetime import datetime

from rich.console import Console


def render_motd(config, blockers, tasks, focus_items):
    """Render a compact MOTD summary to the terminal."""
    console = Console(highlight=False)

    now = datetime.now()
    day_str = now.strftime("%a %b %-d")

    project_count = len(config.get("projects", {}))
    blocked_count = len(blockers)

    # Count in-progress projects
    in_progress = 0
    complete = 0
    for name, proj in config.get("projects", {}).items():
        phases = proj.get("phases", [])
        has_ip = any(p.get("status") == "in_progress" for p in phases)
        all_done = all(p.get("status") == "complete" for p in phases) if phases else False
        if has_ip:
            in_progress += 1
        if all_done:
            complete += 1

    # Header line
    header = f"DevPulse | {day_str} -- {project_count} projects"
    if in_progress:
        header += f", {in_progress} active"
    if complete:
        header += f", {complete} complete"
    if blocked_count:
        header += f", [red]{blocked_count} blocked[/red]"
    console.print(f"[bold bright_cyan]{header}[/bold bright_cyan]")

    # Focus line: top 3 tasks
    if focus_items:
        top_tasks = [item.get("text", "") for item in focus_items[:3]]
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

    # Footer
    console.print(f"  [dim]Type 'devpulse' for full dashboard[/dim]")
