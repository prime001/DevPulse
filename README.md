# DevPulse

A terminal dashboard that shows cross-project status at a glance — git branches, phase progress, ADO tickets, PR alerts, and blockers. Runs on SSH login or on-demand.

## What It Does

- **Git Status** — Scans all your repos: current branch, dirty/clean, unpushed commits, last commit
- **Phase Tracking** — Progress bars per project with blocker detection
- **Focus List** — Cross-project prioritized "what to do next" (blockers → quick wins → in-progress tasks)
- **PR Alerts** — Reads cached data from [ADO Ticket Analyzer](https://github.com/prime001/ADO_Ticket_Analyzer) output
- **SSH MOTD** — Compact 5-line summary on every login

## Quick Start

```bash
git clone https://github.com/prime001/DevPulse.git
cd DevPulse
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
./venv/bin/pip install -e .

# Create your project config
cp projects.yaml.example projects.yaml
# Edit projects.yaml with your projects, paths, and phases

# Run it
./venv/bin/python -m devpulse
```

## Usage

```bash
# Full dashboard (Rich TUI)
devpulse

# Brief summary (MOTD-style, 5 lines)
devpulse brief

# Git status for all projects
devpulse status

# Phase progress
devpulse phases

# Refresh cached ADO data
devpulse refresh

# Open projects.yaml in your editor
devpulse edit
```

## SSH Login Integration

Add to your `~/.zshrc` (or `~/.bashrc`):

```bash
alias devpulse='$HOME/Scripts/DevPulse/venv/bin/python -m devpulse'
if [[ -o interactive ]]; then
  $HOME/Scripts/DevPulse/venv/bin/python -m devpulse brief
fi
```

If using Powerlevel10k, add this **before** the instant prompt block:
```bash
typeset -g POWERLEVEL9K_INSTANT_PROMPT=quiet
```

## Configuration

### projects.yaml

See `projects.yaml.example` for the full format. Each project can define:

| Field | Description |
|-------|-------------|
| `path` | Local git repo path (supports `~`) |
| `display_name` | Human-readable name |
| `ado_epic` | Azure DevOps Epic ID (optional) |
| `test_cmd` | Test command (optional) |
| `phases` | List of phases with `status`: complete, in_progress, blocked, not_started |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `ADO_OUTPUT_DIR` | Path to ADO Ticket Analyzer output directory | `~/Scripts/ADO_Ticket_Analyzer/output` |

## Dependencies

```
click        # CLI framework
rich         # Terminal UI
pyyaml       # Config
gitpython    # Git repo inspection
```

## Running Tests

```bash
./venv/bin/python -m pytest tests/ -v
```

## License

MIT
