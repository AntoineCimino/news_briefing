from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import yfinance as yf

TICKERS = {
    "SP500": "^GSPC",
    "NASDAQ": "^IXIC",
    "CAC40": "^FCHI",
    "VIX": "^VIX",
    "NVDA": "NVDA",
    "MSFT": "MSFT",
    "GOOGL": "GOOGL",
    "META": "META",
    "AAPL": "AAPL",
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "GOLD": "GC=F",
    "OIL": "CL=F",
    "EURUSD": "EURUSD=X",
}

LABELS = {
    "SP500": "S&P 500",
    "NASDAQ": "NASDAQ",
    "CAC40": "CAC 40",
    "VIX": "VIX",
    "NVDA": "NVIDIA",
    "MSFT": "Microsoft",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "AAPL": "Apple",
    "BTC": "Bitcoin",
    "ETH": "Ethereum",
    "GOLD": "Gold",
    "OIL": "Oil",
    "EURUSD": "EUR/USD",
}


def _extract_price(info: dict[str, Any]) -> float:
    for key in ("regularMarketPrice", "currentPrice", "previousClose"):
        value = info.get(key)
        if value is not None:
            return float(value)
    return 0.0


def _extract_change_pct(info: dict[str, Any], price: float) -> float:
    if info.get("regularMarketChangePercent") is not None:
        return float(info["regularMarketChangePercent"])

    previous_close = info.get("previousClose")
    if previous_close in (None, 0):
        return 0.0
    return ((price - float(previous_close)) / float(previous_close)) * 100


def fetch_market_snapshot() -> list[dict[str, Any]]:
    """Fetch latest price + 1d change% for all tickers."""
    collected_at = datetime.now(timezone.utc).isoformat()
    snapshot: list[dict[str, Any]] = []

    for label, ticker in TICKERS.items():
        info = yf.Ticker(ticker).info
        price = _extract_price(info)
        snapshot.append(
            {
                "ticker": label,
                "label": LABELS.get(label, label),
                "price": price,
                "change_pct": _extract_change_pct(info, price),
                "volume": float(info.get("regularMarketVolume") or info.get("volume") or 0.0),
                "collected_at": collected_at,
            }
        )

    return snapshot
