"""SQLite cache for SerpApi responses, plus a log of how many live searches were spent this month.

Every SerpApi call costs one of the 250 free monthly searches, so identical requests are answered
from disk until they expire.
"""

import json
import sqlite3
import time
from datetime import datetime, timezone

from .config import settings


def _db() -> sqlite3.Connection:
    con = sqlite3.connect(settings.cache_path)
    con.execute("CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, created REAL, body TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS usage (ts REAL, engine TEXT)")
    return con


def get(key: str, ttl_hours: float):
    with _db() as con:
        row = con.execute("SELECT created, body FROM cache WHERE key = ?", (key,)).fetchone()
    if row and time.time() - row[0] < ttl_hours * 3600:
        return json.loads(row[1])
    return None


def put(key: str, value) -> None:
    with _db() as con:
        con.execute("INSERT OR REPLACE INTO cache VALUES (?, ?, ?)", (key, time.time(), json.dumps(value)))


def record_search(engine: str) -> None:
    with _db() as con:
        con.execute("INSERT INTO usage VALUES (?, ?)", (time.time(), engine))


def searches_this_month() -> int:
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, tzinfo=timezone.utc).timestamp()
    with _db() as con:
        return con.execute("SELECT COUNT(*) FROM usage WHERE ts >= ?", (start,)).fetchone()[0]
