# News Briefing — Daily AI & Markets Intelligence

Automated daily intelligence briefing on AI, technology, and global financial markets.

## Overview

Fetches, processes, and synthesizes the most important developments from the last 24 hours across:
- AI ecosystem (models, funding, research, regulation)
- Global technology companies
- Financial markets (indices, commodities, crypto, FX)
- Macroeconomic signals

## Architecture

```
news_briefing/
├── src/
│   ├── collectors/      # News & market data fetchers (RSS, APIs, HN)
│   ├── processors/      # Dedup, ranking, relevance filtering
│   ├── llm/             # LLM integration (Ollama local / OpenAI / no-LLM)
│   └── storage/         # SQLite briefing history
├── app/
│   └── dashboard.py     # Streamlit front-end
├── scripts/
│   └── daily_run.sh     # Cron entrypoint
└── data/
    ├── raw/             # Raw fetched articles
    └── processed/       # Briefings database
```

## Modes

| Mode | Description | Requirement |
|------|-------------|-------------|
| **no-llm** | Raw structured data only, no synthesis | None |
| **local** | Synthesis via Ollama with configurable model selection | Ollama running locally |
| **api** | Synthesis via OpenAI / Anthropic API | API key in .env |

## Quick Start

```bash
cd news_briefing
pip install -r requirements.txt
cp .env.example .env   # fill in optional API keys

# Run once (no-LLM mode)
python3 -m src.main run --mode no-llm

# Run with local LLM (auto-select best installed Ollama model)
python3 -m src.main run --mode local

# Force a specific local model
python3 -m src.main run --mode local --model qwen3:14b

# Force a specific API model
python3 -m src.main run --mode api --model gpt-4o-mini

# Launch dashboard
streamlit run app/dashboard.py
```

## Model Configuration

- CLI override: `--model`
- Ollama env override: `OLLAMA_MODEL` or `BRIEFING_OLLAMA_MODEL`
- API env override: `BRIEFING_OPENAI_MODEL` or `BRIEFING_ANTHROPIC_MODEL`
- Local auto-detection checks installed Ollama manifests and prefers stronger local models when available, including `qwen3:14b` and `mistral-nemo:12b`
- Override the manifest root via `OLLAMA_MODELS_PATH` (default: `/usr/share/ollama/.ollama/models`)

## Cron Setup

```bash
# Daily at 07:00
0 7 * * * cd /path/to/news_briefing && bash scripts/daily_run.sh
```

## Data Sources

### Free / No Key Required
- Hacker News API (top stories)
- RSS: Reuters, TechCrunch, VentureBeat, ArsTechnica, The Verge
- RSS: arXiv cs.AI, cs.LG (AI papers)
- Yahoo Finance (market data via yfinance)

### Optional (API Key)
- NewsAPI.org (100 req/day free)
- Alpha Vantage (market data)
- Finnhub (earnings, news)
