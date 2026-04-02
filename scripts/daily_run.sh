#!/usr/bin/env bash
# Daily run entrypoint for cron
# Cron: 0 7 * * * cd /path/to/news_briefing && bash scripts/daily_run.sh

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LOG_DIR="$PROJECT_DIR/data/logs"
LOG_FILE="$LOG_DIR/$(date +%Y-%m-%d).log"

mkdir -p "$LOG_DIR"

echo "[$(date -Iseconds)] Starting daily run" >> "$LOG_FILE"

cd "$PROJECT_DIR"

# Activate venv if present
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
fi

# Determine mode: api > local > no-llm
MODE="no-llm"
if [ -n "${ANTHROPIC_API_KEY:-}" ] || [ -n "${OPENAI_API_KEY:-}" ]; then
    MODE="api"
elif curl -s --max-time 2 "${OLLAMA_HOST:-http://localhost:11434}/api/tags" > /dev/null 2>&1; then
    MODE="local"
fi

echo "[$(date -Iseconds)] Using mode: $MODE" >> "$LOG_FILE"

python -m src.main run --mode "$MODE" >> "$LOG_FILE" 2>&1

echo "[$(date -Iseconds)] Done" >> "$LOG_FILE"
