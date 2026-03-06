# DevPulse — Engineering Command Center

## Problem

Work is scattered across multiple projects, ADO boards, git branches, and mental context. There's no single view that answers: "What should I work on right now, and where do things stand?"

## Solution

A terminal dashboard that runs on SSH login (or on-demand) and shows:
- Project status across all repos (branch, clean/dirty, test health)
- ADO ticket priorities and PR alerts
- Cross-project phase tracking with blockers
- A single prioritized "what to do next" list

---

## Architecture

```
DevPulse/
├── GAMEPLAN.md
├── README.md
├── .gitignore
├── requirements.txt
├── projects.yaml              # Cross-project phase definitions (gitignored)
├── projects.yaml.example      # Template for projects.yaml
├── devpulse/
│   ├── __init__.py
│   ├── cli.py                 # Click CLI: dashboard, brief, status
│   ├── config.py              # Load projects.yaml + env vars
│   ├── git_scanner.py         # Scan git repos: branch, status, recent commits, test results
│   ├── ado_bridge.py          # Pull cached ADO data (from ADO_Ticket_Analyzer output or live)
│   ├── phase_tracker.py       # Parse projects.yaml phases, compute progress
│   ├── dashboard.py           # Rich TUI: full interactive dashboard
│   ├── motd.py                # Brief one-screen summary for SSH login
│   └── prioritizer.py         # Cross-project "what to do next" engine
├── output/
│   └── cache/                 # Cached ADO data, test results
├── scripts/
│   ├── devpulse-motd.sh       # /etc/profile.d script for SSH login
│   └── devpulse-refresh.sh    # Cron script to refresh cache
└── tests/
    ├── test_git_scanner.py
    ├── test_phase_tracker.py
    └── test_prioritizer.py
```

---

## Core Components

### 1. projects.yaml — Single Source of Truth

```yaml
projects:
  my_project:
    path: ~/Projects/my-project
    display_name: My Project
    ado_epic: 12345
    test_cmd: "python -m pytest tests/ -q"
    phases:
      - name: "Core Features"
        status: complete
      - name: "API Integration"
        status: in_progress
        tasks:
          - "Implement REST endpoints"
          - "Add authentication"
      - name: "Documentation"
        status: not_started

  another_project:
    path: ~/Projects/another-project
    display_name: Another Project
    branch: feature-branch
    ado_ticket: 67890
    phases:
      - name: "Build & Test"
        status: complete
      - name: "Deploy"
        status: blocked
        blocker: "Waiting for staging environment access"
```

### 2. Git Scanner (`git_scanner.py`)

For each project with a `path`:
- Current branch name
- Clean/dirty status (uncommitted changes)
- Unpushed commits
- Last commit date + message
- Test pass/fail (run `test_cmd` if defined, cache result)

### 3. ADO Bridge (`ado_bridge.py`)

Two modes:
- **Cached**: Read from ADO_Ticket_Analyzer's output files (fast, no API calls)
- **Live**: Import from ado_analyzer directly and query live

Pulls:
- Focus items (top 5 daily)
- PR alerts (unapproved, stale)
- Epic progress (child state counts)

### 4. Phase Tracker (`phase_tracker.py`)

Reads `projects.yaml` and computes:
- Per-project progress bar (complete/in_progress/blocked/not_started phases)
- Overall completion percentage
- Active blockers list
- Next actionable tasks

### 5. Dashboard (`dashboard.py`) — Rich TUI

Full-screen terminal dashboard using the `rich` library:

```
╔══════════════════════════════════════════════════════════════════════╗
║  DevPulse — Friday, March 6, 2026                                  ║
╠══════════════════════════════════════════════════════════════════════╣
║                                                                     ║
║  PROJECTS                                                           ║
║  Project Alpha    feature-auth         clean   42 tests ok          ║
║  Project Beta     main                 3 new   needs push           ║
║  Project Gamma    refactor-v2          clean   18 tests ok          ║
║                                                                     ║
║  PHASES                                                             ║
║  Project Alpha  [===================>..] 85%  API Integration       ║
║  Project Beta   [==========>..........] 50%  BLOCKED: staging env   ║
║  Project Gamma  [===============>....] 66%   Phase 3 not started    ║
║                                                                     ║
║  FOCUS TODAY                                                        ║
║  1. Unblock staging environment (Project Beta blocker)              ║
║  2. Finish REST endpoints (Project Alpha)                           ║
║  3. Push feature branch                                             ║
║  4. Review open PR #42                                              ║
║                                                                     ║
║  PR ALERTS                                                          ║
║  ! #42 Auth refactor — YOUR PR, 5d, awaiting review                ║
║  * 2 PRs approved and ready to merge                                ║
║                                                                     ║
║  BLOCKERS                                                           ║
║  [Beta]   Waiting for staging environment access                    ║
║  [Gamma]  Need hardware for integration test                        ║
║                                                                     ║
╚══════════════════════════════════════════════════════════════════════╝
```

### 6. MOTD (`motd.py`) — SSH Login Summary

Compact 10-line version that runs instantly on login:

```
DevPulse | Fri Mar 6 — 3 projects, 1 blocked, 4 PRs
  Focus: Unblock staging | Finish REST endpoints | Push feature branch
  PRs: 2 ready to merge | 1 yours (5d) | 1 unreviewed
  Type 'devpulse' for full dashboard
```

### 7. Cross-Project Prioritizer (`prioritizer.py`)

Merges signals from all sources into one ranked list:
1. Blockers (unblock others)
2. Quick closes (Resolved ADO tickets, approved PRs to merge)
3. In-progress phase tasks (from projects.yaml)
4. ADO daily focus items
5. Not-started phases

---

## CLI Interface

```bash
# Full dashboard
devpulse

# Brief summary (MOTD-style, 10 lines)
devpulse brief

# Just project git status
devpulse status

# Just phases
devpulse phases

# Refresh cached ADO data
devpulse refresh

# Edit projects.yaml
devpulse edit
```

---

## Implementation Phases

### Phase 1: Foundation
- [x] GAMEPLAN.md
- [x] Project structure, .gitignore, requirements.txt
- [x] projects.yaml with current project data
- [x] config.py — load projects.yaml
- [x] git_scanner.py — branch, status, unpushed
- [x] phase_tracker.py — parse phases, compute progress
- [x] cli.py — `devpulse status` and `devpulse phases`
- [x] Tests

### Phase 2: Dashboard
- [x] dashboard.py — Rich TUI with full layout
- [x] ado_bridge.py — read ADO Analyzer cached data
- [x] prioritizer.py — cross-project focus list
- [x] cli.py — `devpulse` (full dashboard)

### Phase 3: SSH Integration
- [x] motd.py — compact login summary
- [x] devpulse-motd.sh — profile.d script
- [x] devpulse-refresh.sh — cron cache refresh
- [x] `devpulse brief` command
- [ ] Install instructions

### Phase 4: Polish
- [ ] Auto-detect new git repos in ~/Scripts/
- [ ] Test runner integration (run and cache test results)
- [ ] ADO live mode (query API directly)
- [ ] tmux layout launcher
- [ ] Color themes

---

## Dependencies

```
click              # CLI framework
rich               # Terminal UI (tables, progress bars, panels, colors)
pyyaml             # projects.yaml
gitpython          # Git repo inspection
```

Lightweight. No web server, no database, no background daemon.

---

## Data Flow

```
projects.yaml ──┐
                 ├──> phase_tracker ──┐
git repos ──────┤                    ├──> prioritizer ──> dashboard/motd
                 ├──> git_scanner ───┘         │
ADO cache ──────┴──> ado_bridge ──────────────┘
```
