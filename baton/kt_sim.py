"""Scripted giver/taker personas so a KT can be demoed and evaluated unattended.

Planted weaknesses: the giver is vague on some angles, the taker misunderstands others.
"""
from __future__ import annotations

from baton import kt_engine as eng
from baton.common import call
from baton.kt_models import KTRecord, SimAnswers, SimResponses
from baton.kt_store import waiting_on

GIVER_WEAK = ["deploy", "support"]     # giver hand-waves these
TAKER_WEAK = ["environments", "testing"]  # taker is unsure or wrong on these
PLANTED = GIVER_WEAK + TAKER_WEAK

ANS_SYSTEM = """\
You role-play a participant in a project knowledge-transfer interview, answering each question \
in 2-4 sentences. INVENT plausible, concrete, consistent details for the project (tool names, \
commands, people, thresholds) so answers are usable.
Role {role}: {persona}
Round {rnd}. Return one answer per qid."""

PERSONA = {
    "giver": "You are an experienced engineer who knows the project well and answers concretely, "
             "EXCEPT on the angles {weak}: there you are vague and hand-wavy ('it's mostly in my head', "
             "'I just handle it', 'usual process'), giving no steps, names or commands. In round 2, for "
             "the FIRST weak angle only, give concrete detail; stay vague on the other.",
    "taker": "You are a capable but new engineer. You answer clearly where the project is simple, "
             "EXCEPT on the angles {weak}: there you are unsure, guess, or state something that does not "
             "match a typical setup ('I think it is the same as prod', 'not sure who grants access'). In "
             "round 2, for the FIRST weak angle only, show correct understanding; stay unsure on the other.",
}

RESP_SYSTEM = """\
You role-play the KT {role} responding to action items assigned to you. For each item choose \
mode 'addressed' and write a concrete response (specifics, steps, links, names, dates) as if the work \
is done, OR mode 'justified' with a reason to ignore it. {rule} Return one item per action_id."""
RULE = {
    "giver": "Address every item concretely.",
    "taker": "Address every item concretely EXCEPT any low-severity item: justify ignoring it with a "
             "short reason.",
}


def answer_round(rec: KTRecord, aud: str) -> None:
    qs = eng.current_questions(rec, aud)
    if not qs:
        return
    weak = ", ".join(GIVER_WEAK if aud == "giver" else TAKER_WEAK)
    system = ANS_SYSTEM.format(role=aud, persona=PERSONA[aud].format(weak=weak), rnd=rec.q_round)
    user = eng._project_text(rec.project) + "\n\nQUESTIONS:\n" + "\n".join(
        f"qid={q.id} [angle={q.angle}] {q.question}" for q in qs)
    got = {a.qid: a.answer for a in call(f"ktsim{aud}{rec.q_round}", SimAnswers, system, user).items}
    eng.submit_answers(rec, aud, {q.id: got.get(q.id, "") for q in qs})


def respond_actions(rec: KTRecord, aud: str) -> None:
    mine = [a for a in rec.actions if a.owner == aud and a.status == "open"]
    if not mine:
        return
    user = eng._project_text(rec.project) + "\n\nACTIONS:\n" + "\n".join(
        f"action_id={a.id} severity={a.severity} angle={a.angle}: {a.description}"
        + (f"\n  earlier response was rejected: {a.verdict_note}" if a.prev_responses else "")
        for a in mine)
    system = RESP_SYSTEM.format(role=aud, rule=RULE[aud])
    got = {r.action_id: r for r in call(f"ktresp{aud}{rec.redress_round}", SimResponses, system, user).items}
    for a in mine:
        r = got.get(a.id)
        eng.respond_to_action(rec, a.id, r.mode if r else "addressed", r.response if r else "Done.")
        if rec.status in ("closed", "escalated"):
            return


def step(rec: KTRecord, aud: str) -> None:
    """Simulate one side doing whatever is pending for them right now."""
    if rec.status in ("qa_round_1", "qa_round_2"):
        answer_round(rec, aud)
    elif rec.status in ("action_items", "open_redress"):
        respond_actions(rec, aud)


def run_to_end(rec: KTRecord, max_steps: int = 12) -> KTRecord:
    for _ in range(max_steps):
        if rec.status in ("closed", "escalated"):
            break
        for aud in ("giver", "taker"):
            step(rec, aud)
    return rec
