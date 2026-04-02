from __future__ import annotations

from datetime import datetime, timezone
from math import exp
from typing import Any

AI_KEYWORDS = {
    "gpt": 2.0,
    "llm": 2.0,
    "claude": 2.0,
    "gemini": 2.0,
    "openai": 1.5,
    "anthropic": 1.5,
    "mistral": 1.5,
    "nvidia": 1.5,
    "ai": 1.0,
    "machine learning": 1.0,
    "deep learning": 1.0,
    "transformer": 1.0,
    "copilot": 1.0,
    "agent": 0.8,
    "inference": 1.0,
    "gpu": 1.2,
    "semiconductor": 1.2,
    "chip": 1.0,
    "data center": 1.0,
    "open source": 0.6,
}
MARKET_KEYWORDS = {
    "fed": 1.5,
    "inflation": 1.5,
    "interest rate": 1.5,
    "recession": 1.5,
    "earnings": 1.0,
    "guidance": 1.0,
    "funding": 1.2,
    "valuation": 1.2,
    "ipo": 1.0,
    "acquisition": 1.2,
    "merger": 1.2,
    "partnership": 1.0,
    "regulation": 1.0,
    "antitrust": 1.0,
    "export control": 1.0,
    "tariff": 1.0,
    "cyberattack": 0.8,
    "security": 0.6,
    "gdp": 1.0,
    "nasdaq": 1.0,
    "bitcoin": 1.0,
}
CATEGORY_WEIGHTS = {
    "ai_ecosystem": 1.15,
    "tech_companies": 1.0,
    "markets": 1.05,
    "macro": 1.05,
    "research": 0.45,
}
SOURCE_WEIGHTS = {
    "arxiv_ai": 0.2,
    "arxiv_ml": 0.2,
    "ft_markets": 0.95,
    "reuters_biz": 1.05,
    "reuters_tech": 1.05,
    "techcrunch": 1.0,
    "venturebeat": 0.95,
    "hacker_news": 0.9,
    "theverge": 0.8,
    "arstechnica": 0.9,
}
DECAY = 0.1
MAX_RELEVANCE = sum(AI_KEYWORDS.values()) + sum(MARKET_KEYWORDS.values())


def _parse_published_at(published_at: str | None) -> datetime:
    if not published_at:
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = published_at.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _freshness_score(article: dict[str, Any], now: datetime) -> float:
    delta = now - _parse_published_at(article.get("published_at"))
    hours_old = max(delta.total_seconds() / 3600, 0.0)
    return exp(-DECAY * hours_old)


def _relevance_score(article: dict[str, Any]) -> float:
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    score = 0.0
    for keyword, weight in {**AI_KEYWORDS, **MARKET_KEYWORDS}.items():
        score += text.count(keyword) * weight
    return min(score / MAX_RELEVANCE, 1.0)


def _engagement_score(article: dict[str, Any]) -> float:
    if article.get("source") != "hacker_news":
        return 0.0
    return min(float(article.get("score", 0.0)) / 500.0, 1.0)


def score_article(article: dict[str, Any], now: datetime | None = None) -> float:
    reference = now or datetime.now(timezone.utc)
    base_score = (
        _freshness_score(article, reference) * 0.4
        + _relevance_score(article) * 0.4
        + _engagement_score(article) * 0.2
    )
    category_weight = CATEGORY_WEIGHTS.get(article.get("category", "tech_companies"), 1.0)
    source_weight = SOURCE_WEIGHTS.get(article.get("source", ""), 1.0)
    return min(base_score * category_weight * source_weight, 1.0)


def rank_articles(
    articles: list[dict[str, Any]], now: datetime | None = None
) -> list[dict[str, Any]]:
    """Return articles sorted by composite score descending."""
    reference = now or datetime.now(timezone.utc)
    ranked_articles: list[dict[str, Any]] = []
    for article in articles:
        scored_article = dict(article)
        scored_article["rank_score"] = score_article(article, reference)
        ranked_articles.append(scored_article)
    ranked_articles.sort(key=lambda article: article["rank_score"], reverse=True)
    return ranked_articles
