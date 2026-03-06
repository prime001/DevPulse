"""Tests for devpulse.git_scanner module."""

import os

import pytest
from git import Repo

from devpulse.git_scanner import scan_project, scan_all


@pytest.fixture
def temp_repo(tmp_path):
    """Create a temporary git repo with one commit."""
    repo = Repo.init(tmp_path)
    # Configure git user for the temp repo
    repo.config_writer().set_value("user", "name", "Test User").release()
    repo.config_writer().set_value("user", "email", "test@test.com").release()

    # Create a file and commit it
    test_file = tmp_path / "README.md"
    test_file.write_text("Hello")
    repo.index.add(["README.md"])
    repo.index.commit("Initial commit")

    return tmp_path, repo


class TestScanProject:
    def test_clean_repo(self, temp_repo):
        path, repo = temp_repo
        config = {"path": str(path)}
        result = scan_project("test_project", config)

        assert result["project"] == "test_project"
        assert result["branch"] == "master" or result["branch"] == "main"
        assert result["clean"] is True
        assert result["modified"] == 0
        assert result["untracked"] == 0
        assert result["error"] is None
        assert result["last_commit_msg"] == "Initial commit"
        assert result["last_commit_date"] is not None

    def test_dirty_repo_modified(self, temp_repo):
        path, repo = temp_repo
        # Modify the tracked file
        (path / "README.md").write_text("Changed")
        config = {"path": str(path)}
        result = scan_project("test_project", config)

        assert result["clean"] is False
        assert result["modified"] >= 1

    def test_dirty_repo_untracked(self, temp_repo):
        path, repo = temp_repo
        # Add an untracked file
        (path / "new_file.txt").write_text("New")
        config = {"path": str(path)}
        result = scan_project("test_project", config)

        assert result["clean"] is False
        assert result["untracked"] == 1

    def test_no_path(self):
        result = scan_project("no_path_project", {})
        assert result["error"] == "No path configured"
        assert result["branch"] is None

    def test_invalid_path(self):
        config = {"path": "/tmp/nonexistent_repo_xyz_12345"}
        result = scan_project("bad_project", config)
        assert result["error"] is not None

    def test_multiple_commits(self, temp_repo):
        path, repo = temp_repo
        # Add a second commit
        second_file = path / "second.txt"
        second_file.write_text("Second file")
        repo.index.add(["second.txt"])
        repo.index.commit("Second commit")

        config = {"path": str(path)}
        result = scan_project("test_project", config)

        assert result["last_commit_msg"] == "Second commit"

    def test_commit_message_first_line_only(self, temp_repo):
        path, repo = temp_repo
        another = path / "another.txt"
        another.write_text("data")
        repo.index.add(["another.txt"])
        repo.index.commit("First line\n\nDetailed body here")

        config = {"path": str(path)}
        result = scan_project("test_project", config)

        assert result["last_commit_msg"] == "First line"


class TestScanAll:
    def test_scan_all_filters_no_path(self, temp_repo):
        path, _ = temp_repo
        config = {
            "projects": {
                "with_path": {"path": str(path)},
                "without_path": {"display_name": "No Repo"},
            }
        }
        results = scan_all(config)
        assert len(results) == 1
        assert results[0]["project"] == "with_path"

    def test_scan_all_empty(self):
        results = scan_all({"projects": {}})
        assert results == []
