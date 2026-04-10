"""DevPulse Cross-Project Prioritizer — Ranked 'what to do next' engine."""


def prioritize(phase_results, git_results, config):
    """Generate a ranked list of prioritized action items.

    Priority order:
        1. Blockers to unblock
        2. Quick closes (unpushed branches, dirty repos)
        3. In-progress tasks from projects.yaml
        4. Not-started phases

    Returns:
        List of dicts with keys: text, source, priority_reason
    """
    items = []

    projects = config.get("projects", {})

    # --- Priority 1: Blockers ---
    for name, proj in projects.items():
        display = proj.get("display_name", name)
        for phase in proj.get("phases", []):
            if phase.get("status") == "blocked":
                blocker = phase.get("blocker", "Unknown blocker")
                items.append({
                    "text": f"Unblock: {blocker}",
                    "source": display,
                    "priority_reason": "blocker",
                })

    # --- Priority 2: Quick closes ---
    # Unpushed branches
    for name, scan in git_results.items():
        if scan is None or scan.get("error"):
            continue
        display = projects.get(name, {}).get("display_name", name)
        unpushed = scan.get("unpushed", 0)
        if unpushed:
            branch = scan.get("branch", "?")
            items.append({
                "text": f"Push {unpushed} unpushed commit(s) on {branch}",
                "source": display,
                "priority_reason": "quick close",
            })

    # Dirty repos — quick commit opportunity
    for name, scan in git_results.items():
        if scan is None or scan.get("error"):
            continue
        display = projects.get(name, {}).get("display_name", name)
        if not scan.get("clean", True):
            mod = scan.get("modified", 0)
            unt = scan.get("untracked", 0)
            parts = []
            if mod:
                parts.append(f"{mod} modified")
            if unt:
                parts.append(f"{unt} untracked")
            items.append({
                "text": f"Commit/stash changes ({', '.join(parts)})",
                "source": display,
                "priority_reason": "quick close",
            })

    # --- Priority 3: In-progress tasks ---
    for name, proj in projects.items():
        display = proj.get("display_name", name)
        for phase in proj.get("phases", []):
            if phase.get("status") == "in_progress":
                for task in phase.get("tasks", []):
                    items.append({
                        "text": task,
                        "source": display,
                        "priority_reason": "in-progress task",
                    })

    # --- Priority 4: Not-started phases ---
    for name, proj in projects.items():
        display = proj.get("display_name", name)
        for phase in proj.get("phases", []):
            if phase.get("status") == "not_started":
                items.append({
                    "text": f"Start: {phase.get('name', 'unnamed phase')}",
                    "source": display,
                    "priority_reason": "not started",
                })

    return items
