"""Successor Q&A grounded in docs + handover; refuses (and logs a gap) without a valid citation."""
from __future__ import annotations

from baton.common import call
from baton.schemas import Gap, QAAnswer, Session

SYSTEM = """\
You answer a successor's question using ONLY the sources given: documents (ids = filenames) and \
handover items (ids = H1, H2, ...). Cite every source id you used in `citations`. If the sources \
do not answer the question, set supported=false, citations=[] and answer='Not captured'. Never \
guess or use outside knowledge."""

NOT_CAPTURED = "Not captured in the handover. Logged as a gap for the expert to answer before they leave."


def _sources(s: Session) -> tuple[str, set[str]]:
    parts = [f"[{d.name}]\n{d.text}" for d in s.docs]
    parts += [f"[H{i}] ({h.field}) {h.text}" for i, h in enumerate(s.handover, 1)]
    ids = {d.name for d in s.docs} | {f"H{i}" for i in range(1, len(s.handover) + 1)}
    return "\n\n".join(parts), ids


def ask(s: Session, question: str) -> QAAnswer:
    text, valid = _sources(s)
    a = call("qa", QAAnswer, SYSTEM, f"SOURCES:\n{text}\n\nQUESTION: {question}", fast=True)
    cites = [c for c in a.citations if c in valid]
    if not a.supported or not cites:
        if not any(g.evidence == f"Successor asked: {question}" for g in s.gaps):
            s.gaps.append(Gap(id=f"G{len(s.gaps) + 1}", item_id="-", field="successor_question",
                              evidence=f"Successor asked: {question}", priority=5.0))
        return QAAnswer(answer=NOT_CAPTURED, citations=[], supported=False)
    return QAAnswer(answer=a.answer, citations=cites, supported=True)
