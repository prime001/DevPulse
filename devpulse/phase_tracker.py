"""Track project phases, progress, blockers, and tasks."""


# Weight each status for percentage calculation
STATUS_WEIGHTS = {
    "complete": 100,
    "in_progress": 50,
    "blocked": 25,
    "not_started": 0,
}


def compute_progress(phases):
    """Compute progress percentage for a list of phases.

    Args:
        phases: List of phase dicts, each with at least a 'status' key.

    Returns:
        float: Weighted progress percentage (0.0 - 100.0).
               Returns 0.0 if phases is empty.
    """
    if not phases:
        return 0.0

    total = sum(STATUS_WEIGHTS.get(p.get("status", "not_started"), 0) for p in phases)
    return round(total / len(phases), 1)


def get_phase_counts(phases):
    """Count phases by status.

    Args:
        phases: List of phase dicts.

    Returns:
        dict mapping status strings to counts.
    """
    counts = {"complete": 0, "in_progress": 0, "blocked": 0, "not_started": 0}
    for phase in phases:
        status = phase.get("status", "not_started")
        counts[status] = counts.get(status, 0) + 1
    return counts


def extract_blockers(projects_config):
    """Extract all blockers across all projects.

    Args:
        projects_config: The full config dict from load_projects().

    Returns:
        list of dicts with keys: project, phase, blocker.
    """
    blockers = []
    projects = projects_config.get("projects", {})
    for name, config in projects.items():
        display = config.get("display_name", name)
        for phase in config.get("phases", []):
            if "blocker" in phase:
                blockers.append(
                    {
                        "project": display,
                        "phase": phase["name"],
                        "blocker": phase["blocker"],
                    }
                )
    return blockers


def extract_tasks(projects_config):
    """Extract actionable tasks from in_progress phases.

    Args:
        projects_config: The full config dict from load_projects().

    Returns:
        list of dicts with keys: project, phase, task.
    """
    tasks = []
    projects = projects_config.get("projects", {})
    for name, config in projects.items():
        display = config.get("display_name", name)
        for phase in config.get("phases", []):
            if phase.get("status") == "in_progress" and "tasks" in phase:
                for task in phase["tasks"]:
                    tasks.append(
                        {
                            "project": display,
                            "phase": phase["name"],
                            "task": task,
                        }
                    )
    return tasks


def project_summary(projects_config):
    """Generate a summary for each project.

    Args:
        projects_config: The full config dict from load_projects().

    Returns:
        list of dicts with keys: project, display_name, progress,
        phase_counts, phases.
    """
    summaries = []
    projects = projects_config.get("projects", {})
    for name, config in projects.items():
        phases = config.get("phases", [])
        summaries.append(
            {
                "project": name,
                "display_name": config.get("display_name", name),
                "progress": compute_progress(phases),
                "phase_counts": get_phase_counts(phases),
                "phases": phases,
            }
        )
    return summaries
