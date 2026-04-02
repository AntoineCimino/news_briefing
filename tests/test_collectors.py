from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from time import gmtime

from src.collectors.hn_collector import fetch_hn_articles
from src.collectors.market_collector import TICKERS, fetch_market_snapshot
from src.collectors.newsapi_collector import fetch_newsapi_articles
from src.collectors.rss_collector import FEEDS, fetch_rss_articles


def test_rss_fetch_normalizes_articles(monkeypatch):
    now = datetime.now(timezone.utc)
    fresh_entry = {
        "title": "Fresh item",
        "link": "https://example.com/fresh",
        "published_parsed": gmtime(now.timestamp()),
        "summary": "a" * 700,
    }

    def fake_parse(url, request_headers=None):
        return SimpleNamespace(entries=[fresh_entry])

    monkeypatch.setattr("src.collectors.rss_collector.feedparser.parse", fake_parse)

    articles = fetch_rss_articles()

    assert len(articles) == len(FEEDS)
    assert articles[0]["url"] == "https://example.com/fresh"
    assert len(articles[0]["summary"]) == 500
    assert articles[0]["score"] == 0.0


def test_rss_filters_old_articles(monkeypatch):
    now = datetime.now(timezone.utc)
    old_entry = {
        "title": "Old item",
        "link": "https://example.com/old",
        "published_parsed": gmtime((now - timedelta(hours=48)).timestamp()),
        "summary": "old",
    }

    monkeypatch.setattr(
        "src.collectors.rss_collector.feedparser.parse",
        lambda url, request_headers=None: SimpleNamespace(entries=[old_entry]),
    )

    assert fetch_rss_articles(lookback_hours=24) == []


def test_hn_fetch_filters_by_score(monkeypatch):
    ids = [1, 2, 3]
    items = {
        1: {"type": "story", "title": "AI launch", "url": "https://a", "time": 1710000000, "score": 120},
        2: {"type": "story", "title": "Low score", "url": "https://b", "time": 1710000001, "score": 10},
        3: {"type": "comment", "title": "Ignore", "url": "https://c", "time": 1710000002, "score": 300},
    }

    def fake_fetch_json(url, timeout=10):
        if url.endswith("topstories.json"):
            return ids
        item_id = int(url.rsplit("/", 1)[-1].split(".")[0])
        return items[item_id]

    monkeypatch.setattr("src.collectors.hn_collector._fetch_json", fake_fetch_json)

    articles = fetch_hn_articles(top_n=5, min_score=50)

    assert len(articles) == 1
    assert articles[0]["title"] == "AI launch"
    assert articles[0]["category"] == "ai_ecosystem"


def test_market_snapshot_schema(monkeypatch):
    class FakeTicker:
        def __init__(self, ticker):
            self.info = {
                "regularMarketPrice": 100.0,
                "regularMarketChangePercent": 1.5,
                "regularMarketVolume": 123456,
            }

    monkeypatch.setattr("src.collectors.market_collector.yf.Ticker", FakeTicker)

    snapshot = fetch_market_snapshot()

    assert len(snapshot) == len(TICKERS)
    first = snapshot[0]
    assert set(first) == {"ticker", "label", "price", "change_pct", "volume", "collected_at"}
    assert first["price"] == 100.0
    assert first["change_pct"] == 1.5


def test_newsapi_skipped_without_key(monkeypatch):
    monkeypatch.delenv("NEWSAPI_KEY", raising=False)
    assert fetch_newsapi_articles() == []
