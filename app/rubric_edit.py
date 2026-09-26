"""Convert a Rubric to/from plain table rows so it can be edited live in the UI.

Editing is meaningful: keywords drive the keyword-ATS baseline, equivalents and
type/weight drive the Second Look scoring, so a judge can change a requirement and
watch both shortlists respond after re-running.
"""
from __future__ import annotations

import hashlib

from app.schemas import Requirement, Rubric


def _split(csv_text: object) -> list[str]:
    if csv_text is None:
        return []
    return [p.strip() for p in str(csv_text).split(",") if p.strip()]


def rubric_to_rows(rubric: Rubric) -> list[dict]:
    return [
        {
            "id": r.id,
            "requirement": r.text,
            "type": r.type,
            "weight": r.weight,
            "keywords": ", ".join(r.keywords),
            "equivalents": ", ".join(r.equivalents),
        }
        for r in rubric.requirements
    ]


def rows_to_rubric(base: Rubric, rows: list[dict]) -> Rubric:
    """Apply edited rows on top of `base` (keeps evidence_examples, which aren't editable).
    Rows with an empty requirement text are dropped; invalid type/weight fall back safely."""
    base_by_id = {r.id: r for r in base.requirements}
    reqs: list[Requirement] = []
    for row in rows:
        text = str(row.get("requirement", "")).strip()
        rid = str(row.get("id", "")).strip()
        if not text or not rid:
            continue
        rtype = row.get("type") if row.get("type") in ("must", "nice") else "nice"
        try:
            weight = max(1, min(5, int(row.get("weight", 1))))
        except (TypeError, ValueError):
            weight = 1
        prior = base_by_id.get(rid)
        reqs.append(
            Requirement(
                id=rid,
                text=text,
                type=rtype,
                weight=weight,
                keywords=_split(row.get("keywords")),
                equivalents=_split(row.get("equivalents")),
                evidence_examples=list(prior.evidence_examples) if prior else [],
            )
        )
    return Rubric(role_title=base.role_title, requirements=reqs)


def rubric_signature(rubric: Rubric) -> str:
    """Stable short id for a rubric's content (used to reset the editor / detect stale results)."""
    return hashlib.sha256(rubric.model_dump_json().encode()).hexdigest()[:12]
