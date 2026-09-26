"""Shared helper: cached structured Gemini call, and doc-rendering utilities."""
from __future__ import annotations

import time
from collections import deque

from pydantic import BaseModel

from app.cache import get_or_compute
from app.envload import load_dotenv
from app.llm import MODEL_FAST, MODEL_REASONING, call_structured
from baton.schemas import Doc

load_dotenv()

# Free-tier Gemini allows 15 requests/min per model; stay under it with a rolling window.
_RPM = 13
_sent: deque[float] = deque()


def _throttle() -> None:
    now = time.monotonic()
    while _sent and now - _sent[0] > 60:
        _sent.popleft()
    if len(_sent) >= _RPM:
        time.sleep(60 - (now - _sent[0]) + 0.5)
    _sent.append(time.monotonic())


def call(kind: str, schema: type[BaseModel], system: str, user: str, *, fast: bool = False):
    """Cached, schema-validated Gemini call (same input -> zero extra quota)."""
    model = MODEL_FAST if fast else MODEL_REASONING
    return get_or_compute(
        f"baton-{kind}", schema,
        lambda: (_throttle(), call_structured(model=model, system=system, user_content=user,
                                              response_schema=schema, max_retries=8))[1],
        system, user,
    )


def render_docs(docs: list[Doc]) -> str:
    return "\n\n".join(f"=== {d.name} ===\n{d.text}" for d in docs)


def norm(s: str) -> str:
    return " ".join(s.lower().split())


def span_in_docs(span: str, docs: list[Doc]) -> bool:
    s = norm(span).strip(" .\"'")
    return len(s) >= 8 and any(s in norm(d.text) for d in docs)
