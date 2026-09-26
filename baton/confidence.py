"""Deterministic handover confidence (no model self-rating).

confidence = 0.7 * resolution + 0.3 * faithfulness
- resolution: priority-weighted share of interview gaps closed with a concrete answer
- faithfulness: share of captured handover lines whose key words appear in the expert's own answer
"""
from __future__ import annotations

import re

from baton.schemas import Session

W_RESOLUTION, W_FAITHFUL = 0.7, 0.3


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if len(w) > 3}


def _faithful(s: Session, source: str, captured: str) -> bool:
    m = re.search(r"(\d+)$", source)
    turn = next((t for t in s.turns if m and t.n == int(m.group(1))), None)
    if not turn:
        return False
    cw = _words(captured)
    return bool(cw) and len(cw & _words(turn.answer)) / len(cw) >= 0.6


def score(s: Session) -> dict:
    gaps = [g for g in s.gaps if g.field != "successor_question"]
    total = sum(g.priority for g in gaps)
    resolution = sum(g.priority for g in gaps if g.status == "closed") / total if total else 0.0
    ok = [_faithful(s, h.source, h.text) for h in s.handover]
    faith = sum(ok) / len(ok) if ok else 0.0
    return {
        "resolution": resolution,
        "faithfulness": faith,
        "confidence": W_RESOLUTION * resolution + W_FAITHFUL * faith,
    }
