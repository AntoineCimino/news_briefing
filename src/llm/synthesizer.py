from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any

from src.llm.api_client import call_api
from src.llm.ollama_client import OllamaUnavailableError, call_ollama

SYSTEM_PROMPT = """Tu es un senior intelligence analyst couvrant l'intelligence artificielle, la technologie et les marches financiers mondiaux.

Ta mission est de produire un briefing quotidien a tres forte densite informationnelle a partir des signaux fournis.

Contraintes de sortie :
- Ecris tout en francais.
- Format markdown propre et lisible.
- Ton analytique, factuel, sans hype.
- Priorise ce qui change l'allocation du capital, la concurrence, la regulation, l'infrastructure IA et le sentiment de marche.
- Ignore les annonces marketing, les papiers de recherche mineurs et les actualites de faible impact.
- Fusionne les signaux redondants en une seule insight.
- Chaque bullet doit expliquer pourquoi cela compte.
- Ajoute des sources markdown en fin de bullet quand elles existent.
- N'invente aucun fait absent du contexte. Si un point n'est pas couvert, indique "Non documente dans les sources du jour".

Structure attendue :

# Briefing Quotidien IA, Tech et Marches

## Section 1 — Global Market Wrap
### Macro Drivers
### Major Indices
### Key Stocks & Sectors
### Commodities / FX / Crypto
### Market Narrative
### Forward Look

## Section 2 — AI & Technology Intelligence
### Top Strategic Developments
### Major Product / Model Releases
### Capital & Strategic Moves
### Emerging Signals
### What This Means

Regles supplementaires :
- "Top Strategic Developments" : maximum 5 points.
- "What This Means" : 3 a 5 bullets de synthese.
- Quand des donnees de marche sont disponibles, cite les variations importantes.
- Quand tu fais une inference, formule-la explicitement comme interpretation.
"""

SECTION_TITLES = {
    "ai_ecosystem": "ai",
    "research": "research",
    "tech_companies": "tech",
    "markets": "markets",
    "macro": "macro",
}

PROMPT_CATEGORY_QUOTAS = {
    "ai_ecosystem": 7,
    "tech_companies": 6,
    "markets": 5,
    "macro": 5,
    "research": 2,
}

TOP_STRATEGIC_LIMIT = 5


def _parse_published_at(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _hours_ago(value: str | None) -> str:
    published_at = _parse_published_at(value)
    delta = datetime.now(timezone.utc) - published_at
    hours = max(int(delta.total_seconds() // 3600), 0)
    return f"{hours}h"


def _format_change(value: float | int | None, digits: int = 2) -> str:
    if value is None:
        return "n/d"
    return f"{float(value):+.{digits}f}%"


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


class Synthesizer:
    def __init__(self, mode: str = "no-llm", model: str | None = None):
        self.mode = mode
        self.model = model

    def summarize_article(self, article: dict[str, Any]) -> str:
        summary = " ".join((article.get("summary") or "").split())
        if summary:
            first_sentence = summary.split(".")[0].strip()
            return first_sentence or summary[:220].strip()
        return article.get("title", "").strip()

    def build_briefing(
        self, articles: list[dict[str, Any]], market_data: list[dict[str, Any]]
    ) -> str:
        prompt = self._build_prompt(articles, market_data)
        if self.mode == "api":
            try:
                return call_api(prompt, model=self.model)
            except Exception:
                try:
                    return call_ollama(prompt, model=self.model)
                except OllamaUnavailableError:
                    return self._build_no_llm_briefing(articles, market_data)
        if self.mode == "local":
            try:
                return call_ollama(prompt, model=self.model)
            except OllamaUnavailableError:
                return self._build_no_llm_briefing(articles, market_data)
        return self._build_no_llm_briefing(articles, market_data)

    def _select_articles_for_prompt(
        self, articles: list[dict[str, Any]], limit: int = 22
    ) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for article in sorted(
            articles,
            key=lambda item: _safe_float(item.get("rank_score", item.get("score", 0.0))),
            reverse=True,
        ):
            grouped[article.get("category", "tech_companies")].append(article)

        selected: list[dict[str, Any]] = []
        seen_urls: set[str] = set()
        for category, quota in PROMPT_CATEGORY_QUOTAS.items():
            for article in grouped.get(category, [])[:quota]:
                url = article.get("url")
                if url and url in seen_urls:
                    continue
                selected.append(article)
                if url:
                    seen_urls.add(url)

        if len(selected) < limit:
            for article in grouped.get("research", [])[PROMPT_CATEGORY_QUOTAS["research"] :]:
                url = article.get("url")
                if url and url in seen_urls:
                    continue
                selected.append(article)
                if url:
                    seen_urls.add(url)
                if len(selected) >= limit:
                    break

        return selected[:limit]

    def _build_prompt(
        self, articles: list[dict[str, Any]], market_data: list[dict[str, Any]]
    ) -> str:
        selected_articles = self._select_articles_for_prompt(articles)
        article_lines = []
        for article in selected_articles:
            category = article.get("category", "tech_companies")
            title = article.get("title", "").strip()
            source = article.get("source", "unknown")
            summary = self.summarize_article(article)
            url = article.get("url", "")
            score = _safe_float(article.get("rank_score", article.get("score", 0.0)))
            article_lines.append(
                f"- score={score:.3f} | categorie={category} | source={source} | age={_hours_ago(article.get('published_at'))} | titre={title} | resume={summary} | url={url}"
            )

        market_lines = []
        for snapshot in market_data:
            market_lines.append(
                f"- {snapshot.get('label', snapshot.get('ticker', ''))}: prix={_safe_float(snapshot.get('price')):.2f}, variation={_format_change(snapshot.get('change_pct'))}, volume={_safe_float(snapshot.get('volume')):.0f}"
            )

        return (
            f"{SYSTEM_PROMPT}\n\n"
            f"Date de reference: {datetime.now(timezone.utc).date().isoformat()}\n"
            f"Fenetre d'analyse: dernieres 24 heures\n\n"
            "Contexte articles:\n"
            + "\n".join(article_lines or ["- Aucun article retenu"])
            + "\n\nContexte marche:\n"
            + "\n".join(market_lines or ["- Aucune donnee de marche disponible"])
        )

    def _articles_for_category(
        self, articles: list[dict[str, Any]], categories: set[str], limit: int
    ) -> list[dict[str, Any]]:
        selected = [
            article
            for article in articles
            if article.get("category", "tech_companies") in categories
        ]
        selected.sort(
            key=lambda item: _safe_float(item.get("rank_score", item.get("score", 0.0))),
            reverse=True,
        )
        return selected[:limit]

    def _format_article_bullet(self, article: dict[str, Any]) -> str:
        title = article.get("title", "").strip()
        summary = self.summarize_article(article)
        source = article.get("source", "source inconnue")
        url = article.get("url")
        if url:
            return f"- {title} : {summary}. Source: [{source}]({url})"
        return f"- {title} : {summary}. Source: {source}"

    def _market_map(self, market_data: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        return {snapshot.get("ticker", ""): snapshot for snapshot in market_data}

    def _market_line(self, market_map: dict[str, dict[str, Any]], ticker: str) -> str:
        snapshot = market_map.get(ticker)
        if not snapshot:
            return "- Non documente dans les sources du jour."
        label = snapshot.get("label", ticker)
        price = _safe_float(snapshot.get("price"))
        change_pct = _safe_float(snapshot.get("change_pct"))
        return f"- {label}: {price:.2f} ({change_pct:+.2f}%)"

    def _market_narrative(self, articles: list[dict[str, Any]], market_data: list[dict[str, Any]]) -> str:
        market_map = self._market_map(market_data)
        strongest_move = max(
            market_data,
            key=lambda item: abs(_safe_float(item.get("change_pct"))),
            default=None,
        )
        catalyst_titles = [
            article.get("title", "").strip()
            for article in self._articles_for_category(articles, {"macro", "markets"}, limit=2)
        ]
        parts: list[str] = []
        if strongest_move:
            parts.append(
                f"Le mouvement le plus marque porte sur {strongest_move.get('label', strongest_move.get('ticker', 'un actif'))} ({_format_change(strongest_move.get('change_pct'))})."
            )
        if catalyst_titles:
            parts.append(
                "Les catalyseurs dominants dans les sources du jour sont "
                + "; ".join(catalyst_titles)
                + "."
            )
        if market_map.get("VIX"):
            parts.append(
                f"Le VIX se situe a {_safe_float(market_map['VIX'].get('price')):.2f}, ce qui sert de point de repere sur l'appetit pour le risque."
            )
        return " ".join(parts) or "Le narratif de marche n'est pas suffisamment documente dans les sources du jour."

    def _emerging_signals(self, articles: list[dict[str, Any]], market_data: list[dict[str, Any]]) -> list[str]:
        category_counts = Counter(
            SECTION_TITLES.get(article.get("category", "tech_companies"), "tech")
            for article in articles
        )
        signals: list[str] = []
        if category_counts.get("ai", 0) >= 3:
            signals.append("- Les flux du jour restent fortement concentres sur l'IA appliquee et la competition produit.")
        if category_counts.get("markets", 0) + category_counts.get("macro", 0) >= 3:
            signals.append("- Les catalyseurs macro et de marche reprennent du poids dans la lecture des actifs technologiques.")
        if any(abs(_safe_float(item.get("change_pct"))) >= 2.5 for item in market_data):
            signals.append("- Les variations de prix depassant 2,5% sur plusieurs actifs signalent un regime de marche plus nerveux que la normale.")
        research_count = sum(1 for article in articles if article.get("category") == "research")
        if research_count:
            signals.append("- Les papiers de recherche restent abondants, mais peu d'entre eux semblent constituer un signal strategique autonome a ce stade.")
        return signals[:4] or ["- Peu de signaux transverses nets emergent du corpus du jour."]

    def _what_this_means(self, articles: list[dict[str, Any]], market_data: list[dict[str, Any]]) -> list[str]:
        bullets: list[str] = []
        if self._articles_for_category(articles, {"ai_ecosystem", "tech_companies"}, limit=1):
            bullets.append("- La concurrence IA reste tiree par la mise en production et la distribution, davantage que par la seule nouveaute technique.")
        if self._articles_for_category(articles, {"macro", "markets"}, limit=1):
            bullets.append("- Les conditions macro continuent d'influencer directement la valorisation des acteurs IA, du logiciel et des semi-conducteurs.")
        if any(item.get("ticker") in {"NVDA", "NASDAQ", "BTC"} for item in market_data):
            bullets.append("- Les actifs les plus sensibles au risque servent toujours de barometre pour l'appetit du marche envers le theme IA.")
        if self._articles_for_category(articles, {"research"}, limit=1):
            bullets.append("- Le flux de recherche reste intense, mais la rarete se situe dans la conversion en produits, partenariats et investissements deployes.")
        return bullets[:5] or ["- Les sources du jour ne permettent pas une lecture sectorielle robuste."]

    def _build_no_llm_briefing(
        self, articles: list[dict[str, Any]], market_data: list[dict[str, Any]]
    ) -> str:
        macro_articles = self._articles_for_category(articles, {"macro"}, limit=4)
        market_articles = self._articles_for_category(articles, {"markets"}, limit=4)
        ai_articles = self._articles_for_category(articles, {"ai_ecosystem", "research"}, limit=5)
        tech_articles = self._articles_for_category(articles, {"tech_companies"}, limit=5)
        capital_articles = [
            article
            for article in self._articles_for_category(
                articles,
                {"ai_ecosystem", "tech_companies", "markets", "macro"},
                limit=10,
            )
            if any(
                keyword in f"{article.get('title', '')} {article.get('summary', '')}".lower()
                for keyword in ("fund", "funding", "raise", "acqui", "partnership", "regulat", "deal", "invest")
            )
        ][:4]
        market_map = self._market_map(market_data)

        sections: list[str] = ["# Briefing Quotidien IA, Tech et Marches", ""]
        sections.append("## Section 1 — Global Market Wrap")
        sections.append("### Macro Drivers")
        if macro_articles:
            sections.extend(self._format_article_bullet(article) for article in macro_articles)
        else:
            sections.append("- Non documente dans les sources du jour.")

        sections.append("")
        sections.append("### Major Indices")
        sections.append(self._market_line(market_map, "SP500"))
        sections.append(self._market_line(market_map, "NASDAQ"))
        sections.append(self._market_line(market_map, "CAC40"))
        sections.append("- Marches asiatiques: non documentes dans les donnees de marche disponibles.")

        sections.append("")
        sections.append("### Key Stocks & Sectors")
        for ticker in ("NVDA", "MSFT", "META", "GOOGL", "AAPL"):
            sections.append(self._market_line(market_map, ticker))
        if tech_articles:
            sections.extend(self._format_article_bullet(article) for article in tech_articles[:2])

        sections.append("")
        sections.append("### Commodities / FX / Crypto")
        for ticker in ("OIL", "GOLD", "EURUSD", "BTC", "ETH"):
            sections.append(self._market_line(market_map, ticker))

        sections.append("")
        sections.append("### Market Narrative")
        sections.append(f"- {self._market_narrative(articles, market_data)}")

        sections.append("")
        sections.append("### Forward Look")
        if macro_articles or market_articles:
            forward_candidates = (macro_articles + market_articles)[:3]
            for article in forward_candidates:
                sections.append(
                    f"- A surveiller: prolongation potentielle du theme porte par \"{article.get('title', '').strip()}\". Source: [{article.get('source', 'source')}]({article.get('url', '')})"
                    if article.get("url")
                    else f"- A surveiller: prolongation potentielle du theme porte par \"{article.get('title', '').strip()}\"."
                )
        else:
            sections.append("- Aucun catalyseur clair sur 24-48h n'est explicite dans les sources disponibles.")

        sections.append("")
        sections.append("## Section 2 — AI & Technology Intelligence")
        sections.append("### Top Strategic Developments")
        top_strategic = (
            self._articles_for_category(articles, {"ai_ecosystem"}, limit=TOP_STRATEGIC_LIMIT - 1)
            + self._articles_for_category(articles, {"tech_companies"}, limit=2)
        )[:TOP_STRATEGIC_LIMIT]
        if top_strategic:
            sections.extend(self._format_article_bullet(article) for article in top_strategic)
        else:
            sections.append("- Non documente dans les sources du jour.")

        sections.append("")
        sections.append("### Major Product / Model Releases")
        if ai_articles:
            sections.extend(self._format_article_bullet(article) for article in ai_articles[:4])
        else:
            sections.append("- Non documente dans les sources du jour.")

        sections.append("")
        sections.append("### Capital & Strategic Moves")
        if capital_articles:
            sections.extend(self._format_article_bullet(article) for article in capital_articles)
        else:
            sections.append("- Aucun mouvement capitalistique ou reglementaire majeur n'apparait clairement dans le corpus du jour.")

        sections.append("")
        sections.append("### Emerging Signals")
        sections.extend(self._emerging_signals(articles, market_data))

        sections.append("")
        sections.append("### What This Means")
        sections.extend(self._what_this_means(articles, market_data))

        return "\n".join(sections)
