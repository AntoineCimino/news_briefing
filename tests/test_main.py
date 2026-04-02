from __future__ import annotations

from datetime import datetime, timezone

from src.main import collect_only, run, status


class FakeDB:
    def __init__(self):
        self.articles = []
        self.market = []
        self.briefings = []

        class FakePath:
            def exists(self):
                return True

            def stat(self):
                class Stat:
                    st_size = 1024 * 1024

                return Stat()

        self.db_path = FakePath()

    def insert_articles(self, articles):
        self.articles.extend(articles)
        return len(articles)

    def save_market_snapshots(self, snapshots):
        self.market.extend(snapshots)

    def save_briefing(self, content, mode, article_count):
        self.briefings.append((content, mode, article_count))
        return "briefing-1"

    def load_briefings(self, limit=1):
        if not self.briefings:
            return []
        content, mode, article_count = self.briefings[-1]
        return [
            {
                "created_at": "2026-03-30T10:00:00+00:00",
                "mode": mode,
                "content": content,
                "article_count": article_count,
            }
        ]

    def load_today_articles(self, category=None):
        return self.articles

    def load_latest_market_snapshot(self):
        return self.market


def _article():
    return {
        "title": "OpenAI ships GPT release",
        "url": "https://example.com/article",
        "source": "techcrunch",
        "published_at": datetime.now(timezone.utc).isoformat(),
        "summary": "OpenAI released a new GPT model for developers.",
        "category": "ai_ecosystem",
        "score": 0.0,
    }


def test_run_no_llm_end_to_end(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr("src.main.fetch_rss_articles", lambda lookback: [_article()])
    monkeypatch.setattr("src.main.fetch_hn_articles", lambda: [])
    monkeypatch.setattr("src.main.fetch_newsapi_articles", lambda existing_articles, lookback_hours: [])
    monkeypatch.setattr(
        "src.main.fetch_market_snapshot",
        lambda: [{"ticker": "SP500", "label": "S&P 500", "price": 1.0, "change_pct": 0.1, "volume": 10, "collected_at": "2026-03-30T10:00:00+00:00"}],
    )

    briefing = run("no-llm", db=db)

    assert db.articles
    assert db.market
    assert db.briefings
    assert "# Briefing Quotidien IA, Tech et Marches" in briefing


def test_collect_only_skips_llm(monkeypatch):
    db = FakeDB()
    monkeypatch.setattr("src.main.fetch_rss_articles", lambda lookback: [_article()])
    monkeypatch.setattr("src.main.fetch_hn_articles", lambda: [])
    monkeypatch.setattr("src.main.fetch_newsapi_articles", lambda existing_articles, lookback_hours: [])
    monkeypatch.setattr(
        "src.main.fetch_market_snapshot",
        lambda: [{"ticker": "SP500", "label": "S&P 500", "price": 1.0, "change_pct": 0.1, "volume": 10, "collected_at": "2026-03-30T10:00:00+00:00"}],
    )
    monkeypatch.setattr(
        "src.main.Synthesizer",
        lambda mode: (_ for _ in ()).throw(AssertionError("Synthesizer should not be called")),
    )

    count = collect_only(db=db)

    assert count == 1
    assert not db.briefings


def test_status_output():
    db = FakeDB()
    db.articles.append(_article())
    db.market.append({"ticker": "SP500"})
    db.briefings.append(("content", "no-llm", 1))
    output = status(db=db)
    assert "Articles collected today: 1" in output
    assert "Last briefing: 2026-03-30T10:00:00+00:00 (mode: no-llm)" in output
