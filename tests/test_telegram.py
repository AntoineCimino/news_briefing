from __future__ import annotations

from unittest.mock import MagicMock, patch

from src.notifications.telegram_notifier import (
    TelegramNotifier,
    _split_text,
    markdown_to_telegram_html,
)


def make_notifier() -> TelegramNotifier:
    return TelegramNotifier(token="test_token", chat_id="12345")


# --- _split_text ---

def test_split_text_short_message():
    assert _split_text("hello") == ["hello"]


def test_split_text_chunks_long_message():
    text = ("x" * 100 + "\n") * 50  # 5050 chars
    chunks = _split_text(text, max_len=4096)
    assert len(chunks) == 2
    for chunk in chunks:
        assert len(chunk) <= 4096


def test_split_text_no_newline_fallback():
    text = "a" * 5000
    chunks = _split_text(text, max_len=4096)
    assert len(chunks) == 2
    assert len(chunks[0]) == 4096


# --- markdown_to_telegram_html ---

def test_html_h1_becomes_bold():
    result = markdown_to_telegram_html("# Briefing Quotidien")
    assert "<b>Briefing Quotidien</b>" in result
    assert "📰" in result


def test_html_h2_gets_emoji_and_bold():
    result = markdown_to_telegram_html("## IA & Modeles")
    assert "🤖" in result
    assert "<b>" in result


def test_html_bullet_becomes_dot():
    result = markdown_to_telegram_html("- Some article — summary")
    assert "•" in result
    assert "Some article" in result


def test_html_table_row_renders_with_color():
    md = "| S&P 500 | 5200.00 | +1.50% |"
    result = markdown_to_telegram_html(md)
    assert "🟢" in result
    assert "S&amp;P 500" in result  # html-escaped


def test_html_table_negative_row():
    md = "| OIL | 98.00 | -2.37% |"
    result = markdown_to_telegram_html(md)
    assert "🔴" in result


def test_html_table_header_skipped():
    md = "| Actif | Prix | Variation |"
    result = markdown_to_telegram_html(md)
    assert result.strip() == ""


def test_html_table_separator_skipped():
    md = "| --- | ---: | ---: |"
    result = markdown_to_telegram_html(md)
    assert result.strip() == ""


def test_html_escapes_special_chars():
    result = markdown_to_telegram_html("- <script>alert(1)</script>")
    assert "<script>" not in result
    assert "&lt;script&gt;" in result


# --- TelegramNotifier ---

@patch("src.notifications.telegram_notifier.requests.post")
def test_send_briefing_uses_html_parse_mode(mock_post):
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
    notifier = make_notifier()
    notifier.send_briefing("# Briefing\n## Tech\n- item")
    call_kwargs = mock_post.call_args[1]["json"]
    assert call_kwargs.get("parse_mode") == "HTML"


@patch("src.notifications.telegram_notifier.requests.post")
def test_send_briefing_single_chunk(mock_post):
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
    notifier = make_notifier()
    result = notifier.send_briefing("Short briefing")
    assert result is True
    assert mock_post.call_count == 1


@patch("src.notifications.telegram_notifier.requests.post")
def test_send_briefing_chunks_long_message(mock_post):
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=lambda: None)
    notifier = make_notifier()
    long_text = ("- bullet point\n") * 400  # > 4096 chars
    result = notifier.send_briefing(long_text)
    assert result is True
    assert mock_post.call_count >= 2


@patch("src.notifications.telegram_notifier.requests.post")
def test_send_message_retries_on_timeout(mock_post):
    import requests as req_lib
    mock_post.side_effect = [req_lib.Timeout("timeout"), MagicMock(raise_for_status=lambda: None)]
    notifier = make_notifier()
    result = notifier._send_message("test")
    assert result is True
    assert mock_post.call_count == 2


@patch("src.notifications.telegram_notifier.requests.post")
def test_send_message_returns_false_on_persistent_failure(mock_post):
    import requests as req_lib
    mock_post.side_effect = req_lib.ConnectionError("refused")
    notifier = make_notifier()
    result = notifier._send_message("test")
    assert result is False


@patch("src.notifications.telegram_notifier.requests.post")
def test_market_alert_threshold_not_reached(mock_post):
    notifier = make_notifier()
    result = notifier.send_market_alert("NVDA", change_pct=2.0, price=900.0, threshold=5.0)
    assert result is False
    mock_post.assert_not_called()


@patch("src.notifications.telegram_notifier.requests.post")
def test_market_alert_above_threshold(mock_post):
    mock_post.return_value = MagicMock(raise_for_status=lambda: None)
    notifier = make_notifier()
    result = notifier.send_market_alert("NVDA", change_pct=7.5, price=950.0, threshold=5.0)
    assert result is True
    call_kwargs = mock_post.call_args[1]["json"]
    assert call_kwargs.get("parse_mode") == "HTML"
