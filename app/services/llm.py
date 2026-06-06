"""Thin OpenRouter (OpenAI-compatible) chat client used for rubric gen + Tier 1 scoring."""
import json

import httpx

from app.core.config import settings

_BASE = "https://openrouter.ai/api/v1/chat/completions"


async def chat_json(system: str, user: str, *, temperature: float = 0.2) -> dict:
    """Call the LLM and parse a JSON object from the response.

    Returns {} if no API key is configured (keeps the scaffold runnable offline).
    """
    if not settings.openrouter_api_key:
        return {}

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": settings.openrouter_model,
        "temperature": temperature,
        "response_format": {"type": "json_object"},
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
    }
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(_BASE, headers=headers, json=body)
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        return {}
