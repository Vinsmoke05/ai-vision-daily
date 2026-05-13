import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from .models import NewsItem


class NewsCache:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS news_cache (
                    item_id TEXT PRIMARY KEY,
                    title TEXT,
                    url TEXT,
                    source TEXT,
                    first_seen TEXT,
                    last_seen TEXT,
                    hit_count INTEGER DEFAULT 1
                )
            """)

    def filter_new(self, items: list[NewsItem]) -> list[NewsItem]:
        with sqlite3.connect(self.db_path) as conn:
            existing = set(
                row[0]
                for row in conn.execute(
                    "SELECT item_id FROM news_cache"
                ).fetchall()
            )
        return [it for it in items if it.item_id not in existing]

    def bulk_upsert(self, items: list[NewsItem]) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with sqlite3.connect(self.db_path) as conn:
            conn.executemany(
                """
                INSERT INTO news_cache (item_id, title, url, source, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    last_seen = excluded.last_seen,
                    hit_count = hit_count + 1
                """,
                [
                    (it.item_id, it.title, it.url, it.source, now, now)
                    for it in items
                ],
            )
