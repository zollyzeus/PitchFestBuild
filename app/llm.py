"""Gemini API wrapper: structured, schema-validated calls with retry.

Model choice (checked live against this project's key on 2026-09-26):
- gemini-pro-latest returned 429 RESOURCE_EXHAUSTED (quota) -> avoided.
- gemini-flash-latest and gemini-flash-lite-latest both work; flash-lite is the
  cheaper/faster of the two and is used for the many per-candidate calls.
"""
from __future__ import annotations

import collections
import os
import re
import threading
import time

from google import genai
from google.genai import types
from pydantic import BaseModel

# gemini-pro-latest returned 429 quota-exhausted and gemini-flash-latest kept 503ing on
# large calls when checked live against this key; gemini-flash-lite-latest was the only
# model that came back clean every time, so it's the default for everything.
DEFAULT_MODEL = "gemini-flash-lite-latest"
MODEL_REASONING = os.environ.get("GEMINI_MODEL_REASONING", DEFAULT_MODEL)
MODEL_FAST = os.environ.get("GEMINI_MODEL_FAST", DEFAULT_MODEL)

class DailyQuotaExceeded(RuntimeError):
    """The free-tier DAILY request cap for a model is used up. Retrying is pointless (the
    server's 'retry in Ns' hint only covers the per-minute limit), so we fail immediately."""


_client: genai.Client | None = None

# The API key is on Gemini's free tier: 15 requests/minute per model. A fresh (uncached)
# screening is 1 rubric call + 1 call per candidate, so we throttle ourselves below that
# limit instead of hammering the API and burning quota on retries.
MAX_RPM = int(os.environ.get("GEMINI_MAX_RPM", "12"))
_call_times: collections.deque[float] = collections.deque()
_throttle_lock = threading.Lock()


def _throttle() -> None:
    """Block until making one more call keeps us within MAX_RPM over a sliding minute."""
    while True:
        with _throttle_lock:
            now = time.monotonic()
            while _call_times and now - _call_times[0] > 60:
                _call_times.popleft()
            if len(_call_times) < MAX_RPM:
                _call_times.append(now)
                return
            wait = 60 - (now - _call_times[0]) + 0.2
        time.sleep(max(wait, 0.2))


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
    deterministic: bool = False,
) -> BaseModel:
    """One Gemini call, JSON-mode + a Pydantic response_schema, with backoff on
    transient errors (503 overload, 429 rate limit). Raises on the final failure."""
    client = get_client()
    last_err: Exception | None = None
    # Scoring/extraction must be reproducible for an audit trail: same input, same
    # verdicts. Dataset generation wants variety, so it leaves this off.
    extra = {"temperature": 0.0, "seed": 0} if deterministic else {}
    for attempt in range(max_retries):
        _throttle()
        try:
            resp = client.models.generate_content(
                model=model,
                contents=user_content,
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_schema=response_schema,
                    **extra,
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
            rate_limited = "429" in msg or "RESOURCE_EXHAUSTED" in msg
            if rate_limited and "PerDay" in msg:
                raise DailyQuotaExceeded(
                    f"Gemini free-tier DAILY quota is used up for model '{model}' (resets at midnight "
                    "Pacific time). Cached results still work; new API calls will fail until the reset, "
                    "or until billing is enabled / a new API key is used."
                ) from e
            transient = rate_limited or ("503" in msg) or ("UNAVAILABLE" in msg)
            if not transient or attempt == max_retries - 1:
                raise
            if rate_limited:
                # Honor the server's own hint ("Please retry in 16.3s"), don't guess.
                m = re.search(r"retry in ([\d.]+)s", msg)
                time.sleep((float(m.group(1)) if m else 20.0) + 1.0)
            else:
                time.sleep(1.5 * (attempt + 1))
    raise last_err  # pragma: no cover - unreachable, satisfies type checkers
