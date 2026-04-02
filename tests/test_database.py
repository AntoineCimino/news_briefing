from __future__ import annotations

from src.storage.database import BriefingDatabase


def test_insert_and_load_articles(tmp_path):
    db = BriefingDatabase(str(tmp_path / "briefings.db"))
    articles = [
        {
            "url": f"https://{index}",
            "title": f"title {index}",
            "source": "test",
            "published_at": "2026-03-30T10:00:00+00:00",
            "category": "tech_companies",
            "rank_score": 0.5,
            "summary": "summary",
        }
        for index in range(3)
    ]
    db.insert_articles(articles)
    assert len(db.load_today_articles()) == 3


def test_upsert_does_not_duplicate(tmp_path):
    db = BriefingDatabase(str(tmp_path / "briefings.db"))
    article = {
        "url": "https://same",
        "title": "title",
        "source": "test",
        "published_at": "2026-03-30T10:00:00+00:00",
        "category": "tech_companies",
        "rank_score": 0.5,
        "summary": "summary",
    }
    db.insert_articles([article])
    article["title"] = "updated"
    db.insert_articles([article])
    rows = db.load_today_articles()
    assert len(rows) == 1
    assert rows[0]["title"] == "updated"


def test_save_and_load_briefing(tmp_path):
    db = BriefingDatabase(str(tmp_path / "briefings.db"))
    briefing_id = db.save_briefing("content", "no-llm", 2)
    rows = db.load_briefings()
    assert rows[0]["briefing_id"] == briefing_id
    assert rows[0]["content"] == "content"


def test_load_latest_market_snapshot(tmp_path):
    db = BriefingDatabase(str(tmp_path / "briefings.db"))
    db.save_market_snapshots(
        [
            {
                "ticker": "SP500",
                "label": "S&P 500",
                "price": 100.0,
                "change_pct": 1.0,
                "volume": 10.0,
                "collected_at": "2026-03-30T10:00:00+00:00",
            },
            {
                "ticker": "SP500",
                "label": "S&P 500",
                "price": 110.0,
                "change_pct": 2.0,
                "volume": 11.0,
                "collected_at": "2026-03-30T11:00:00+00:00",
            },
        ]
    )
    latest = db.load_latest_market_snapshot()
    assert len(latest) == 1
    assert latest[0]["price"] == 110.0


def test_migration_safe(tmp_path):
    db_path = tmp_path / "briefings.db"
    db = BriefingDatabase(str(db_path))
    db.init_db()
    db.init_db()
