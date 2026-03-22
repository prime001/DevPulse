#!/usr/bin/env python3
"""
Weekly Metrics Snapshot — tracks growth across all platforms over time.

Collects: signups, Twitter followers/impressions, YouTube views/subs,
GSC impressions/clicks, and stores in SQLite for trend analysis.

Usage:
  python weekly_metrics.py              # Collect snapshot + show trends
  python weekly_metrics.py --report     # Just show the report
  python weekly_metrics.py --discord    # Collect + post to Discord

Run weekly via cron (Sunday morning).
"""

import json
import logging
import os
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("WeeklyMetrics")

DB_FILE = "/opt/DevPulse/metrics.db"
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1485085184201199667/UGN7aOmxFCT53cbRIG-BaZrdT1QBZ4kJGdAzyMsN1kCuExyhM0BjtHYBNaO5ojjad_N-"


def init_db():
    conn = sqlite3.connect(DB_FILE)
    conn.execute("""CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collected_at TEXT NOT NULL,
        week_label TEXT,
        category TEXT NOT NULL,
        metric TEXT NOT NULL,
        value REAL,
        details TEXT
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_cat ON snapshots(category, metric)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_snap_date ON snapshots(collected_at)")
    conn.commit()
    conn.close()


def store(category, metric, value, details=None):
    conn = sqlite3.connect(DB_FILE)
    week = datetime.now().strftime("%Y-W%U")
    conn.execute(
        "INSERT INTO snapshots (collected_at, week_label, category, metric, value, details) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), week, category, metric, value, details),
    )
    conn.commit()
    conn.close()


def get_previous(category, metric):
    """Get the most recent previous value for comparison."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT value, collected_at FROM snapshots WHERE category=? AND metric=? ORDER BY collected_at DESC LIMIT 1 OFFSET 1",
        (category, metric),
    )
    row = c.fetchone()
    conn.close()
    return row if row else (None, None)


def get_history(category, metric, weeks=8):
    """Get last N values for trend display."""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(
        "SELECT value, week_label FROM snapshots WHERE category=? AND metric=? ORDER BY collected_at DESC LIMIT ?",
        (category, metric, weeks),
    )
    rows = c.fetchall()
    conn.close()
    return list(reversed(rows))


def delta_str(current, previous):
    """Format a delta string like +5 or -3."""
    if previous is None:
        return "(new)"
    diff = current - previous
    if diff > 0:
        return f"+{diff:.0f}"
    elif diff < 0:
        return f"{diff:.0f}"
    return "="


def spark(values):
    """Simple ASCII sparkline."""
    if not values or len(values) < 2:
        return ""
    mn, mx = min(values), max(values)
    if mn == mx:
        return "─" * len(values)
    chars = "▁▂▃▄▅▆▇█"
    return "".join(chars[int((v - mn) / (mx - mn) * (len(chars) - 1))] for v in values)


# ── Collectors ──────────────────────────────────────────────────────

def collect_signups():
    """Collect signup counts from all sites."""
    logger.info("Collecting signups...")

    # erikandersonbook.com
    try:
        db = sqlite3.connect("/opt/erik_anderson_book_web/backend/subscribers.db")
        db.row_factory = sqlite3.Row

        users = db.execute("SELECT COUNT(*) as cnt FROM users").fetchone()["cnt"]
        subs = db.execute("SELECT COUNT(*) as cnt FROM subscribers").fetchone()["cnt"]
        # Filter test accounts
        real_users = db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE email NOT IN ('primex001@gmail.com','test@example.com','erik@test.com','test-tools@example.com','verify-test@example.com','applereview@erikandersonbook.com')"
        ).fetchone()["cnt"]
        real_subs = db.execute(
            "SELECT COUNT(*) as cnt FROM subscribers WHERE email NOT IN ('primex001@gmail.com','test@example.com','erik@test.com','test-tools@example.com','verify-test@example.com','applereview@erikandersonbook.com')"
        ).fetchone()["cnt"]
        db.close()

        store("erikandersonbook", "users", real_users)
        store("erikandersonbook", "subscribers", real_subs)
        logger.info(f"  erikandersonbook: {real_users} users, {real_subs} subscribers")
    except Exception as e:
        logger.error(f"  erikandersonbook failed: {e}")

    # inkengine.ai
    try:
        db = sqlite3.connect("/opt/BookForge/webapp/inkengine.db")
        users = db.execute(
            "SELECT COUNT(*) as cnt FROM users WHERE email NOT IN ('primex001@gmail.com','test@example.com')"
        ).fetchone()[0]
        db.close()
        store("inkengine", "users", users)
        logger.info(f"  inkengine: {users} users")
    except Exception as e:
        logger.error(f"  inkengine failed: {e}")

    # humanrail.dev (Postgres in Docker)
    try:
        result = subprocess.run(
            ["docker", "exec", "work_route_engine-postgres-1", "psql", "-U", "dev", "-d", "escalation",
             "-t", "-A", "-c",
             "SELECT COUNT(*) FROM organizations WHERE contact_email NOT IN ('ci-test@humanrail.dev','public-test@humanrail.dev','rls@test.com')"],
            capture_output=True, text=True, timeout=10,
        )
        orgs = int(result.stdout.strip()) if result.stdout.strip() else 0
        store("humanrail", "organizations", orgs)
        logger.info(f"  humanrail: {orgs} organizations")
    except Exception as e:
        logger.error(f"  humanrail failed: {e}")


def collect_twitter():
    """Collect Twitter metrics."""
    logger.info("Collecting Twitter metrics...")
    try:
        sys.path.insert(0, "/opt/twitter")
        from dotenv import load_dotenv
        load_dotenv("/opt/twitter/.env")
        import tweepy

        client = tweepy.Client(
            bearer_token=os.getenv("BEARER_TOKEN"),
            consumer_key=os.getenv("API_KEY"),
            consumer_secret=os.getenv("API_SECRET"),
            access_token=os.getenv("ACCESS_TOKEN"),
            access_token_secret=os.getenv("ACCESS_TOKEN_SECRET"),
        )

        me = client.get_me(user_fields=["public_metrics"])
        m = me.data.public_metrics
        store("twitter", "followers", m["followers_count"])
        store("twitter", "following", m["following_count"])
        store("twitter", "tweets", m["tweet_count"])

        # Get last 20 tweets for engagement
        tweets = client.get_users_tweets(
            me.data.id, max_results=20,
            tweet_fields=["public_metrics"],
        )
        total_imp = sum(t.public_metrics.get("impression_count", 0) for t in tweets.data)
        total_likes = sum(t.public_metrics.get("like_count", 0) for t in tweets.data)
        total_replies = sum(t.public_metrics.get("reply_count", 0) for t in tweets.data)
        avg_imp = total_imp // 20

        store("twitter", "avg_impressions", avg_imp)
        store("twitter", "total_likes_20", total_likes)
        store("twitter", "total_replies_20", total_replies)

        logger.info(f"  Twitter: {m['followers_count']} followers, avg {avg_imp} impressions")
    except Exception as e:
        logger.error(f"  Twitter failed: {e}")


def collect_gsc():
    """Collect Google Search Console metrics via subprocess (separate venv)."""
    logger.info("Collecting GSC metrics...")
    try:
        result = subprocess.run(
            ["/opt/mcp_servers/google-search-console/venv/bin/python", "-c",
             'import asyncio,json,sys,os;'
             'os.environ["GOOGLE_SERVICE_ACCOUNT_KEY"]="/opt/mcp_servers/google-search-console/service-account.json";'
             'sys.path.insert(0,"/opt/mcp_servers/google-search-console");'
             'from server import gsc_all_sites_summary;'
             'print(asyncio.run(gsc_all_sites_summary(days=7)))'],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)

        total_clicks = 0
        total_impressions = 0
        for site in data.get("sites", []):
            if "error" in site:
                continue
            clicks = site.get("clicks", 0)
            impr = site.get("impressions", 0)
            total_clicks += clicks
            total_impressions += impr
            if impr > 0:
                domain = site["site"].replace("sc-domain:", "").replace("https://", "").rstrip("/")
                store("gsc", f"impressions_{domain}", impr)

        store("gsc", "total_impressions", total_impressions)
        store("gsc", "total_clicks", total_clicks)
        logger.info(f"  GSC: {total_impressions} impressions, {total_clicks} clicks")
    except Exception as e:
        logger.error(f"  GSC failed: {e}")


def collect_youtube():
    """Collect YouTube metrics via the YouTube Data API."""
    logger.info("Collecting YouTube metrics...")
    try:
        sys.path.insert(0, "/opt/YouTubeShorts")
        from modules.uploader import get_youtube_credentials
        from googleapiclient.discovery import build as yt_build

        creds = get_youtube_credentials()
        if not creds:
            logger.warning("  YouTube: no valid credentials")
            store("youtube", "note", 0, "credentials unavailable")
            return

        youtube = yt_build("youtube", "v3", credentials=creds)

        # Channel stats
        channels = youtube.channels().list(part="statistics", mine=True).execute()
        if not channels.get("items"):
            logger.warning("  YouTube: no channel found")
            return

        stats = channels["items"][0]["statistics"]
        subs = int(stats.get("subscriberCount", 0))
        views = int(stats.get("viewCount", 0))
        videos = int(stats.get("videoCount", 0))

        store("youtube", "subscribers", subs)
        store("youtube", "total_views", views)
        store("youtube", "videos", videos)

        # Get last 10 Shorts performance
        search = youtube.search().list(
            part="snippet", channelId=channels["items"][0]["id"],
            order="date", maxResults=10, type="video",
        ).execute()
        video_ids = [item["id"]["videoId"] for item in search.get("items", [])]

        if video_ids:
            vids = youtube.videos().list(
                part="statistics", id=",".join(video_ids),
            ).execute()
            recent_views = sum(int(v["statistics"].get("viewCount", 0)) for v in vids.get("items", []))
            recent_likes = sum(int(v["statistics"].get("likeCount", 0)) for v in vids.get("items", []))
            store("youtube", "recent_10_views", recent_views)
            store("youtube", "recent_10_likes", recent_likes)

        logger.info(f"  YouTube: {subs} subs, {views} total views, {videos} videos")
    except Exception as e:
        logger.error(f"  YouTube failed: {e}")
        store("youtube", "note", 0, str(e)[:200])


# ── Report ──────────────────────────────────────────────────────────

def generate_report():
    """Generate a formatted metrics report with trends."""
    init_db()

    metrics = [
        ("Twitter", "twitter", "followers"),
        ("Twitter Avg Impressions", "twitter", "avg_impressions"),
        ("Twitter Likes (last 20)", "twitter", "total_likes_20"),
        ("erikandersonbook Users", "erikandersonbook", "users"),
        ("erikandersonbook Subs", "erikandersonbook", "subscribers"),
        ("InkEngine Users", "inkengine", "users"),
        ("HumanRail Orgs", "humanrail", "organizations"),
        ("GSC Total Impressions", "gsc", "total_impressions"),
        ("GSC Total Clicks", "gsc", "total_clicks"),
        ("YouTube Subscribers", "youtube", "subscribers"),
        ("YouTube Total Views", "youtube", "total_views"),
        ("YouTube Videos", "youtube", "videos"),
        ("YouTube Recent 10 Views", "youtube", "recent_10_views"),
        ("YouTube Recent 10 Likes", "youtube", "recent_10_likes"),
    ]

    lines = []
    lines.append(f"**Weekly Metrics Report — {datetime.now().strftime('%Y-%m-%d')}**")
    lines.append("")
    lines.append(f"{'Metric':<30} {'Current':>8} {'Delta':>8} {'Trend':>10}")
    lines.append(f"{'─'*30} {'─'*8} {'─'*8} {'─'*10}")

    for label, cat, metric in metrics:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        c.execute(
            "SELECT value FROM snapshots WHERE category=? AND metric=? ORDER BY collected_at DESC LIMIT 1",
            (cat, metric),
        )
        current_row = c.fetchone()
        conn.close()

        if not current_row:
            continue

        current = current_row[0]
        prev_val, _ = get_previous(cat, metric)
        history = get_history(cat, metric, 8)
        trend = spark([v for v, _ in history]) if history else ""
        delta = delta_str(current, prev_val)

        lines.append(f"{label:<30} {current:>8.0f} {delta:>8} {trend:>10}")

    report = "\n".join(lines)
    print(report)
    return report


def post_to_discord(report):
    """Post the report to Discord."""
    import requests
    try:
        requests.post(
            DISCORD_WEBHOOK,
            json={"content": f"```\n{report}\n```", "username": "Metrics Bot"},
            timeout=10,
        )
        logger.info("Report posted to Discord")
    except Exception as e:
        logger.error(f"Discord post failed: {e}")


# ── Main ────────────────────────────────────────────────────────────

def main():
    init_db()

    report_only = "--report" in sys.argv
    post_discord = "--discord" in sys.argv

    if not report_only:
        collect_signups()
        collect_twitter()
        collect_gsc()
        collect_youtube()
        logger.info("Snapshot complete")

    report = generate_report()

    if post_discord:
        post_to_discord(report)


if __name__ == "__main__":
    main()
