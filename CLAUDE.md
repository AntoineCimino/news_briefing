# CLAUDE.md — news_briefing

Agent instructions for the news_briefing project.

---

## Project purpose

Daily automated intelligence briefing on AI, technology, and global financial markets.
Fetches → deduplicates → ranks → synthesizes (optional LLM) → stores → displays.

---

## Architecture

```
src/
  collectors/    # Fetch raw data: RSS feeds, HN API, market APIs
  processors/    # Dedup, rank, filter by relevance
  llm/           # Synthesis wrappers (Ollama / OpenAI / Anthropic / no-llm)
  storage/       # SQLite persistence (articles, briefings)
app/
  dashboard.py   # Streamlit front-end
scripts/
  daily_run.sh   # Cron entrypoint (runs src/main.py run)
```

---

## Running modes

| Mode | Env var | Description |
|------|---------|-------------|
| no-llm | — | Raw structured data only |
| local | OLLAMA_HOST | Synthesis via Ollama |
| api | OPENAI_API_KEY or ANTHROPIC_API_KEY | Synthesis via API |

---

## Commands

```bash
cd ~/dev/data/news_briefing
pip install -r requirements.txt
cp .env.example .env

# One-shot run
python -m src.main run --mode no-llm

# Streamlit dashboard
streamlit run app/dashboard.py

# Tests
pytest tests/ -v
```

---

## Scheduling

Daily run via systemd `--user` timer `news-briefing-daily.timer` (07:00) — see `systemd/`. Logs: `data/logs/systemd_daily.log` + `data/logs/<date>.log` (written by `daily_run.sh` itself).

---

## Development rules

- All code in `src/` — no logic in `app/` beyond rendering
- Each collector is a standalone module returning a list of `Article` dicts
- Processors are pure functions (no side effects)
- LLM wrappers must handle failures gracefully (fallback to no-llm)
- No new dependencies without updating `requirements.txt`
- Tests go in `tests/` — mock external HTTP calls

---

## Playbooks

| Situation | Action |
|-----------|--------|
| Add new RSS source | Edit `src/collectors/rss_collector.py`, add to `FEEDS` list |
| Add new market ticker | Edit `src/collectors/market_collector.py`, add to `TICKERS` dict |
| LLM prompt tuning | Edit `src/llm/synthesizer.py` |
| DB schema change | Use safe `ALTER TABLE` pattern in `src/storage/database.py` |

---

## Backlog

`tasks/backlog.md`
