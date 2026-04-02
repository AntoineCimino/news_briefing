# News Briefing — Task Backlog

---

## [TODO] FEAT-001 — Collecteurs de données (fondation)

Added: 2026-03-23 | Priority: Critique
Playbook: feature_development

### Contexte
Construire les collecteurs de données brutes qui alimentent tout le pipeline.
Chaque collecteur est un module indépendant, sans effet de bord, retournant une liste de dicts `Article`.

### Schéma Article normalisé
```python
{
    "title": str,
    "url": str,           # clé de déduplication
    "source": str,        # ex: "techcrunch", "reuters", "hn"
    "published_at": str,  # ISO datetime
    "summary": str,       # premier paragraphe ou description RSS
    "category": str,      # "ai_ecosystem" | "tech_companies" | "markets" | "macro" | "research"
    "score": float,       # HN points ou 0.0
}
```

### Étape 1 — `src/collectors/rss_collector.py`

**Flux RSS à implémenter :**
```python
FEEDS = {
    # Tech / IA générale
    "techcrunch":    "https://techcrunch.com/feed/",
    "venturebeat":   "https://venturebeat.com/feed/",
    "arstechnica":   "https://feeds.arstechnica.com/arstechnica/index",
    "theverge":      "https://www.theverge.com/rss/index.xml",
    "reuters_tech":  "https://feeds.reuters.com/reuters/technologyNews",
    # Recherche IA
    "arxiv_ai":      "https://rss.arxiv.org/rss/cs.AI",
    "arxiv_ml":      "https://rss.arxiv.org/rss/cs.LG",
    # Finance / macro
    "reuters_biz":   "https://feeds.reuters.com/reuters/businessNews",
    "ft_markets":    "https://www.ft.com/rss/home/uk",
}
```

**Fonction principale :**
```python
def fetch_rss_articles(lookback_hours: int = 24) -> list[dict]:
    """Fetch all RSS feeds, filter by lookback window, normalize to Article schema."""
```

**Requirements :**
- `feedparser.parse()` avec timeout 10s
- Filtrer `published_at >= now - lookback_hours`
- Tronquer `summary` à 500 chars
- Catégorisation automatique par source (`arxiv_*` → "research", `reuters_biz` → "macro", etc.)
- Logger les flux en erreur (pas de raise)

### Étape 2 — `src/collectors/hn_collector.py`

**API Hacker News (officielle, sans clé) :**
```python
HN_TOP_STORIES = "https://hacker-news.firebaseio.com/v0/topstories.json"
HN_ITEM = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
```

**Fonction principale :**
```python
def fetch_hn_articles(top_n: int = 30, min_score: int = 50) -> list[dict]:
    """Fetch top N HN stories, filter by score, normalize to Article schema."""
```

**Requirements :**
- Fetch top 100 IDs → filter by `score >= min_score` → garder top_n
- `category` = "ai_ecosystem" si "AI" / "LLM" / "GPT" in title (case-insensitive), sinon "tech_companies"
- `source` = "hacker_news"
- Paralléliser les requêtes item avec `ThreadPoolExecutor(max_workers=10)`

### Étape 3 — `src/collectors/market_collector.py`

**Tickers surveillés :**
```python
TICKERS = {
    # Indices
    "SP500":  "^GSPC",
    "NASDAQ": "^IXIC",
    "CAC40":  "^FCHI",
    "VIX":    "^VIX",
    # Tech majors
    "NVDA": "NVDA", "MSFT": "MSFT", "GOOGL": "GOOGL", "META": "META", "AAPL": "AAPL",
    # Crypto
    "BTC":    "BTC-USD",
    "ETH":    "ETH-USD",
    # Commodités
    "GOLD":   "GC=F",
    "OIL":    "CL=F",
    # FX
    "EURUSD": "EURUSD=X",
}
```

**Fonction principale :**
```python
def fetch_market_snapshot() -> list[dict]:
    """Fetch latest price + 1d change% for all tickers. Returns list of market dicts."""
```

**Schéma market dict :**
```python
{
    "ticker": str,
    "label": str,         # ex: "S&P 500"
    "price": float,
    "change_pct": float,  # variation 1 jour en %
    "volume": float,
    "collected_at": str,  # ISO datetime
}
```

### Étape 4 — `src/collectors/newsapi_collector.py`

**Requirements :**
- Conditionnel : ne s'exécute que si `NEWSAPI_KEY` est défini dans `.env`
- Endpoint : `https://newsapi.org/v2/everything`
- Queries : `["artificial intelligence", "LLM", "machine learning", "financial markets"]`
- Déduplication préalable avec les articles RSS déjà collectés (même URL)

### Tests — `tests/test_collectors.py`
- `test_rss_fetch_normalizes_articles` : mock `feedparser.parse()`, vérifie schéma Article
- `test_rss_filters_old_articles` : articles > 24h filtrés
- `test_hn_fetch_filters_by_score` : articles < min_score exclus
- `test_market_snapshot_schema` : mock `yfinance.Ticker`, vérifie tous les champs
- `test_newsapi_skipped_without_key` : retourne [] si pas de clé

---

## [TODO] FEAT-002 — Pipeline de traitement

Added: 2026-03-23 | Priority: Haute
Playbook: feature_development

### Contexte
Traiter les articles bruts : dédupliquer, scorer, filtrer, catégoriser.
Tous les processeurs sont des **fonctions pures** (entrée liste → sortie liste).

### Étape 1 — `src/processors/dedup.py`

```python
def dedup_articles(articles: list[dict]) -> list[dict]:
    """
    1. Dédup par URL exacte (dict keyed by url)
    2. Dédup par titre similaire : TF-IDF cosine > 0.85 → garder le plus récent
    Returns deduplicated list.
    """
```

**Requirements :**
- `sklearn.feature_extraction.text.TfidfVectorizer` + `cosine_similarity`
- Grouper d'abord par URL, ensuite clustering par similarité titre
- Complexité acceptable : O(n²) sur ~200 articles max

### Étape 2 — `src/processors/ranker.py`

**Score composite :**
```python
score = freshness_score * 0.4 + relevance_score * 0.4 + engagement_score * 0.2

# freshness : exp(-decay * hours_old), decay = 0.1
# relevance : comptage keywords pondérés (voir liste)
# engagement : min(hn_score / 500, 1.0), 0.0 si non HN
```

**Keywords de pertinence (avec poids) :**
```python
AI_KEYWORDS = {
    "gpt": 2.0, "llm": 2.0, "claude": 2.0, "gemini": 2.0, "openai": 1.5,
    "anthropic": 1.5, "mistral": 1.5, "nvidia": 1.5, "ai": 1.0,
    "machine learning": 1.0, "deep learning": 1.0, "transformer": 1.0,
}
MARKET_KEYWORDS = {
    "fed": 1.5, "inflation": 1.5, "interest rate": 1.5, "recession": 1.5,
    "earnings": 1.0, "gdp": 1.0, "nasdaq": 1.0, "bitcoin": 1.0,
}
```

### Étape 3 — `src/processors/relevance_filter.py`

```python
def filter_articles(articles: list[dict], min_score: float = 0.3) -> list[dict]:
    """Remove articles below relevance threshold."""
```

### Étape 4 — `src/processors/categorizer.py`

```python
def categorize_article(article: dict) -> str:
    """
    Returns category string based on title + summary keywords.
    Priority: research > ai_ecosystem > markets > macro > tech_companies
    """
```

### Tests — `tests/test_processors.py`
- `test_dedup_exact_url` : 2 articles même URL → 1 retourné
- `test_dedup_similar_title` : cosine > 0.85 → dédupliqué
- `test_ranker_orders_by_freshness` : article récent avant article ancien
- `test_ranker_engagement_boost` : HN article avec score élevé monte
- `test_filter_removes_low_score` : articles < seuil exclus
- `test_categorizer_ai_keywords` : "OpenAI releases GPT-5" → "ai_ecosystem"

---

## [TODO] FEAT-003 — Synthèse LLM multi-mode

Added: 2026-03-23 | Priority: Haute
Playbook: feature_development

### Contexte
Générer un briefing quotidien structuré à partir des articles triés.
Trois modes : no-llm (résumé brut), local (Ollama), api (OpenAI ou Anthropic).
Fallback automatique vers no-llm si le LLM est indisponible.

### Étape 1 — `src/llm/synthesizer.py`

**Classe principale :**
```python
class Synthesizer:
    def __init__(self, mode: str = "no-llm"):
        # mode: "no-llm" | "local" | "api"

    def build_briefing(self, articles: list[dict], market_data: list[dict]) -> str:
        """Generate full daily briefing. Returns markdown string."""

    def summarize_article(self, article: dict) -> str:
        """One-sentence summary of article. Falls back to original summary."""
```

**Prompt système pour LLM :**
```
Tu es un analyste financier et technologique senior.
Génère un briefing quotidien en français, structuré en sections :
1. 🤖 IA & Modèles (nouveaux modèles, funding, recherche)
2. 💻 Tech (entreprises tech, produits)
3. 📈 Marchés (variations notables, macro)
4. 🌍 Macro (banques centrales, géopolitique)

Pour chaque section : 3-5 bullet points. Ton neutre, factuel, concis.
Termine par : "📊 Données de marché" avec tableau prix/variation.
```

### Étape 2 — `src/llm/ollama_client.py`

```python
def call_ollama(prompt: str, model: str = "llama3.2:3b", timeout: int = 60) -> str:
    """Call local Ollama API. Raises OllamaUnavailableError if unreachable."""
```

**Requirements :**
- `requests.post(f"{OLLAMA_HOST}/api/generate", ...)`
- Streaming response : accumulate chunks
- Timeout 60s
- `OllamaUnavailableError` si connexion échoue → Synthesizer capte et fallback

### Étape 3 — `src/llm/api_client.py`

```python
def call_api(prompt: str) -> str:
    """
    Call OpenAI or Anthropic API (whichever key is set).
    Preference: Anthropic (claude-haiku-4-5) > OpenAI (gpt-4o-mini)
    """
```

**Requirements :**
- Si `ANTHROPIC_API_KEY` → utiliser `anthropic` SDK, modèle `claude-haiku-4-5-20251001`
- Sinon si `OPENAI_API_KEY` → utiliser `openai` SDK, modèle `gpt-4o-mini`
- Max tokens : 1500
- Temperature : 0.3 (factuel)

### Étape 4 — Fallback chain

```
mode=api → essaye API → échec → essaye Ollama → échec → no-llm
mode=local → essaye Ollama → échec → no-llm
mode=no-llm → format structuré sans LLM (bullet points des titres top articles)
```

### Tests — `tests/test_synthesizer.py`
- `test_no_llm_returns_structured_markdown` : retourne markdown sans LLM call
- `test_ollama_called_in_local_mode` : mock `call_ollama`, vérifie appel
- `test_api_called_in_api_mode` : mock `call_api`, vérifie appel
- `test_fallback_ollama_to_nollm` : `call_ollama` raises → fallback no-llm
- `test_fallback_api_to_ollama_to_nollm` : double fallback chain

---

## [TODO] FEAT-004 — Stockage SQLite

Added: 2026-03-23 | Priority: Haute
Playbook: feature_development

### Contexte
Persister articles, briefings et snapshots marché dans SQLite.
Pattern : migrations safe avec `ALTER TABLE IF NOT EXISTS`.

### Étape 1 — `src/storage/database.py`

**Tables :**
```sql
CREATE TABLE IF NOT EXISTS articles (
    url             TEXT PRIMARY KEY,
    title           TEXT NOT NULL,
    source          TEXT,
    published_at    TEXT,
    category        TEXT,
    relevance_score REAL DEFAULT 0.0,
    summary         TEXT,
    collected_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS briefings (
    briefing_id     TEXT PRIMARY KEY,  -- uuid hex[:12]
    created_at      TEXT NOT NULL,
    mode            TEXT NOT NULL,     -- no-llm | local | api
    content         TEXT,              -- markdown du briefing
    article_count   INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS market_snapshots (
    snapshot_id     TEXT PRIMARY KEY,  -- uuid hex[:12]
    collected_at    TEXT NOT NULL,
    ticker          TEXT NOT NULL,
    label           TEXT,
    price           REAL,
    change_pct      REAL,
    volume          REAL
);
```

**Classe :**
```python
class BriefingDatabase:
    def __init__(self, db_path: str = "data/processed/briefings.db"):

    def init_db(self) -> None:
        """Create tables + safe migrations."""

    def insert_articles(self, articles: list[dict]) -> int:
        """Upsert articles. Returns count inserted."""

    def load_today_articles(self, category: str = None) -> list[dict]:
        """Load articles collected today (UTC). Optional category filter."""

    def save_briefing(self, content: str, mode: str, article_count: int) -> str:
        """Insert briefing. Returns briefing_id."""

    def load_briefings(self, limit: int = 7) -> list[dict]:
        """Load last N briefings."""

    def save_market_snapshots(self, snapshots: list[dict]) -> None:
        """Insert market data snapshot."""

    def load_latest_market_snapshot(self) -> list[dict]:
        """Load most recent market snapshot per ticker."""
```

### Tests — `tests/test_database.py`
- `test_insert_and_load_articles` : insert 3 articles, load today → 3 retournés
- `test_upsert_does_not_duplicate` : insert même URL 2x → 1 en base
- `test_save_and_load_briefing` : save + load → contenu identique
- `test_load_latest_market_snapshot` : 2 snapshots même ticker → seul le plus récent
- `test_migration_safe` : init_db() sur DB existante → pas d'erreur

---

## [TODO] FEAT-005 — Pipeline principal + scheduling

Added: 2026-03-23 | Priority: Haute
Playbook: feature_development

### Contexte
Point d'entrée CLI qui orchestre tout le pipeline.

### Étape 1 — `src/main.py`

**Commandes CLI (argparse) :**
```bash
python -m src.main run --mode [no-llm|local|api] [--lookback 24]
python -m src.main collect-only
python -m src.main status
```

**Fonction `run()` :**
```python
def run(mode: str, lookback_hours: int = 24):
    # 1. Collect
    articles = fetch_rss_articles(lookback_hours) + fetch_hn_articles()
    market = fetch_market_snapshot()

    # 2. Process
    articles = dedup_articles(articles)
    articles = [score_article(a) for a in articles]
    articles = filter_articles(articles)

    # 3. Store raw
    db.insert_articles(articles)
    db.save_market_snapshots(market)

    # 4. Synthesize
    briefing = Synthesizer(mode).build_briefing(articles, market)

    # 5. Store briefing
    db.save_briefing(briefing, mode, len(articles))

    print(briefing)
```

**Fonction `status()` :**
```
Last run: 2026-03-23 07:02:14
Articles collected today: 47
Last briefing: 2026-03-23 07:02:58 (mode: api)
DB size: 2.3 MB
```

### Tests — `tests/test_main.py`
- `test_run_no_llm_end_to_end` : mock tous les collecteurs + DB, vérifie pipeline complet
- `test_collect_only_skips_llm` : mode collect-only → Synthesizer jamais appelé
- `test_status_output` : mock DB → status s'affiche sans erreur

---

## [TODO] FEAT-006 — Dashboard Streamlit

Added: 2026-03-23 | Priority: Moyenne
Playbook: feature_development

### Contexte
Interface de lecture du briefing quotidien et suivi des marchés.

### `app/dashboard.py`

**Navigation sidebar :**
```
📰 Briefing du jour
📈 Marchés
📚 Historique
⚙️ Sources & Statut
```

**Page "📰 Briefing du jour" :**
- Timestamp dernière collecte + fraîcheur (badge vert/orange/rouge)
- Contenu markdown du briefing (rendu avec `st.markdown`)
- Si pas de briefing → bouton "Générer maintenant" → appel `src.main.run()`
- Articles bruts par catégorie dans expanders

**Page "📈 Marchés" :**
- Tableau : Ticker | Prix | Variation 1j% (coloré vert/rouge) | Volume
- Groupé par catégorie (Indices, Tech, Crypto, Commodités, FX)
- Sparkline 5 jours via `yfinance` history

**Page "📚 Historique" :**
- Sélecteur date → affiche briefing du jour sélectionné
- Filtre catégorie articles
- Compteur articles par source (bar chart)

**Page "⚙️ Sources & Statut" :**
- Status de chaque collecteur (dernier run, nb articles, OK/KO)
- Bouton "Forcer collecte maintenant"
- Config mode LLM actif

---

## [TODO] FEAT-007 — Intégration Telegram

Added: 2026-03-23 | Priority: Moyenne
Playbook: feature_development

### Contexte
Envoyer le briefing quotidien automatiquement sur Telegram (bot personnel).
Permet de recevoir le résumé sur mobile sans ouvrir le dashboard.

### Étape 1 — Setup bot

**Variables `.env` à ajouter :**
```
TELEGRAM_BOT_TOKEN=        # @BotFather → /newbot
TELEGRAM_CHAT_ID=          # ton chat_id (obtenu via getUpdates)
TELEGRAM_ENABLED=false     # activer explicitement
```

### Étape 2 — `src/notifications/telegram_notifier.py`

```python
class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):

    def send_briefing(self, briefing_markdown: str) -> bool:
        """
        Split briefing in chunks ≤ 4096 chars (Telegram limit).
        Send each chunk as separate message.
        Returns True if all sent, False on any error.
        """

    def send_market_alert(self, ticker: str, change_pct: float, price: float) -> bool:
        """Send alert when |change_pct| > threshold (default 5%)."""

    def _send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """Low-level send via requests.post to Telegram Bot API."""
```

**Requirements :**
- Endpoint : `https://api.telegram.org/bot{token}/sendMessage`
- Markdown → Telegram MarkdownV2 : échapper les caractères spéciaux (`.`, `-`, `(`, `)`, `!`)
- Retry 1x sur timeout (5s)
- Logger erreurs sans raise (notification non critique)

### Étape 3 — Intégration dans `src/main.py`

```python
# Dans run() — après save_briefing()
if os.getenv("TELEGRAM_ENABLED", "false").lower() == "true":
    notifier = TelegramNotifier(...)
    notifier.send_briefing(briefing)
```

### Étape 4 — Alertes marché (optionnel, activable)

```
TELEGRAM_MARKET_ALERTS=false
TELEGRAM_ALERT_THRESHOLD=5.0   # % variation pour déclencher alerte
```

Dans `collect-only` mode : si alertes activées → envoyer pour tickers > threshold.

### Tests — `tests/test_telegram.py`
- `test_send_briefing_chunks_long_message` : message > 4096 chars → 2+ messages envoyés
- `test_send_briefing_disabled` : `TELEGRAM_ENABLED=false` → aucun appel HTTP
- `test_send_message_retries_on_timeout` : timeout 1ère requête → retry → succès
- `test_markdown_escaping` : caractères spéciaux correctement échappés
- `test_market_alert_threshold` : change_pct < threshold → pas d'envoi

---

## [TODO] FEAT-008 — Tests globaux & CI

Added: 2026-03-23 | Priority: Haute

### Acceptance criteria globaux

- [ ] `pytest tests/ -v` passe sans réseau ni clé API
- [ ] `python -m src.main run --mode no-llm` s'exécute sans erreur
- [ ] Dashboard Streamlit démarre : `streamlit run app/dashboard.py`
- [ ] Cron `daily_run.sh` auto-détecte le mode (api > local > no-llm)
- [ ] Telegram : message reçu sur mobile après run (si token configuré)
- [ ] Déduplication : aucun article en double sur 2 runs consécutifs
