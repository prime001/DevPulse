"""DevPulse Full Rich TUI Dashboard."""

import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from rich.console import Console
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


def _build_metrics_section():
    """Build the METRICS section with subscriber counts and other stats."""
    lines = []

    # Book subscribers
    book_db = Path("/opt/erik_anderson_book_web/backend/subscribers.db")
    if book_db.exists():
        try:
            conn = sqlite3.connect(str(book_db))
            c = conn.cursor()
            total = c.execute("SELECT COUNT(*) FROM subscribers").fetchone()[0]
            today = datetime.now().strftime("%Y-%m-%d")
            today_count = c.execute(
                "SELECT COUNT(*) FROM subscribers WHERE subscribed_at LIKE ?",
                (f"{today}%",),
            ).fetchone()[0]
            week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            week_count = c.execute(
                "SELECT COUNT(*) FROM subscribers WHERE subscribed_at >= ?",
                (week_ago,),
            ).fetchone()[0]
            latest = c.execute(
                "SELECT first_name, subscribed_at FROM subscribers ORDER BY id DESC LIMIT 1"
            ).fetchone()
            conn.close()

            lines.append(
                f"  [bold yellow]Book Subscribers:[/bold yellow]  "
                f"[bold white]{total}[/bold white] total  |  "
                f"[green]+{week_count}[/green] this week  |  "
                f"[cyan]+{today_count}[/cyan] today"
            )
            if latest:
                name = latest[0] or "Anonymous"
                when = latest[1] or ""
                if "T" in when:
                    when = when.split("T")[0]
                lines.append(
                    f"  [dim]Latest: {name} ({when})[/dim]"
                )
        except Exception:
            lines.append("  [dim]Book subscribers: error reading DB[/dim]")
    else:
        lines.append("  [dim]Book subscribers: no database found[/dim]")

    # Twitter bot stats
    twitter_db = Path("/opt/twitter/primetweet.db")
    if twitter_db.exists():
        try:
            conn = sqlite3.connect(str(twitter_db))
            c = conn.cursor()
            month = datetime.now().strftime("%Y-%m")
            row = c.execute(
                "SELECT count FROM tweet_counter WHERE month = ?", (month,)
            ).fetchone()
            tweets_this_month = row[0] if row else 0
            conn.close()
            lines.append(
                f"  [bold yellow]Tweets This Month:[/bold yellow]  "
                f"[bold white]{tweets_this_month}[/bold white]"
            )
        except Exception:
            pass

    if not lines:
        return Text("  No metrics available.", style="dim")

    return Text.from_markup("\n".join(lines))


def render_dashboard(config, git_results, phase_results, blockers, tasks, focus_items):
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

    # METRICS
    metrics_content = _build_metrics_section()
    console.print(
        Panel(
            metrics_content,
            title="[bold bright_white]METRICS[/bold bright_white]",
            border_style="yellow",
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

    # BLOCKERS
    blockers_content = _build_blockers_section(blockers)
    console.print(
        Panel(
            blockers_content,
            title="[bold bright_white]BLOCKERS[/bold bright_white]",
            border_style="red",
            expand=True,
        )
    )
    console.print()
