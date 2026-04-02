from __future__ import annotations

import os

DEFAULT_ANTHROPIC_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_OPENAI_MODEL = "gpt-4o-mini"


def call_api(prompt: str, model: str | None = None) -> str:
    """
    Call OpenAI or Anthropic API (whichever key is set).
    Preference: Anthropic > OpenAI.
    """
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if anthropic_key:
        from anthropic import Anthropic

        client = Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model=model or os.getenv("BRIEFING_ANTHROPIC_MODEL") or DEFAULT_ANTHROPIC_MODEL,
            max_tokens=2200,
            temperature=0.2,
            messages=[{"role": "user", "content": prompt}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key:
        from openai import OpenAI

        client = OpenAI(api_key=openai_key)
        response = client.responses.create(
            model=model or os.getenv("BRIEFING_OPENAI_MODEL") or DEFAULT_OPENAI_MODEL,
            input=prompt,
            max_output_tokens=2200,
            temperature=0.2,
        )
        return response.output_text.strip()

    raise RuntimeError("No API key configured")
