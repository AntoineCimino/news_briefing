from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sqlite3
import uuid


class BriefingDatabase:
    def __init__(self, db_path: str = "data/processed/briefings.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection

    def init_db(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS articles (
                    url TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    source TEXT,
                    published_at TEXT,
                    category TEXT,
                    relevance_score REAL DEFAULT 0.0,
                    summary TEXT,
                    collected_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS briefings (
                    briefing_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    mode TEXT NOT NULL,
                    content TEXT,
                    article_count INTEGER DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS market_snapshots (
                    snapshot_id TEXT PRIMARY KEY,
                    collected_at TEXT NOT NULL,
                    ticker TEXT NOT NULL,
                    label TEXT,
                    price REAL,
                    change_pct REAL,
                    volume REAL
                );
                """
            )

    def insert_articles(self, articles: list[dict]) -> int:
        collected_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            for article in articles:
                connection.execute(
                    """
                    INSERT INTO articles (
                        url, title, source, published_at, category, relevance_score, summary, collected_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(url) DO UPDATE SET
                        title=excluded.title,
                        source=excluded.source,
                        published_at=excluded.published_at,
                        category=excluded.category,
                        relevance_score=excluded.relevance_score,
                        summary=excluded.summary,
                        collected_at=excluded.collected_at
                    """,
                    (
                        article["url"],
                        article["title"],
                        article.get("source"),
                        article.get("published_at"),
                        article.get("category"),
                        float(article.get("rank_score", article.get("score", 0.0))),
                        article.get("summary", ""),
                        collected_at,
                    ),
                )
        return len(articles)

    def load_today_articles(self, category: str | None = None) -> list[dict]:
        today_prefix = datetime.now(timezone.utc).date().isoformat()
        query = "SELECT * FROM articles WHERE collected_at LIKE ?"
        params: list[str] = [f"{today_prefix}%"]
        if category:
            query += " AND category = ?"
            params.append(category)
        query += " ORDER BY published_at DESC"
        with self._connect() as connection:
            rows = connection.execute(query, params).fetchall()
        return [dict(row) for row in rows]

    def save_briefing(self, content: str, mode: str, article_count: int) -> str:
        briefing_id = uuid.uuid4().hex[:12]
        created_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO briefings (briefing_id, created_at, mode, content, article_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (briefing_id, created_at, mode, content, article_count),
            )
        return briefing_id

    def load_briefings(self, limit: int = 7) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM briefings ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [dict(row) for row in rows]

    def save_market_snapshots(self, snapshots: list[dict]) -> None:
        with self._connect() as connection:
            for snapshot in snapshots:
                connection.execute(
                    """
                    INSERT INTO market_snapshots (
                        snapshot_id, collected_at, ticker, label, price, change_pct, volume
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex[:12],
                        snapshot.get("collected_at"),
                        snapshot.get("ticker"),
                        snapshot.get("label"),
                        snapshot.get("price"),
                        snapshot.get("change_pct"),
                        snapshot.get("volume"),
                    ),
                )

    def load_latest_market_snapshot(self) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT ms.*
                FROM market_snapshots ms
                JOIN (
                    SELECT ticker, MAX(collected_at) AS latest_collected_at
                    FROM market_snapshots
                    GROUP BY ticker
                ) latest
                ON ms.ticker = latest.ticker AND ms.collected_at = latest.latest_collected_at
                ORDER BY ms.ticker
                """
            ).fetchall()
        return [dict(row) for row in rows]
