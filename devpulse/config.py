"""Load and parse projects.yaml configuration."""

import os
from pathlib import Path

import yaml


PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILE = PROJECT_ROOT / "projects.yaml"


def load_projects(config_path=None):
    """Load projects from YAML config, expanding ~ in paths.

    Args:
        config_path: Optional path to config file. Defaults to projects.yaml
                     in the project root.

    Returns:
        dict: The full config dict with a 'projects' key mapping project
              names to their settings.
    """
    path = Path(config_path) if config_path else CONFIG_FILE

    with open(path, "r") as f:
        config = yaml.safe_load(f)

    projects = config.get("projects", {})
    for name, project in projects.items():
        if "path" in project:
            project["path"] = os.path.expanduser(project["path"])

    return config
