"""Scan git repositories for status information."""

from datetime import datetime, timezone

from git import Repo, InvalidGitRepositoryError, NoSuchPathError


def scan_project(project_name, project_config):
    """Scan a single project's git repository.

    Args:
        project_name: The project key from projects.yaml.
        project_config: The project's config dict (must contain 'path').

    Returns:
        dict with keys: project, branch, clean, modified, untracked,
        unpushed, last_commit_date, last_commit_msg, error.
        On error, most fields are None and 'error' contains the message.
    """
    path = project_config.get("path")
    result = {
        "project": project_name,
        "branch": None,
        "clean": None,
        "modified": 0,
        "untracked": 0,
        "unpushed": 0,
        "last_commit_date": None,
        "last_commit_msg": None,
        "error": None,
    }

    if not path:
        result["error"] = "No path configured"
        return result

    try:
        repo = Repo(path)
    except (InvalidGitRepositoryError, NoSuchPathError) as e:
        result["error"] = str(e)
        return result

    try:
        result["branch"] = repo.active_branch.name
    except TypeError:
        # Detached HEAD
        result["branch"] = "DETACHED"

    # Working tree status
    modified = len(repo.index.diff(None))
    untracked = len(repo.untracked_files)
    try:
        staged = len(repo.index.diff("HEAD"))
    except Exception:
        # No commits yet — everything in index is new
        staged = 0
    dirty_count = modified + untracked + staged
    result["modified"] = modified + staged
    result["untracked"] = untracked
    result["clean"] = dirty_count == 0

    # Unpushed commits
    try:
        tracking = repo.active_branch.tracking_branch()
        if tracking:
            unpushed = list(
                repo.iter_commits(f"{tracking.name}..{repo.active_branch.name}")
            )
            result["unpushed"] = len(unpushed)
    except (TypeError, ValueError):
        # No tracking branch or detached HEAD
        pass

    # Last commit
    try:
        commit = repo.head.commit
        result["last_commit_date"] = datetime.fromtimestamp(
            commit.committed_date, tz=timezone.utc
        ).isoformat()
        result["last_commit_msg"] = commit.message.strip().split("\n")[0]
    except ValueError:
        # Empty repo, no commits
        pass

    return result


def scan_all(projects_config):
    """Scan all projects that have a path defined.

    Args:
        projects_config: The full config dict from load_projects().

    Returns:
        list of dicts, one per project with a path.
    """
    results = []
    projects = projects_config.get("projects", {})
    for name, config in projects.items():
        if "path" in config:
            results.append(scan_project(name, config))
    return results
