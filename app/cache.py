"""Tiny disk cache so re-running the app (or the demo, twice) doesn't re-spend
Gemini quota or wait on latency for calls it already made."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from pydantic import BaseModel

CACHE_DIR = Path(os.environ.get("RELOOK_CACHE_DIR", "data/cache"))

# Bump this if a prompt changes shape, to invalidate stale cached results.
PROMPT_VERSION = "v2-deterministic"  # v1 results were sampled at default temperature


def _key(*parts: str) -> str:
    h = hashlib.sha256()
    h.update(PROMPT_VERSION.encode())
    for p in parts:
        h.update(b"\x00")
        h.update(p.encode())
    return h.hexdigest()[:24]


def get_or_compute(kind: str, model_cls: type[BaseModel], compute, *key_parts: str):
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / f"{kind}-{_key(*key_parts)}.json"
    if path.exists():
        try:
            return model_cls.model_validate_json(path.read_text())
        except Exception:
            pass  # corrupt/stale cache entry, recompute
    result = compute()
    path.write_text(result.model_dump_json())
    return result
