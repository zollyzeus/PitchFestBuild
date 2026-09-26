"""KT workflow engine: question generation, independent answers, assessment, action items,
review of owner responses, and the close / redress / escalate decision (decision is plain code)."""
from __future__ import annotations

from datetime import date, timedelta

from baton.common import call, norm
from baton.kt_models import (
    ANGLE_DESC, ANGLE_KEYS, ANGLE_TITLE, MAX_REDRESS, QA, Action, ActionSet, AngleAssessment,
    AssessmentSet, KTRecord, ProjectInput, QuestionSet, ReviewSet,
)
from baton.kt_store import ACTION_DAYS, deadline, new_id, now, readiness, save, set_status

MAX_ACTIONS = 10

Q_SYSTEM = """\
You design a knowledge-transfer (KT) interview for a corporate software project handover. For \
each requested angle key write ONE question for each side:
- giver_question, for the KT giver (outgoing owner): extract what the taker needs, probing what is \
documented, what only lives in their head, and pitfalls.
- taker_question, for the KT taker (incoming owner): test real understanding and ability to act \
alone (e.g. 'walk me through how you would ...').
Both questions for an angle must cover the same topic so the two answers can be compared. Make \
them specific to the project's tech stack, environments and roles, naming concrete technologies \
from the input. Each under 45 words. Return exactly one item per requested angle key, using the key \
as `angle`."""

Q2_EXTRA = """
This is the FOLLOW-UP round. For each angle you are shown the earlier answers and what was found \
missing. Ask sharper questions aimed at exactly what was missing, vague or contradictory. Do not \
repeat earlier questions."""

A_SYSTEM = """\
You assess whether a knowledge transfer is sufficient, angle by angle, by comparing the KT giver's \
answers with the KT taker's answers. For each angle key:
- covered: the giver gave concrete, actionable detail (names, commands, thresholds, locations, \
reasons) AND the taker's answers show they understand it and could act on it alone.
- partial: one side is thin, or there is a minor mismatch.
- gap: knowledge is missing, vague, or the two sides contradict each other.
mismatch = true when the taker's understanding contradicts or misses key things the giver said, or \
the two accounts do not line up.
giver_evidence / taker_evidence: a SHORT quote copied word for word from that side's answers that \
supports your judgement, or empty if none. note: one sentence saying what is missing. Return \
exactly one item per angle key."""

ACT_SYSTEM = f"""\
You recommend action items to close knowledge-transfer gaps. For each angle assessed partial, gap \
or mismatch, recommend one concrete action for the KT giver (e.g. document X, record a walkthrough \
of Y, hand over credential process Z) or the KT taker (e.g. shadow a deployment, run the test \
suite and report, write back the incident procedure). At most {MAX_ACTIONS} actions in total, \
most severe first. severity: high/medium/low by business risk. description: imperative, under 30 \
words, and testable so a reviewer can tell if it was done."""

R_SYSTEM = """\
You review owners' responses to KT action items. mode=addressed: accept only if the response gives \
concrete evidence the action was done or the missing knowledge is now supplied (specifics, links, \
names, steps, dates). mode=justified: the owner wants to ignore the gap; accept only if the \
justification is credible for a low-risk item (why it does not matter, or where it is already \
covered); be strict with high-severity items. Reject vague responses and say what is still needed. \
Return one verdict per action_id."""


def _project_text(p: ProjectInput) -> str:
    return (f"PROJECT: {p.title}\nDESCRIPTION: {p.description}\nDURATION: {p.duration_days} days\n"
            f"ROLES & RESPONSIBILITIES: {p.roles}\nTECH STACK: {p.tech_stack}\n"
            f"DEV ENVIRONMENT: {p.dev_env}\nTEST ENVIRONMENT: {p.test_env}\n"
            f"MANAGER NOTES: {p.extra or '-'}\nKT GIVER: {p.giver}\nKT TAKER: {p.taker}")


def _answers(rec: KTRecord, angle: str, aud: str) -> str:
    return "\n".join(f"Q: {q.question}\nA: {q.answer or '(no answer)'}"
                     for q in rec.qa if q.angle == angle and q.audience == aud)


def _note(rec: KTRecord, angle: str) -> str:
    a = next((a for a in rec.assessments if a.angle == angle), None)
    return a.note if a else ""


def add_questions(rec: KTRecord, angles: list[str], rnd: int) -> None:
    user = _project_text(rec.project) + "\n\nANGLES:\n" + "\n".join(
        f"- {k}: {ANGLE_TITLE[k]} ({ANGLE_DESC[k]})" for k in angles)
    system = Q_SYSTEM
    if rnd > 1:
        system += Q2_EXTRA
        user += "\n\nEARLIER ANSWERS AND FINDINGS:\n" + "\n\n".join(
            f"[{k}] missing: {_note(rec, k)}\nGIVER:\n{_answers(rec, k, 'giver')}\nTAKER:\n{_answers(rec, k, 'taker')}"
            for k in angles)
    got = {i.angle: i for i in call(f"ktq{rnd}", QuestionSet, system, user).items}
    for k in angles:
        i = got.get(k)
        g = i.giver_question if i else f"Walk the taker through {ANGLE_TITLE[k]}: what do they need to know?"
        t = i.taker_question if i else f"Explain in your own words how {ANGLE_TITLE[k]} works for this project."
        rec.qa.append(QA(id=f"R{rnd}-{k}-giver", round=rnd, angle=k, audience="giver", question=g))
        rec.qa.append(QA(id=f"R{rnd}-{k}-taker", round=rnd, angle=k, audience="taker", question=t))


def create_kt(project: ProjectInput) -> KTRecord:
    rec = KTRecord(id=new_id(project.title), project=project, created_at=now())
    set_status(rec, "qa_round_1")
    add_questions(rec, ANGLE_KEYS, 1)
    save(rec)
    return rec


def current_questions(rec: KTRecord, aud: str) -> list[QA]:
    if rec.status not in ("qa_round_1", "qa_round_2") or f"R{rec.q_round}-{aud}" in rec.submitted:
        return []
    return [q for q in rec.qa if q.round == rec.q_round and q.audience == aud]


def submit_answers(rec: KTRecord, aud: str, answers: dict[str, str]) -> None:
    """Record one side's answers independently; advance once BOTH sides have submitted."""
    key = f"R{rec.q_round}-{aud}"
    if key in rec.submitted:
        return
    for q in rec.qa:
        if q.id in answers and q.audience == aud and q.round == rec.q_round:
            q.answer, q.answered_at = answers[q.id].strip(), now()
    rec.submitted[key] = now()
    save(rec)
    if all(f"R{rec.q_round}-{a}" in rec.submitted for a in ("giver", "taker")):
        advance(rec)


def assess(rec: KTRecord) -> None:
    user = _project_text(rec.project) + "\n\n" + "\n\n".join(
        f"### {k} ({ANGLE_TITLE[k]})\nGIVER:\n{_answers(rec, k, 'giver')}\nTAKER:\n{_answers(rec, k, 'taker')}"
        for k in ANGLE_KEYS)
    got = {i.angle: i for i in call("ktassess", AssessmentSet, A_SYSTEM, user).items}
    out = []
    for k in ANGLE_KEYS:
        g_text = norm(" ".join(q.answer for q in rec.qa if q.angle == k and q.audience == "giver"))
        t_text = norm(" ".join(q.answer for q in rec.qa if q.angle == k and q.audience == "taker"))
        i = got.get(k)
        if not i:
            out.append(AngleAssessment(angle=k, status="gap", note="Not assessed."))
            continue
        status, note = i.status, i.note
        ge = i.giver_evidence if len(norm(i.giver_evidence).strip(" .\"'")) >= 6 and \
            norm(i.giver_evidence).strip(" .\"'") in g_text else ""
        te = i.taker_evidence if len(norm(i.taker_evidence).strip(" .\"'")) >= 6 and \
            norm(i.taker_evidence).strip(" .\"'") in t_text else ""
        if not g_text.strip() or not t_text.strip():
            status, note = "gap", "One side gave no answer."
        elif status == "covered" and not (ge and te):
            status, note = "partial", (note + " (No verifiable quote from both sides.)").strip()
        out.append(AngleAssessment(angle=k, status=status, giver_evidence=ge, taker_evidence=te,
                                   mismatch=i.mismatch, note=note))
    rec.assessments = out
    rec.readiness_log.append({"at": now(), "stage": rec.status, "readiness": round(readiness(rec), 3)})


def advance(rec: KTRecord) -> None:
    assess(rec)
    weak = [a.angle for a in rec.assessments if a.status != "covered" or a.mismatch]
    if weak and rec.q_round < 2:
        rec.q_round = 2
        add_questions(rec, weak, 2)
        set_status(rec, "qa_round_2")
    else:
        make_actions(rec)
    save(rec)


def make_actions(rec: KTRecord) -> None:
    weak = [a for a in rec.assessments if a.status != "covered" or a.mismatch]
    due = min(date.today() + timedelta(days=ACTION_DAYS), max(deadline(rec), date.today())).isoformat()
    if weak:
        user = _project_text(rec.project) + "\n\nASSESSMENTS:\n" + "\n".join(
            f"- {a.angle}: {a.status}{' + mismatch' if a.mismatch else ''}: {a.note}" for a in weak)
        items = [i for i in call("ktact", ActionSet, ACT_SYSTEM, user).items if i.angle in ANGLE_KEYS]
        order = {"high": 0, "medium": 1, "low": 2}
        for n, i in enumerate(sorted(items, key=lambda i: order[i.severity])[:MAX_ACTIONS], 1):
            rec.actions.append(Action(id=f"A{n}", angle=i.angle, owner=i.owner,
                                      description=i.description, severity=i.severity, due=due))
    if rec.actions:
        set_status(rec, "action_items")
    else:
        decide(rec)


def respond_to_action(rec: KTRecord, action_id: str, mode: str, text: str) -> None:
    a = next(a for a in rec.actions if a.id == action_id)
    a.status, a.response, a.responded_at = mode, text.strip(), now()  # type: ignore[assignment]
    save(rec)
    if all(x.status != "open" for x in rec.actions):
        review(rec)


def review(rec: KTRecord) -> None:
    todo = [a for a in rec.actions if a.verdict != "accepted"]
    user = "\n\n".join(
        f"action_id: {a.id}\nangle: {a.angle}\nseverity: {a.severity}\naction: {a.description}\n"
        f"mode: {a.status}\nresponse: {a.response}\ngap found: {_note(rec, a.angle)}" for a in todo)
    got = {v.action_id: v for v in call("ktreview", ReviewSet, R_SYSTEM, user).items}
    for a in todo:
        v = got.get(a.id)
        ok = bool(v and v.accepted and a.response)
        a.verdict, a.verdict_note = ("accepted" if ok else "rejected"), (v.note if v else "No verdict returned.")
    for asm in rec.assessments:
        acts = [a for a in rec.actions if a.angle == asm.angle]
        if acts and all(a.verdict == "accepted" for a in acts):
            asm.resolution = "accepted_risk" if any(a.status == "justified" for a in acts) else "addressed"
    rec.readiness_log.append({"at": now(), "stage": "review", "readiness": round(readiness(rec), 3)})
    decide(rec)


def decide(rec: KTRecord) -> None:
    """Deterministic close / keep-open / escalate rule."""
    r = readiness(rec)
    unresolved = [a for a in rec.actions if a.verdict != "accepted"]
    if not unresolved and r >= rec.project.threshold:
        rec.decision_note = f"Closed: all action items resolved, readiness {r:.0%} >= target {rec.project.threshold:.0%}."
        set_status(rec, "closed")
    elif unresolved and rec.redress_round < MAX_REDRESS:
        rec.redress_round += 1
        for a in unresolved:
            if a.response:
                a.prev_responses.append(a.response)
            a.status, a.response, a.verdict = "open", "", ""
        rec.decision_note = (f"Kept open for redress round {rec.redress_round}: {len(unresolved)} item(s) "
                             f"unresolved, readiness {r:.0%}.")
        set_status(rec, "open_redress")
    else:
        rec.decision_note = (f"Escalated: {len(unresolved)} item(s) unresolved after the redress round, "
                             f"readiness {r:.0%} vs target {rec.project.threshold:.0%}.")
        set_status(rec, "escalated")
    save(rec)


def manager_override(rec: KTRecord, status: str, note: str) -> None:
    rec.decision_note = f"Manager override -> {status}: {note}"
    set_status(rec, status)
    save(rec)
