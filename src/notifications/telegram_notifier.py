from __future__ import annotations

import html as html_lib
import logging
import re
import time
from typing import Any

import requests

LOGGER = logging.getLogger(__name__)
TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"
MAX_MESSAGE_LEN = 4096

_SECTION_EMOJIS: list[tuple[str, str]] = [
    ("ia", "🤖"),
    ("tech", "💻"),
    ("march", "📈"),
    ("macro", "🌍"),
    ("donn", "📊"),
]


def _section_emoji(title: str) -> str:
    lower = title.lower()
    for key, emoji in _SECTION_EMOJIS:
        if key in lower:
            return emoji
    return "•"


def _parse_table_row(line: str) -> list[str]:
    return [c.strip() for c in line.strip().strip("|").split("|") if c.strip()]


def markdown_to_telegram_html(text: str) -> str:
    """Convert the no-llm briefing markdown to clean Telegram HTML."""
    lines = text.split("\n")
    out: list[str] = []
    for line in lines:
        if line.startswith("# "):
            out.append(f"📰 <b>{html_lib.escape(line[2:].strip())}</b>\n")
        elif line.startswith("## "):
            section = line[3:].strip()
            emoji = _section_emoji(section)
            out.append(f"\n{emoji} <b>{html_lib.escape(section)}</b>")
        elif line.startswith("- "):
            out.append(f"  • {html_lib.escape(line[2:].strip())}")
        elif line.startswith("| "):
            cols = _parse_table_row(line)
            # Skip header and separator rows
            if not cols or all(c.replace("-", "").replace(":", "").strip() == "" for c in cols):
                continue
            if cols[0] in ("Actif",):
                continue
            if len(cols) >= 3:
                actif, prix, var = cols[0], cols[1], cols[2]
                if var.startswith("+"):
                    sign = "🟢"
                elif var.startswith("-"):
                    sign = "🔴"
                else:
                    sign = "⚪"
                out.append(f"  {sign} <b>{html_lib.escape(actif)}</b>  {html_lib.escape(prix)}  <i>{html_lib.escape(var)}</i>")
        elif line.strip():
            out.append(html_lib.escape(line))
        else:
            out.append("")
    return "\n".join(out).strip()


def _split_text(text: str, max_len: int = MAX_MESSAGE_LEN) -> list[str]:
    """Split text into chunks respecting Telegram's message size limit."""
    if len(text) <= max_len:
        return [text]
    chunks: list[str] = []
    while text:
        if len(text) <= max_len:
            chunks.append(text)
            break
        split_at = text.rfind("\n", 0, max_len)
        if split_at == -1:
            split_at = max_len
        chunks.append(text[:split_at])
        text = text[split_at:].lstrip("\n")
    return chunks


class TelegramNotifier:
    def __init__(self, token: str, chat_id: str):
        self._token = token
        self._chat_id = chat_id
        self._url = TELEGRAM_API.format(token=token)

    def _send_message(self, text: str, parse_mode: str | None = None) -> bool:
        payload: dict[str, Any] = {"chat_id": self._chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        for attempt in range(2):
            try:
                response = requests.post(self._url, json=payload, timeout=5)
                response.raise_for_status()
                return True
            except requests.RequestException as exc:
                if attempt == 0:
                    LOGGER.warning("Telegram send failed (attempt 1), retrying: %s", exc)
                    time.sleep(1)
                else:
                    LOGGER.error("Telegram send failed: %s", exc)
        return False

    def send_briefing(self, briefing_markdown: str) -> bool:
        html = markdown_to_telegram_html(briefing_markdown)
        chunks = _split_text(html)
        all_sent = True
        for chunk in chunks:
            if not self._send_message(chunk, parse_mode="HTML"):
                all_sent = False
        return all_sent

    def send_market_alert(
        self, ticker: str, change_pct: float, price: float, threshold: float = 5.0
    ) -> bool:
        if abs(change_pct) < threshold:
            return False
        direction = "📈" if change_pct > 0 else "📉"
        text = f"{direction} <b>{html_lib.escape(ticker)}</b> {change_pct:+.2f}% — {price:.2f}"
        return self._send_message(text, parse_mode="HTML")
