from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

import requests

HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
AI_HINTS = ("ai", "llm", "gpt")


def _fetch_json(url: str, timeout: int = 10) -> Any:
    response = requests.get(url, timeout=timeout)
    response.raise_for_status()
    return response.json()


def _fetch_item(item_id: int) -> dict[str, Any] | None:
    item = _fetch_json(HN_ITEM.format(id=item_id))
    if not isinstance(item, dict):
        return None
    return item


def _categorize(title: str) -> str:
    lower_title = title.lower()
    if any(hint in lower_title for hint in AI_HINTS):
        return "ai_ecosystem"
    return "tech_companies"


def fetch_hn_articles(top_n: int = 30, min_score: int = 50) -> list[dict[str, Any]]:
    """Fetch top N HN stories, filter by score, normalize to Article schema."""
    story_ids = _fetch_json(HN_TOP_STORIES, timeout=10)[:100]
    with ThreadPoolExecutor(max_workers=10) as executor:
        items = list(executor.map(_fetch_item, story_ids))

    articles: list[dict[str, Any]] = []
    for item in items:
        if not item or item.get("type") != "story":
            continue
        score = float(item.get("score", 0))
        if score < min_score:
            continue
        title = item.get("title")
        url = item.get("url")
        item_time = item.get("time")
        if not title or not url or not item_time:
            continue
        articles.append(
            {
                "title": title.strip(),
                "url": url.strip(),
                "source": "hacker_news",
                "published_at": datetime.fromtimestamp(
                    item_time, tz=timezone.utc
                ).isoformat(),
                "summary": "",
                "category": _categorize(title),
                "score": score,
            }
        )

    articles.sort(key=lambda article: article["score"], reverse=True)
    return articles[:top_n]
