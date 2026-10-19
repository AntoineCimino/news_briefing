# News Briefing

Briefing quotidien automatisé avec synthèse LLM et dashboard Streamlit.

## Vue d'ensemble
- [[README]] — sources, modes (no-llm / local / api), dashboard
- [[tasks/backlog]] — tâches actives

## Modes de synthèse
- `--mode no-llm` : agrégation pure sans LLM
- `--mode local` : synthèse via Ollama
- `--mode api` : synthèse via OpenAI/Anthropic

## Status
Production — pipeline quotidien + dashboard

## Stack
Python · Streamlit · Ollama · OpenAI API · RSS/scraping
Cron : `bash scripts/daily_run.sh`
