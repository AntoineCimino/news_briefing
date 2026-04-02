from __future__ import annotations

import json
import os
from pathlib import Path

import requests

DEFAULT_OLLAMA_MODEL = "qwen3:14b"
FALLBACK_OLLAMA_MODEL = "llama3.2:3b"
PREFERRED_MODELS = (
    "qwen3:14b",
    "mistral-nemo:12b",
    "glm-4.7-flash",
    "qwen3:8b",
    "deepseek-r1:8b",
    "qwen3:4b",
    "llama3.2:3b",
)


class OllamaUnavailableError(RuntimeError):
    """Raised when the local Ollama instance cannot be reached."""


def _normalize_model_name(model_name: str, tag: str) -> str:
    return model_name if tag == "latest" else f"{model_name}:{tag}"


def list_installed_ollama_models(models_root: str | None = None) -> list[str]:
    manifest_root = Path(
        models_root
        or os.getenv("OLLAMA_MODELS_PATH")
        or "/usr/share/ollama/.ollama/models"
    )
    if manifest_root.name != "manifests":
        manifest_root = manifest_root / "manifests"
    library_dir = manifest_root / "registry.ollama.ai" / "library"
    if not library_dir.exists():
        return []

    installed_models: list[str] = []
    for model_dir in sorted(path for path in library_dir.iterdir() if path.is_dir()):
        for tag_path in sorted(path for path in model_dir.iterdir() if path.is_file()):
            installed_models.append(_normalize_model_name(model_dir.name, tag_path.name))
    return installed_models


def resolve_ollama_model(model: str | None = None) -> str:
    if model:
        return model

    env_model = os.getenv("OLLAMA_MODEL") or os.getenv("BRIEFING_OLLAMA_MODEL")
    if env_model:
        return env_model

    installed = set(list_installed_ollama_models())
    for candidate in PREFERRED_MODELS:
        if candidate in installed:
            return candidate
    if DEFAULT_OLLAMA_MODEL in installed:
        return DEFAULT_OLLAMA_MODEL
    return FALLBACK_OLLAMA_MODEL


def call_ollama(prompt: str, model: str | None = None, timeout: int = 120) -> str:
    """Call local Ollama API and accumulate streamed response chunks."""
    host = os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
    selected_model = resolve_ollama_model(model)
    try:
        response = requests.post(
            f"{host}/api/generate",
            json={
                "model": selected_model,
                "prompt": prompt,
                "stream": True,
                "options": {"temperature": 0.2},
            },
            timeout=timeout,
            stream=True,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise OllamaUnavailableError(str(exc)) from exc

    chunks: list[str] = []
    try:
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            payload = json.loads(line)
            chunks.append(payload.get("response", ""))
            if payload.get("done"):
                break
    except (json.JSONDecodeError, requests.RequestException) as exc:
        raise OllamaUnavailableError(str(exc)) from exc

    return "".join(chunks).strip()
