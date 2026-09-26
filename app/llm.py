"""Gemini API wrapper: structured, schema-validated calls with retry.

Model choice (checked live against this project's key on 2026-09-26):
- gemini-pro-latest returned 429 RESOURCE_EXHAUSTED (quota) -> avoided.
- gemini-flash-latest and gemini-flash-lite-latest both work; flash-lite is the
  cheaper/faster of the two and is used for the many per-candidate calls.
"""
from __future__ import annotations

import os
import time

from google import genai
from google.genai import types
from pydantic import BaseModel

# gemini-pro-latest returned 429 quota-exhausted and gemini-flash-latest kept 503ing on
# large calls when checked live against this key; gemini-flash-lite-latest was the only
# model that came back clean every time, so it's the default for everything.
MODEL_REASONING = os.environ.get("GEMINI_MODEL_REASONING", "gemini-flash-lite-latest")
MODEL_FAST = os.environ.get("GEMINI_MODEL_FAST", "gemini-flash-lite-latest")

_client: genai.Client | None = None


def get_client() -> genai.Client:
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "Set GEMINI_API_KEY (export it, or put it in a .env file at the repo root) "
                "before running."
            )
        _client = genai.Client(api_key=key)
    return _client


def call_structured(
    *,
    model: str,
    system: str,
    user_content: str,
    response_schema: type[BaseModel],
    max_retries: int = 6,
) -> BaseModel:
    """One Gemini call, JSON-mode + a Pydantic response_schema, with backoff on
    transient errors (503 overload, 429 rate limit). Raises on the final failure."""
    client = get_client()
    last_err: Exception | None = None
    for attempt in range(max_retries):
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                ),
            )
            if resp.parsed is not None:
                return resp.parsed
            # Fallback: some SDK/model combinations don't populate .parsed even
            # though .text is valid JSON matching the schema.
            return response_schema.model_validate_json(resp.text)
        except Exception as e:  # noqa: BLE001 - we want to retry broadly, then surface
            last_err = e
            msg = str(e)
            transient = ("503" in msg) or ("UNAVAILABLE" in msg) or ("429" in msg)
            if not transient or attempt == max_retries - 1:
                raise
            time.sleep(1.5 * (attempt + 1))
    raise last_err  # pragma: no cover - unreachable, satisfies type checkers
