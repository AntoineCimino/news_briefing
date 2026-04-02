from __future__ import annotations

import argparse
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.collectors.hn_collector import fetch_hn_articles
from src.collectors.market_collector import fetch_market_snapshot
from src.collectors.newsapi_collector import fetch_newsapi_articles
from src.collectors.rss_collector import fetch_rss_articles
from src.llm.synthesizer import Synthesizer
from src.notifications.telegram_notifier import TelegramNotifier
from src.processors.dedup import dedup_articles
from src.processors.ranker import rank_articles
from src.processors.relevance_filter import filter_articles
from src.storage.database import BriefingDatabase


def _get_telegram_notifier() -> TelegramNotifier | None:
    if os.getenv("TELEGRAM_ENABLED", "false").lower() != "true":
        return None
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return None
    return TelegramNotifier(token=token, chat_id=chat_id)


def collect_articles(lookback_hours: int = 24) -> list[dict[str, Any]]:
    rss_articles = fetch_rss_articles(lookback_hours)
    hn_articles = fetch_hn_articles()
    api_articles = fetch_newsapi_articles(existing_articles=rss_articles + hn_articles, lookback_hours=lookback_hours)
    return rss_articles + hn_articles + api_articles


def run(
    mode: str,
    lookback_hours: int = 24,
    db: BriefingDatabase | None = None,
    model: str | None = None,
) -> str:
    database = db or BriefingDatabase()
    articles = collect_articles(lookback_hours)
    market = fetch_market_snapshot()

    ranked_articles = rank_articles(dedup_articles(articles))
    filtered_articles = filter_articles(ranked_articles)

    database.insert_articles(filtered_articles)
    database.save_market_snapshots(market)

    briefing = Synthesizer(mode, model=model).build_briefing(filtered_articles, market)
    database.save_briefing(briefing, mode, len(filtered_articles))

    notifier = _get_telegram_notifier()
    if notifier:
        notifier.send_briefing(briefing)

    print(briefing)
    return briefing


def collect_only(lookback_hours: int = 24, db: BriefingDatabase | None = None) -> int:
    database = db or BriefingDatabase()
    articles = filter_articles(rank_articles(dedup_articles(collect_articles(lookback_hours))))
    market = fetch_market_snapshot()
    database.insert_articles(articles)
    database.save_market_snapshots(market)
    print(f"Collected {len(articles)} articles and {len(market)} market snapshots.")
    return len(articles)


def status(db: BriefingDatabase | None = None) -> str:
    database = db or BriefingDatabase()
    briefings = database.load_briefings(limit=1)
    articles_today = database.load_today_articles()
    latest_market = database.load_latest_market_snapshot()
    db_size_mb = database.db_path.stat().st_size / (1024 * 1024) if database.db_path.exists() else 0.0

    last_briefing_line = "Last briefing: none"
    if briefings:
        last = briefings[0]
        last_briefing_line = f"Last briefing: {last['created_at']} (mode: {last['mode']})"

    output = "\n".join(
        [
            f"Articles collected today: {len(articles_today)}",
            last_briefing_line,
            f"Latest market rows: {len(latest_market)}",
            f"DB size: {db_size_mb:.1f} MB",
        ]
    )
    print(output)
    return output


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="News briefing pipeline")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--mode", choices=["no-llm", "local", "api"], default="no-llm")
    run_parser.add_argument("--lookback", type=int, default=24)
    run_parser.add_argument("--model", type=str, default=None)

    collect_parser = subparsers.add_parser("collect-only")
    collect_parser.add_argument("--lookback", type=int, default=24)

    subparsers.add_parser("status")
    return parser


def main() -> None:
    load_dotenv()
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "run":
        run(mode=args.mode, lookback_hours=args.lookback, model=args.model)
        return
    if args.command == "collect-only":
        collect_only(lookback_hours=args.lookback)
        return
    status()


if __name__ == "__main__":
    main()
