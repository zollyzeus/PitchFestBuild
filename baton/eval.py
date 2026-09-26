"""Unattended evaluation: scripted expert answers the interview, then we score
gap recall, questions per fact captured, and Q&A faithfulness.

    .venv/bin/python -m baton.eval
"""
from __future__ import annotations

import json

from baton import qa
from baton.confidence import score
from baton.common import call
from baton.data_gen import DATASET_PATH, generate_dataset
from baton.interview import start_session, submit_answer
from baton.schemas import BatonDataset, ExpertReply, FactChecks, Grades, Session

EXPERT_SYSTEM = """\
You role-play a retiring finance operations manager being interviewed. You know ONLY the FACT \
SHEET. If the question is about something a fact covers: on the FIRST ask, answer briefly and a \
little vaguely ("it depends, I use judgement"); if the interview already asked about this topic \
(EARLIER shown), give the specific detail from the fact. If no fact covers it, say you don't \
remember. Never invent details. One to three sentences."""

CHECK_SYSTEM = """\
For each hidden fact, decide if the HANDOVER items capture its concrete detail (the specific \
threshold/name/reason), not just the topic. Return one check per fact id."""

GRADE_SYSTEM = """\
Grade each successor Q&A result. correct=true if: expected is empty and the system refused \
(supported=false); or expected is non-empty and the answer is supported and conveys the expected \
answer. Otherwise false. Return one grade per index."""


def load_dataset() -> BatonDataset:
    if DATASET_PATH.exists():
        return BatonDataset.model_validate_json(DATASET_PATH.read_text())
    ds = generate_dataset()
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_PATH.write_text(ds.model_dump_json(indent=2))
    return ds


def scripted_expert(ds: BatonDataset, s: Session, question: str) -> str:
    earlier = "\n".join(f"Q: {t.question}\nA: {t.answer}" for t in s.turns[:-1] if t.answer)
    facts = "\n".join(f"{f.id}: ({f.hint}) {f.truth}" for f in ds.hidden_facts)
    user = f"FACT SHEET:\n{facts}\n\nEARLIER:\n{earlier or '(none)'}\n\nQUESTION: {question}"
    return call("expert", ExpertReply, EXPERT_SYSTEM, user, fast=True).answer


def run_interview(ds: BatonDataset, progress=None, target: float = 0.8) -> Session:
    s = start_session(ds.docs, ds.last_day, target)
    while s.current_question:
        submit_answer(s, scripted_expert(ds, s, s.current_question))
        if progress:
            progress(len(s.turns))
    return s


def evaluate(ds: BatonDataset, s: Session) -> dict:
    hand = "\n".join(f"- {h.text}" for h in s.handover)
    facts = "\n".join(f"{f.id}: {f.truth}" for f in ds.hidden_facts)
    checks = call("check", FactChecks, CHECK_SYSTEM, f"FACTS:\n{facts}\n\nHANDOVER:\n{hand}").checks
    captured = sum(c.captured for c in checks)

    results = []
    for i, q in enumerate(ds.qa_questions):
        a = qa.ask(s, q.question)
        results.append({"index": i, "question": q.question, "expected": q.expected,
                        "answer": a.answer, "supported": a.supported, "citations": a.citations})
    grades = call("grade", Grades, GRADE_SYSTEM, json.dumps(results)).grades
    correct = sum(g.correct for g in grades)
    conf = score(s)
    return {
        "target": s.target, "confidence_log": s.confidence_log, "rounds": s.round,
        "confidence": conf["confidence"], "resolution": conf["resolution"],
        "faithfulness": conf["faithfulness"],
        "facts_total": len(ds.hidden_facts), "facts_captured": captured,
        "questions_asked": len(s.turns),
        "questions_per_fact": round(len(s.turns) / captured, 2) if captured else None,
        "qa_total": len(ds.qa_questions), "qa_correct": correct,
        "qa_results": results,
    }


def main() -> None:
    ds = load_dataset()
    s = run_interview(ds, progress=lambda n: print(f"  question {n}", end="\r"))
    m = evaluate(ds, s)
    print(f"\nConfidence by round: {[round(c, 2) for c in m['confidence_log']]} -> final {m['confidence']:.2f} "
          f"(target {m['target']:.2f}, rounds {m['rounds']})")
    print(f"Gap recall: {m['facts_captured']}/{m['facts_total']} (target >= 8)")
    print(f"Questions per fact captured: {m['questions_per_fact']} (target <= 2)")
    print(f"Q&A faithfulness: {m['qa_correct']}/{m['qa_total']} (target >= 13)")


if __name__ == "__main__":
    main()
