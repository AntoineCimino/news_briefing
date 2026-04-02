from __future__ import annotations

from datetime import datetime, timedelta, timezone
import logging
from time import mktime
from typing import Any

import feedparser

LOGGER = logging.getLogger(__name__)

FEEDS = {
    "techcrunch": "https://techcrunch.com/feed/",
    "venturebeat": "https://venturebeat.com/feed/",
    "arstechnica": "https://feeds.arstechnica.com/arstechnica/index",
    "theverge": "https://www.theverge.com/rss/index.xml",
    "reuters_tech": "https://feeds.reuters.com/reuters/technologyNews",
    "arxiv_ai": "https://rss.arxiv.org/rss/cs.AI",
    "arxiv_ml": "https://rss.arxiv.org/rss/cs.LG",
    "reuters_biz": "https://feeds.reuters.com/reuters/businessNews",
    "ft_markets": "https://www.ft.com/markets?format=rss",
    "ft_technology": "https://www.ft.com/technology?format=rss",
}

SOURCE_CATEGORIES = {
    "techcrunch": "ai_ecosystem",
    "venturebeat": "ai_ecosystem",
    "arstechnica": "tech_companies",
    "theverge": "tech_companies",
    "reuters_tech": "tech_companies",
    "arxiv_ai": "research",
    "arxiv_ml": "research",
    "reuters_biz": "macro",
    "ft_markets": "markets",
    "ft_technology": "tech_companies",
}


def _coerce_datetime(entry: Any) -> datetime | None:
    published_parsed = getattr(entry, "published_parsed", None) or entry.get(
        "published_parsed"
    )
    if published_parsed is not None:
        return datetime.fromtimestamp(mktime(published_parsed), tz=timezone.utc)
    return None


def _normalize_entry(source: str, entry: Any) -> dict[str, Any] | None:
    title = getattr(entry, "title", None) or entry.get("title")
    url = getattr(entry, "link", None) or entry.get("link")
    published_at = _coerce_datetime(entry)
    if not title or not url or published_at is None:
        return None

    summary = getattr(entry, "summary", None) or entry.get("summary") or ""
    return {
        "title": title.strip(),
        "url": url.strip(),
        "source": source,
        "published_at": published_at.isoformat(),
        "summary": summary.strip()[:500],
        "category": SOURCE_CATEGORIES.get(source, "tech_companies"),
        "score": 0.0,
    }


def fetch_rss_articles(lookback_hours: int = 24) -> list[dict[str, Any]]:
    """Fetch all RSS feeds, filter by lookback window, normalize to Article schema."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=lookback_hours)
    articles: list[dict[str, Any]] = []

    for source, url in FEEDS.items():
        try:
            parsed_feed = feedparser.parse(url, request_headers={"User-Agent": "news-briefing/1.0"})
        except Exception:
            LOGGER.exception("Failed to parse RSS feed %s", source)
            continue

        for entry in getattr(parsed_feed, "entries", []):
            article = _normalize_entry(source, entry)
            if article is None:
                continue
            published_at = datetime.fromisoformat(article["published_at"])
            if published_at >= cutoff:
                articles.append(article)

    return articles
