"""Gap-driven adaptive interview loop. State lives in a Session (JSON-serialisable)."""
from __future__ import annotations

from baton.confidence import score
from baton.common import call, render_docs, span_in_docs
from baton.mapper import build_map, coverage, detect_gaps
from baton.schemas import Doc, Gap, HandoverItem, Question, Session, Turn, Verdict

MAX_QUESTIONS = 25
REFINE_EXTRA_TURNS = 10
REFINE_REOPEN = 8
MAX_FOLLOWUPS = 2

Q_SYSTEM = """\
You are Baton, interviewing a departing employee so their successor can take over. Ask exactly ONE \
short, specific question about the gap given. The question must quote (in `quoted_span`) exact \
words copied from the documents or gap evidence, and use them inside the question. Ask about the \
missing field: how = the concrete steps/threshold; why = the reason; who = the person and how to \
reach them; contradiction/vague = which is right / what exactly. If earlier answers on this gap \
are shown, this is a follow-up: ask for the missing specific (a threshold, an example, a name), \
and do not repeat the earlier question. If the expert earlier said they do not remember, rephrase: ask \
for the last time it happened, an example, or who else would know."""

J_SYSTEM = """\
You judge an expert's answer to a handover interview question.
- closes_gap: the answer gives a concrete, usable detail for the asked field (a threshold, name, \
reason, or steps). captured_text = that detail in one or two sentences, faithful to the answer; \
never add anything the expert did not say.
- vague: an answer that dodges or stays generic ("it depends", "just use judgement").
- skip: the expert says they do not know or it is not their area.
new_gap: if the answer mentions a system, person or step not explained anywhere, name it, else ''."""


def _gap(s: Session, gid: str | None) -> Gap | None:
    return next((g for g in s.gaps if g.id == gid), None)


def _item(s: Session, item_id: str):
    return next((i for i in s.kmap.items if i.id == item_id), None)


def start_session(docs: list[Doc], last_day: str = "", target: float = 0.8) -> Session:
    kmap = build_map(docs)
    gaps = detect_gaps(kmap, docs, last_day)
    s = Session(docs=docs, kmap=kmap, gaps=gaps, baseline_coverage=coverage(kmap), target=target, max_turns=MAX_QUESTIONS)
    ask_next(s)
    return s


def _make_question(s: Session, gap: Gap) -> str:
    item = _item(s, gap.item_id)
    prior = [t for t in s.turns if t.gap_id == gap.id]
    user = (f"GAP: field={gap.field} item='{item.title if item else gap.item_id}' "
            f"evidence: {gap.evidence}\n"
            + "".join(f"EARLIER Q: {t.question}\nEARLIER A: {t.answer}\n" for t in prior)
            + f"\nDOCUMENTS:\n{render_docs(s.docs)}")
    for attempt in range(3):
        # attempt in the key busts the cache when a prior try failed the quote check
        q = call("question", Question, Q_SYSTEM, user + ("" if attempt == 0 else f"\n(retry {attempt})"), fast=True)
        if span_in_docs(q.quoted_span, s.docs) or span_in_docs(q.quoted_span, [Doc(name="g", text=gap.evidence)]):
            return q.question
    return f"Your documents say: \"{gap.evidence}\" -- can you explain the {gap.field}?"


def ask_next(s: Session) -> None:
    open_gaps = [g for g in s.gaps if g.status == "open"]
    if not open_gaps or len(s.turns) >= s.max_turns:
        s.current_gap = s.current_question = None
        return
    gap = max(open_gaps, key=lambda g: g.priority)
    s.current_gap, s.followups = gap.id, 0
    s.current_question = _make_question(s, gap)
    s.turns.append(Turn(n=len(s.turns) + 1, gap_id=gap.id, question=s.current_question))


def submit_answer(s: Session, answer: str) -> Verdict:
    """Record the expert's answer to the pending question; then follow up or move on."""
    turn = s.turns[-1]
    gap = _gap(s, s.current_gap)
    turn.answer = answer
    user = (f"FIELD ASKED: {gap.field}\nQUESTION: {turn.question}\nANSWER: {answer}\n\n"
            f"DOCUMENTS (to decide what is already explained):\n{render_docs(s.docs)}")
    v = call("judge", Verdict, J_SYSTEM, user, fast=True)
    if v.verdict == "vague" and s.followups >= MAX_FOLLOWUPS:
        v = Verdict(verdict="skip", captured_text="", new_gap=v.new_gap)
    turn.verdict = v.verdict

    if v.new_gap and len(s.gaps) < 40 and not any(v.new_gap.lower() in g.evidence.lower() for g in s.gaps):
        s.gaps.append(Gap(id=f"G{len(s.gaps) + 1}", item_id=gap.item_id, field="how",
                          evidence=f"Expert mentioned: {v.new_gap}", priority=gap.priority * 0.9))

    if v.verdict == "closes_gap" and v.captured_text:
        gap.status = "closed"
        s.handover.append(HandoverItem(gap_id=gap.id, item_id=gap.item_id, field=gap.field,
                                       text=v.captured_text, source=f"interview turn {turn.n}"))
        it = _item(s, gap.item_id)
        if it and gap.field in ("how", "why", "who"):
            setattr(it, gap.field, True)
        ask_next(s)
    elif v.verdict == "vague":
        s.followups += 1
        s.current_question = _make_question(s, gap)
        s.turns.append(Turn(n=len(s.turns) + 1, gap_id=gap.id, question=s.current_question))
    else:  # skip: stays a risk for the manager, move on
        gap.status = "skipped"
        ask_next(s)
    maybe_refine(s)
    if not s.current_question and s.round == 2 and len(s.confidence_log) < 2:
        s.confidence_log.append(score(s)["confidence"])
    return v


def maybe_refine(s: Session) -> bool:
    """When the round ends below the target confidence, run ONE refinement round: reopen the
    highest-priority skipped gaps and allow a few more questions. Never more than one."""
    if s.current_question:
        return False
    conf = score(s)["confidence"]
    if s.round == 1:
        s.confidence_log = [conf]
    if s.round != 1 or conf >= s.target:
        return False
    s.round, s.max_turns = 2, len(s.turns) + REFINE_EXTRA_TURNS
    for g in sorted((g for g in s.gaps if g.status == "skipped"), key=lambda g: -g.priority)[:REFINE_REOPEN]:
        g.status = "open"
    ask_next(s)
    return s.current_question is not None


def open_risks(s: Session) -> list[str]:
    out = []
    for g in sorted((g for g in s.gaps if g.status in ("open", "skipped")), key=lambda g: -g.priority):
        it = _item(s, g.item_id)
        out.append(f"[{g.status}] {it.title if it else g.item_id} - {g.field}: {g.evidence[:100]}")
    return out
