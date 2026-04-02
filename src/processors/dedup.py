from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def _parse_published_at(article: dict[str, Any]) -> datetime:
    published_at = article.get("published_at")
    if not published_at:
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = published_at.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _dedup_by_url(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: dict[str, dict[str, Any]] = {}
    for article in articles:
        url = article.get("url")
        if not url:
            continue
        current = deduped.get(url)
        if current is None or _parse_published_at(article) > _parse_published_at(current):
            deduped[url] = article
    return list(deduped.values())


def dedup_articles(articles: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    1. Dédup par URL exacte (dict keyed by url)
    2. Dédup par titre similaire : TF-IDF cosine > 0.85 -> garder le plus récent
    Returns deduplicated list.
    """
    unique_articles = _dedup_by_url(articles)
    if len(unique_articles) < 2:
        return unique_articles

    titles = [article.get("title", "").strip() for article in unique_articles]
    # Character n-grams are more robust than word-only TF-IDF for near-duplicate headlines.
    tfidf_matrix = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform(
        titles
    )
    similarity_matrix = cosine_similarity(tfidf_matrix)

    kept_indices: list[int] = []
    visited_indices: set[int] = set()

    for index, article in enumerate(unique_articles):
        if index in visited_indices:
            continue
        cluster_indices = {index}
        winner_index = index
        winner_article = article

        for other_index in range(index + 1, len(unique_articles)):
            if other_index in visited_indices:
                continue
            if similarity_matrix[index][other_index] <= 0.85:
                continue

            cluster_indices.add(other_index)
            other_article = unique_articles[other_index]
            if _parse_published_at(other_article) > _parse_published_at(winner_article):
                winner_index = other_index
                winner_article = other_article

        visited_indices.update(cluster_indices)
        kept_indices.append(winner_index)

    return [unique_articles[index] for index in kept_indices]
