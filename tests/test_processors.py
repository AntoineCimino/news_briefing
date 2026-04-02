from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src.processors.categorizer import categorize_article
from src.processors.dedup import dedup_articles
from src.processors.ranker import rank_articles
from src.processors.relevance_filter import filter_articles


def _article(
    title: str,
    url: str,
    published_at: datetime,
    summary: str = "",
    source: str = "techcrunch",
    score: float = 0.0,
) -> dict:
    return {
        "title": title,
        "url": url,
        "source": source,
        "published_at": published_at.isoformat(),
        "summary": summary,
        "category": "tech_companies",
        "score": score,
    }


def test_dedup_exact_url():
    now = datetime.now(timezone.utc)
    older = _article("First title", "https://same", now - timedelta(hours=2))
    newer = _article("Updated title", "https://same", now - timedelta(hours=1))

    result = dedup_articles([older, newer])

    assert len(result) == 1
    assert result[0]["title"] == "Updated title"


def test_dedup_similar_title():
    now = datetime.now(timezone.utc)
    articles = [
        _article(
            "OpenAI launches new GPT model for developers",
            "https://a",
            now - timedelta(hours=2),
        ),
        _article(
            "OpenAI launches new GPT model for developers!",
            "https://b",
            now - timedelta(hours=1),
        ),
    ]

    result = dedup_articles(articles)

    assert len(result) == 1
    assert result[0]["url"] == "https://b"


def test_ranker_orders_by_freshness():
    now = datetime.now(timezone.utc)
    recent = _article("Neutral update", "https://recent", now - timedelta(hours=1))
    old = _article("Neutral update", "https://old", now - timedelta(hours=20))

    ranked = rank_articles([old, recent], now=now)

    assert ranked[0]["url"] == "https://recent"
    assert ranked[0]["rank_score"] > ranked[1]["rank_score"]


def test_ranker_engagement_boost():
    now = datetime.now(timezone.utc)
    standard = _article(
        "Tech company ships release",
        "https://standard",
        now - timedelta(hours=1),
        source="techcrunch",
    )
    hn_story = _article(
        "Tech company ships release",
        "https://hn",
        now - timedelta(hours=1),
        source="hacker_news",
        score=450,
    )

    ranked = rank_articles([standard, hn_story], now=now)

    assert ranked[0]["url"] == "https://hn"


def test_filter_removes_low_score():
    articles = [
        {"title": "keep", "rank_score": 0.5},
        {"title": "drop", "rank_score": 0.1},
    ]

    filtered = filter_articles(articles, min_score=0.3)

    assert [article["title"] for article in filtered] == ["keep"]


def test_filter_drops_low_signal_guides():
    articles = [
        {"title": "Claude Code Unpacked : A visual guide", "rank_score": 0.9, "category": "tech_companies", "source": "hacker_news", "summary": ""},
        {"title": "OpenAI raises funding at new valuation", "rank_score": 0.4, "category": "ai_ecosystem", "source": "hacker_news", "summary": ""},
    ]

    filtered = filter_articles(articles, min_score=0.3)

    assert [article["title"] for article in filtered] == ["OpenAI raises funding at new valuation"]


def test_filter_caps_research_articles():
    articles = [
        {"title": "paper 1", "rank_score": 0.9, "category": "research", "source": "arxiv_ai", "summary": ""},
        {"title": "paper 2", "rank_score": 0.8, "category": "research", "source": "arxiv_ml", "summary": ""},
        {"title": "paper 3", "rank_score": 0.7, "category": "research", "source": "arxiv_ai", "summary": ""},
    ]

    filtered = filter_articles(articles, min_score=0.3)

    assert [article["title"] for article in filtered] == ["paper 1", "paper 2"]


def test_categorizer_ai_keywords():
    article = {
        "title": "OpenAI releases GPT-5",
        "summary": "A new flagship model for developers.",
    }

    assert categorize_article(article) == "ai_ecosystem"
