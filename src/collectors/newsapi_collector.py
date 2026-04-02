from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
from typing import Any

import requests

NEWSAPI_URL = "https://newsapi.org/v2/everything"
QUERIES = [
    "artificial intelligence",
    "LLM",
    "machine learning",
    "financial markets",
]


def fetch_newsapi_articles(
    existing_articles: list[dict[str, Any]] | None = None, lookback_hours: int = 24
) -> list[dict[str, Any]]:
    """Fetch NewsAPI articles when NEWSAPI_KEY is configured."""
    api_key = os.getenv("NEWSAPI_KEY")
    if not api_key:
        return []

    seen_urls = {article.get("url") for article in (existing_articles or [])}
    from_date = (datetime.now(timezone.utc) - timedelta(hours=lookback_hours)).isoformat()
    articles: list[dict[str, Any]] = []

    for query in QUERIES:
        response = requests.get(
            NEWSAPI_URL,
            timeout=10,
            params={
                "q": query,
                "from": from_date,
                "language": "en",
                "sortBy": "publishedAt",
                "pageSize": 20,
                "apiKey": api_key,
            },
        )
        response.raise_for_status()
        payload = response.json()
        for article in payload.get("articles", []):
            url = article.get("url")
            title = article.get("title")
            published_at = article.get("publishedAt")
            if not url or not title or not published_at or url in seen_urls:
                continue
            seen_urls.add(url)
            articles.append(
                {
                    "title": title.strip(),
                    "url": url.strip(),
                    "source": "newsapi",
                    "published_at": published_at,
                    "summary": (article.get("description") or "").strip()[:500],
                    "category": "ai_ecosystem" if query != "financial markets" else "markets",
                    "score": 0.0,
                }
            )

    return articles
