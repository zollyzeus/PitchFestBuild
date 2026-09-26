"""A deterministic stand-in for a blunt, keyword-matching ATS. Pure Python,
no model call: this is exactly the kind of filter Second Look is auditing."""
from __future__ import annotations

from app.schemas import BaselineResult, Candidate, Rubric


def run_baseline(candidate: Candidate, rubric: Rubric) -> BaselineResult:
    text = candidate.text.lower()
    fired: list[str] = []
    for req in rubric.requirements:
        if req.type != "must":
            continue
        kws = req.keywords or [req.text]
        if not any(kw.lower() in text for kw in kws if kw.strip()):
            fired.append(f"{req.id} ({req.text}): none of {kws} found in CV text")
    return BaselineResult(candidate_id=candidate.id, passed=not fired, fired_rules=fired)
