"""Tests for devpulse.phase_tracker module."""

import pytest

from devpulse.phase_tracker import (
    compute_progress,
    extract_blockers,
    extract_tasks,
    get_phase_counts,
)


class TestComputeProgress:
    def test_empty_phases(self):
        assert compute_progress([]) == 0.0

    def test_all_complete(self):
        phases = [
            {"name": "A", "status": "complete"},
            {"name": "B", "status": "complete"},
        ]
        assert compute_progress(phases) == 100.0

    def test_all_not_started(self):
        phases = [
            {"name": "A", "status": "not_started"},
            {"name": "B", "status": "not_started"},
        ]
        assert compute_progress(phases) == 0.0

    def test_all_blocked(self):
        phases = [
            {"name": "A", "status": "blocked"},
            {"name": "B", "status": "blocked"},
        ]
        assert compute_progress(phases) == 25.0

    def test_mixed_statuses(self):
        phases = [
            {"name": "A", "status": "complete"},      # 100
            {"name": "B", "status": "in_progress"},    # 50
            {"name": "C", "status": "not_started"},    # 0
        ]
        # (100 + 50 + 0) / 3 = 50.0
        assert compute_progress(phases) == 50.0

    def test_complete_and_in_progress(self):
        phases = [
            {"name": "A", "status": "complete"},      # 100
            {"name": "B", "status": "in_progress"},    # 50
        ]
        # (100 + 50) / 2 = 75.0
        assert compute_progress(phases) == 75.0

    def test_single_in_progress(self):
        phases = [{"name": "A", "status": "in_progress"}]
        assert compute_progress(phases) == 50.0

    def test_missing_status_defaults_to_not_started(self):
        phases = [{"name": "A"}]
        assert compute_progress(phases) == 0.0


class TestGetPhaseCounts:
    def test_counts(self):
        phases = [
            {"name": "A", "status": "complete"},
            {"name": "B", "status": "complete"},
            {"name": "C", "status": "in_progress"},
            {"name": "D", "status": "blocked"},
            {"name": "E", "status": "not_started"},
        ]
        counts = get_phase_counts(phases)
        assert counts == {
            "complete": 2,
            "in_progress": 1,
            "blocked": 1,
            "not_started": 1,
        }

    def test_empty(self):
        counts = get_phase_counts([])
        assert counts == {
            "complete": 0,
            "in_progress": 0,
            "blocked": 0,
            "not_started": 0,
        }


class TestExtractBlockers:
    def test_extracts_blockers(self):
        config = {
            "projects": {
                "proj_a": {
                    "phases": [
                        {"name": "Phase 1", "status": "blocked", "blocker": "Need X"},
                        {"name": "Phase 2", "status": "complete"},
                    ]
                },
                "proj_b": {
                    "display_name": "Project B",
                    "phases": [
                        {"name": "Phase 1", "status": "blocked", "blocker": "Need Y"},
                    ]
                },
            }
        }
        blockers = extract_blockers(config)
        assert len(blockers) == 2
        assert blockers[0]["project"] == "proj_a"
        assert blockers[0]["blocker"] == "Need X"
        assert blockers[1]["project"] == "Project B"
        assert blockers[1]["blocker"] == "Need Y"

    def test_no_blockers(self):
        config = {
            "projects": {
                "proj_a": {
                    "phases": [{"name": "Phase 1", "status": "complete"}]
                }
            }
        }
        assert extract_blockers(config) == []

    def test_empty_projects(self):
        assert extract_blockers({"projects": {}}) == []


class TestExtractTasks:
    def test_extracts_tasks_from_in_progress(self):
        config = {
            "projects": {
                "proj_a": {
                    "phases": [
                        {
                            "name": "Active Phase",
                            "status": "in_progress",
                            "tasks": ["Do thing 1", "Do thing 2"],
                        },
                        {
                            "name": "Done Phase",
                            "status": "complete",
                            "tasks": ["Old task"],
                        },
                    ]
                }
            }
        }
        tasks = extract_tasks(config)
        assert len(tasks) == 2
        assert tasks[0]["task"] == "Do thing 1"
        assert tasks[1]["task"] == "Do thing 2"

    def test_ignores_non_in_progress(self):
        config = {
            "projects": {
                "proj_a": {
                    "phases": [
                        {
                            "name": "Blocked",
                            "status": "blocked",
                            "tasks": ["Waiting task"],
                        },
                    ]
                }
            }
        }
        assert extract_tasks(config) == []

    def test_no_tasks_key(self):
        config = {
            "projects": {
                "proj_a": {
                    "phases": [
                        {"name": "Active", "status": "in_progress"},
                    ]
                }
            }
        }
        assert extract_tasks(config) == []
