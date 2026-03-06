"""DevPulse ADO Bridge — Read cached data from ADO Ticket Analyzer."""

import json
import os
from pathlib import Path


# Default path to ADO Ticket Analyzer output (override with ADO_OUTPUT_DIR env var)
ADO_OUTPUT_DIR = Path(
    os.environ.get("ADO_OUTPUT_DIR", str(Path.home() / "Scripts" / "ADO_Ticket_Analyzer" / "output"))
)
PR_REVIEWS_DIR = ADO_OUTPUT_DIR / "pr_reviews"


def _find_latest_review_summary():
    """Find the most recent review_summary JSON file.

    Returns the path to the latest file, or None if not found.
    """
    if not PR_REVIEWS_DIR.is_dir():
        return None

    summaries = sorted(
        PR_REVIEWS_DIR.glob("review_summary_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return summaries[0] if summaries else None


def _parse_review_summary(filepath):
    """Parse a review summary JSON into PR alert strings.

    Args:
        filepath: Path to the review_summary JSON file.

    Returns:
        Tuple of (pr_alerts list, stale_prs count).
    """
    pr_alerts = []
    stale_prs = 0

    try:
        with open(filepath, "r") as f:
            reviews = json.load(f)
    except (json.JSONDecodeError, OSError):
        return pr_alerts, stale_prs

    if not isinstance(reviews, list):
        return pr_alerts, stale_prs

    for pr in reviews:
        pr_id = pr.get("pr_id", "?")
        repo = pr.get("repo", "unknown")
        title = pr.get("title", "")
        author = pr.get("author", "")
        files_changed = pr.get("files_changed", 0)

        # Build a compact summary string
        short_title = title[:50] + "..." if len(title) > 50 else title
        alert = f"#{pr_id} {repo}: {short_title} ({author}, {files_changed} files)"
        pr_alerts.append(alert)

        # Check verdicts for stale / request-changes indicators
        reviews_dict = pr.get("reviews", {})
        for reviewer, review_text in reviews_dict.items():
            if isinstance(review_text, str) and "REQUEST CHANGES" in review_text.upper():
                # Already flagged via alert, just count as needing attention
                break

    # Count stale PRs (heuristic: any PR in the review list is worth tracking)
    stale_prs = len([p for p in reviews if _is_stale_pr(p)])

    return pr_alerts, stale_prs


def _is_stale_pr(pr_data):
    """Check if a PR looks stale based on available data.

    Uses the reviewed_at timestamp; if older than 7 days, consider stale.
    """
    from datetime import datetime, timedelta

    reviewed_at = pr_data.get("reviewed_at", "")
    if not reviewed_at:
        return False

    try:
        review_date = datetime.fromisoformat(reviewed_at)
        return (datetime.now() - review_date) > timedelta(days=7)
    except (ValueError, TypeError):
        return False


def load_ado_data():
    """Load cached ADO data from ADO Ticket Analyzer output.

    Returns:
        dict with keys:
            - focus_items: list (empty for now, future ADO daily items)
            - pr_alerts: list of PR summary strings
            - stale_prs: int count of stale PRs
    """
    result = {
        "focus_items": [],
        "pr_alerts": [],
        "stale_prs": 0,
    }

    # Gracefully handle missing ADO Analyzer
    if not ADO_OUTPUT_DIR.is_dir():
        return result

    # Find and parse the latest review summary
    latest = _find_latest_review_summary()
    if latest:
        pr_alerts, stale_prs = _parse_review_summary(latest)
        result["pr_alerts"] = pr_alerts
        result["stale_prs"] = stale_prs

    return result
