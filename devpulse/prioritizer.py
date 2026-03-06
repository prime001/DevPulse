"""DevPulse Cross-Project Prioritizer — Ranked 'what to do next' engine."""


def prioritize(phase_results, ado_data, git_results, config):
    """Generate a ranked list of prioritized action items.

    Priority order:
        1. Blockers to unblock
        2. Quick closes (Resolved tickets, approved PRs, unpushed branches)
        3. In-progress tasks from projects.yaml
        4. Not-started phases

    Args:
        phase_results: dict[project_name, progress_dict] from phase_tracker
        ado_data: dict from ado_bridge (focus_items, pr_alerts, stale_prs)
        git_results: dict[project_name, scan_result] from git_scanner
        config: full config dict with 'projects' key

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
        if scan is None:
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
        if scan is None:
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

    # PR alerts from ADO as quick closes
    for alert in ado_data.get("pr_alerts", []):
        items.append({
            "text": alert,
            "source": "ADO",
            "priority_reason": "quick close - PR",
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

    # ADO focus items
    for item in ado_data.get("focus_items", []):
        text = item if isinstance(item, str) else item.get("text", str(item))
        items.append({
            "text": text,
            "source": "ADO",
            "priority_reason": "ADO focus",
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
