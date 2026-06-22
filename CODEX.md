# CODEX.md — news_briefing

Repository-specific guidance for Codex work in `news_briefing/`.

## Project Purpose

Daily automated intelligence briefing on AI, technology, and global financial markets.

Pipeline shape:

- fetch
- deduplicate
- rank
- synthesize optionally with an LLM
- store
- display

## Architecture

```text
src/
  collectors/    raw inputs: RSS, HN, market APIs
  processors/    dedup, ranking, relevance filtering
  llm/           synthesis wrappers
  storage/       SQLite persistence
app/
  webapp.py      application entrypoint and rendering
scripts/
  daily_run.sh   scheduled entrypoint
```

## Working Rules

- Keep business logic in `src/`, not in `app/`.
- Collectors should remain standalone modules returning article-like records.
- Processors should stay close to pure functions.
- LLM wrappers must fail gracefully and preserve a no-LLM fallback path.
- Do not add dependencies without updating `requirements.txt`.
- Put tests in `tests/` and mock external HTTP calls.

## Commands

```bash
cd /home/antoine/dev/news_briefing
pip install -r requirements.txt
cp .env.example .env
python -m src.main run --mode no-llm
uvicorn app.webapp:app --reload
pytest tests/ -v
```

## Task Routing

- add or change RSS sources -> `src/collectors/rss_collector.py`
- add or change market tickers -> `src/collectors/market_collector.py`
- prompt or synthesis tuning -> `src/llm/synthesizer.py`
- DB schema changes -> `src/storage/database.py`

## Backlog

Use `tasks/backlog.md`.
