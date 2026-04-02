from __future__ import annotations

from collections import defaultdict
from typing import Any

BASE_THRESHOLDS = {
    "research": 0.55,
    "ai_ecosystem": 0.2,
    "tech_companies": 0.18,
    "markets": 0.18,
    "macro": 0.15,
}

MAX_PER_SOURCE = {
    "hacker_news": 3,
    "arxiv_ai": 1,
    "arxiv_ml": 1,
}

MAX_PER_CATEGORY = {
    "research": 2,
}

LOW_SIGNAL_TERMS = (
    "visual guide",
    "guide",
    "best deals",
    "sale",
    "review",
    "hands-on",
    "podcast",
    "live blog",
)

STRATEGIC_TERMS = (
    "fund",
    "valuation",
    "ipo",
    "earnings",
    "guidance",
    "acqui",
    "merger",
    "partner",
    "regulat",
    "antitrust",
    "chip",
    "semiconductor",
    "gpu",
    "cloud",
    "data center",
    "cyber",
    "security",
    "openai",
    "anthropic",
    "mistral",
    "gemini",
    "claude",
    "copilot",
)

HIGH_IMPACT_TERMS = (
    "fund",
    "valuation",
    "ipo",
    "earnings",
    "guidance",
    "acqui",
    "merger",
    "partner",
    "regulat",
    "antitrust",
    "chip",
    "semiconductor",
    "gpu",
    "cloud",
    "data center",
    "cyber",
    "security",
)

HARD_BLOCK_TERMS = (
    "big spring sale",
    "best deals",
)


def _article_score(article: dict[str, Any]) -> float:
    return float(article.get("rank_score", article.get("score", 0.0)))


def _text(article: dict[str, Any]) -> str:
    return f"{article.get('title', '')} {article.get('summary', '')}".lower()


def _is_low_signal(article: dict[str, Any]) -> bool:
    text = _text(article)
    if any(term in text for term in HARD_BLOCK_TERMS):
        return True
    if any(term in text for term in LOW_SIGNAL_TERMS) and not any(
        term in text for term in HIGH_IMPACT_TERMS
    ):
        return True
    return False


def _threshold_for(article: dict[str, Any], default_min_score: float) -> float:
    category = article.get("category", "tech_companies")
    threshold = BASE_THRESHOLDS.get(category, default_min_score)
    if article.get("source") == "hacker_news":
        threshold = max(threshold, 0.22)
    return max(default_min_score - 0.1, threshold)


def filter_articles(
    articles: list[dict[str, Any]], min_score: float = 0.3
) -> list[dict[str, Any]]:
    """Remove low-signal articles and keep a more balanced editorial mix."""
    filtered_articles: list[dict[str, Any]] = []
    per_source: defaultdict[str, int] = defaultdict(int)
    per_category: defaultdict[str, int] = defaultdict(int)

    for article in articles:
        category = article.get("category", "tech_companies")
        source = article.get("source", "")
        if _article_score(article) < _threshold_for(article, min_score):
            continue
        if _is_low_signal(article):
            continue
        if per_source[source] >= MAX_PER_SOURCE.get(source, 999_999):
            continue
        if per_category[category] >= MAX_PER_CATEGORY.get(category, 999_999):
            continue
        filtered_articles.append(article)
        per_source[source] += 1
        per_category[category] += 1

    return filtered_articles
