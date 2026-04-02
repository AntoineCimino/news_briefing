from __future__ import annotations

from src.llm.ollama_client import OllamaUnavailableError
from src.llm.synthesizer import Synthesizer


ARTICLES = [
    {
        "title": "OpenAI releases a model",
        "summary": "A concise update for developers.",
        "category": "ai_ecosystem",
        "source": "techcrunch",
        "url": "https://example.com/openai",
        "published_at": "2026-04-01T08:00:00+00:00",
        "rank_score": 0.8,
    }
]
MARKET = [{"ticker": "SP500", "label": "S&P 500", "price": 5000.0, "change_pct": 1.2}]


def test_no_llm_returns_target_structure():
    briefing = Synthesizer("no-llm").build_briefing(ARTICLES, MARKET)
    assert "# Briefing Quotidien IA, Tech et Marches" in briefing
    assert "## Section 1 — Global Market Wrap" in briefing
    assert "## Section 2 — AI & Technology Intelligence" in briefing
    assert "### Top Strategic Developments" in briefing


def test_ollama_called_in_local_mode(monkeypatch):
    calls = []

    def fake_call(prompt, model=None):
        calls.append((prompt, model))
        return "local briefing"

    monkeypatch.setattr("src.llm.synthesizer.call_ollama", fake_call)

    briefing = Synthesizer("local", model="qwen3:14b").build_briefing(ARTICLES, MARKET)
    assert briefing == "local briefing"
    assert len(calls) == 1
    assert calls[0][1] == "qwen3:14b"


def test_api_called_in_api_mode(monkeypatch):
    calls = []

    def fake_call(prompt, model=None):
        calls.append((prompt, model))
        return "api briefing"

    monkeypatch.setattr("src.llm.synthesizer.call_api", fake_call)

    briefing = Synthesizer("api", model="gpt-4o-mini").build_briefing(ARTICLES, MARKET)
    assert briefing == "api briefing"
    assert len(calls) == 1
    assert calls[0][1] == "gpt-4o-mini"


def test_fallback_ollama_to_nollm(monkeypatch):
    monkeypatch.setattr(
        "src.llm.synthesizer.call_ollama",
        lambda prompt, model=None: (_ for _ in ()).throw(OllamaUnavailableError("down")),
    )
    briefing = Synthesizer("local").build_briefing(ARTICLES, MARKET)
    assert "# Briefing Quotidien IA, Tech et Marches" in briefing


def test_fallback_api_to_ollama_to_nollm(monkeypatch):
    monkeypatch.setattr(
        "src.llm.synthesizer.call_api",
        lambda prompt, model=None: (_ for _ in ()).throw(RuntimeError("api down")),
    )
    monkeypatch.setattr(
        "src.llm.synthesizer.call_ollama",
        lambda prompt, model=None: (_ for _ in ()).throw(OllamaUnavailableError("ollama down")),
    )
    briefing = Synthesizer("api").build_briefing(ARTICLES, MARKET)
    assert "# Briefing Quotidien IA, Tech et Marches" in briefing
