from __future__ import annotations

from typing import Iterable

RESEARCH_KEYWORDS = (
    "arxiv",
    "paper",
    "research",
    "benchmark",
    "dataset",
    "transformer",
)
AI_KEYWORDS = (
    "gpt",
    "llm",
    "openai",
    "anthropic",
    "claude",
    "gemini",
    "mistral",
    "machine learning",
    "deep learning",
    "artificial intelligence",
    "ai",
)
MARKET_KEYWORDS = (
    "nasdaq",
    "s&p",
    "bitcoin",
    "ethereum",
    "stock",
    "market",
    "earnings",
    "shares",
    "crypto",
)
MACRO_KEYWORDS = (
    "fed",
    "ecb",
    "interest rate",
    "inflation",
    "gdp",
    "recession",
    "central bank",
    "tariff",
    "geopolitics",
)


def _contains_any(text: str, keywords: Iterable[str]) -> bool:
    return any(keyword in text for keyword in keywords)


def categorize_article(article: dict) -> str:
    """
    Returns category string based on title + summary keywords.
    Priority: research > ai_ecosystem > markets > macro > tech_companies
    """
    text = f"{article.get('title', '')} {article.get('summary', '')}".lower()
    if _contains_any(text, RESEARCH_KEYWORDS):
        return "research"
    if _contains_any(text, AI_KEYWORDS):
        return "ai_ecosystem"
    if _contains_any(text, MARKET_KEYWORDS):
        return "markets"
    if _contains_any(text, MACRO_KEYWORDS):
        return "macro"
    return "tech_companies"
