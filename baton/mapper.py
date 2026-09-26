"""Knowledge map extraction + gap detection (rules from what/how/why/who flags, plus one LLM pass)."""
from __future__ import annotations

from baton.common import call, render_docs, span_in_docs
from baton.schemas import Doc, ExtraGaps, Gap, KnowledgeMap

CRIT_W = {"high": 3, "medium": 2, "low": 1}

MAP_SYSTEM = """\
You read a departing employee's working documents and build a knowledge map of what their role \
involves: duties, recurring tasks (with cadence), systems, people, vendors, decisions. 8-16 items. \
Ids are M1, M2, ... `sources` are document filenames.

For each item set the four flags strictly from what the DOCUMENTS explicitly state:
- what: the documents say what it is / what is done
- how: the documents give concrete steps, thresholds or procedure
- why: the documents explain the reason
- who: the documents name an owner or contact
Vague phrases ("if needed", "usual fix", "ask Dana") do NOT count as how/why. Be strict: most \
items should have at least one false flag. criticality reflects business risk if it goes wrong."""

GAP_SYSTEM = """\
You review a knowledge map against the source documents and find the undocumented knowledge a \
successor could not act on. Look for: shorthand or vague phrases with no threshold, name, \
location or steps ("if needed", "the usual fix", "ask Dana", "the local folder", "the token", \
"tolerance"); unexplained exceptions ("skip step 7 in March"); contradictions between two \
documents; commitments dated after the last working day. Return up to 14 gaps, one per distinct \
phrase, most operationally risky first. `item_id` must be an id from the map. `evidence` must be \
an EXACT quote copied from a document. Use field 'vague' for unexplained phrases."""


def build_map(docs: list[Doc]) -> KnowledgeMap:
    return call("map", KnowledgeMap, MAP_SYSTEM, render_docs(docs))


def _evidence_for(item, docs: list[Doc]) -> str:
    for d in docs:
        if d.name in item.sources:
            for line in d.text.splitlines():
                if item.title.split()[0].lower() in line.lower() and len(line.strip()) > 10:
                    return line.strip()
    return f"Documents mention '{item.title}' without explaining it."


def detect_gaps(kmap: KnowledgeMap, docs: list[Doc], last_day: str = "") -> list[Gap]:
    gaps: list[Gap] = []
    for it in kmap.items:
        # who-gap is half as urgent when someone is already named
        # generic why/how gaps on a system or vendor are noise; only ask where knowledge lives
        allowed = ("how", "why", "who") if it.kind in ("duty", "recurring_task", "decision") else ()
        for field in allowed:
            if not getattr(it, field):
                pri = CRIT_W[it.criticality] * (2 if it.cadence else 1) * 0.5
                gaps.append(Gap(id="", item_id=it.id, field=field,
                                evidence=_evidence_for(it, docs), priority=float(pri)))
    known = {it.id: it for it in kmap.items}
    user = f"Last working day: {last_day}\n\nMAP:\n{kmap.model_dump_json()}\n\nDOCUMENTS:\n{render_docs(docs)}"
    for g in call("gaps", ExtraGaps, GAP_SYSTEM, user).gaps:
        it = known.get(g.item_id)
        if it and span_in_docs(g.evidence, docs) and not any(g.evidence == x.evidence for x in gaps):
            gaps.append(Gap(id="", item_id=g.item_id, field=g.field, evidence=g.evidence,
                            priority=float(CRIT_W[it.criticality] * 4)))
    gaps.sort(key=lambda g: -g.priority)
    for i, g in enumerate(gaps, 1):
        g.id = f"G{i}"
    return gaps


def coverage(kmap: KnowledgeMap) -> float:
    """Criticality-weighted share of what/how/why/who flags that are answered."""
    num = den = 0.0
    for it in kmap.items:
        w = CRIT_W[it.criticality]
        num += w * sum(getattr(it, f) for f in ("what", "how", "why", "who"))
        den += w * 4
    return num / den if den else 0.0
