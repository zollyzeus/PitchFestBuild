"""Baton -- corporate knowledge-transfer workflow: PM setup, independent giver/taker Q&A,
gap assessment, action items, review, and a manager tracker."""
from __future__ import annotations

from datetime import date

import streamlit as st

from app.envload import load_dotenv

load_dotenv()

from baton import kt_engine as eng  # noqa: E402
from baton import kt_sim as sim  # noqa: E402
from baton.kt_eval import SAMPLE  # noqa: E402
from baton.kt_models import ANGLE_TITLE, STATUS_LABEL, KTRecord, ProjectInput  # noqa: E402
from baton.kt_store import (  # noqa: E402
    action_rows, deadline, list_all, load, readiness, reset_to_seed, row, time_in_stage_days,
    waiting_on,
)

st.set_page_config(page_title="Baton KT", layout="wide")
st.title("Baton")
st.caption("Knowledge transfer with proof: giver and taker are interviewed independently, gaps become "
           "action items, and the KT only closes when the evidence supports it.")


def guarded(fn, *a):
    try:
        with st.spinner("Working (AI calls, can take a few seconds each)..."):
            fn(*a)
        return True
    except Exception as e:  # noqa: BLE001
        st.error(f"API hiccup: nothing was lost, try again. Detail: {e}")
        return False


with st.sidebar:
    view = st.radio("Viewing as", ["Manager", "KT giver", "KT taker"])
    st.caption("Giver and taker views never show each other's answers.")
    if view == "Manager":
        with st.expander("Demo controls"):
            st.caption("Wipes every current KT (including anything just created or answered "
                       "live) and restores the 5 bundled demo KTs. No API calls, instant.")
            confirmed = st.checkbox("I understand this deletes all current KTs")
            if st.button("Reset to the 5 demo KTs", disabled=not confirmed, type="primary"):
                n = reset_to_seed()
                st.success(f"Restored {n} demo KTs.")
                st.rerun()

recs = list_all()
labels = {r.id: f"{r.project.title}  [{STATUS_LABEL[r.status]}]" for r in recs}


# ------------------------------------------------------------------ giver / taker
def participant_view(aud: str) -> None:
    mine = recs
    if not mine:
        st.info("No KT assigned yet. The manager creates one first.")
        return
    kt_id = st.selectbox("Your KT", [r.id for r in mine], format_func=labels.get)
    rec = load(kt_id)
    p = rec.project
    who = p.giver if aud == "giver" else p.taker
    st.subheader(f"{p.title}: {'KT giver' if aud == 'giver' else 'KT taker'} {who}")
    st.write(f"Deadline **{deadline(rec)}** · Stage **{STATUS_LABEL[rec.status]}**")

    qs = eng.current_questions(rec, aud)
    if qs:
        st.markdown(f"### Round {rec.q_round} questions")
        with st.form(f"q-{rec.id}-{aud}-{rec.q_round}"):
            vals = {q.id: st.text_area(f"{ANGLE_TITLE[q.angle]}: {q.question}", key=f"a-{q.id}") for q in qs}
            if st.form_submit_button("Submit my answers", type="primary"):
                if guarded(eng.submit_answers, rec, aud, vals):
                    st.rerun()
    elif rec.status in ("qa_round_1", "qa_round_2"):
        st.success("Your answers are recorded. Waiting on: " + (", ".join(waiting_on(rec)) or "-"))

    if rec.status in ("action_items", "open_redress", "closed", "escalated"):
        acts = [a for a in rec.actions if a.owner == aud]
        st.markdown("### Your action items")
        if not acts:
            st.write("None assigned.")
        for a in acts:
            with st.expander(f"{a.id} [{a.severity}] {a.description}  ·  due {a.due}  ·  {a.status}"
                             + (f" / {a.verdict}" if a.verdict else ""), expanded=a.status == "open"):
                st.write(f"Gap: {next((x.note for x in rec.assessments if x.angle == a.angle), '')}")
                if a.verdict_note:
                    st.info(f"Reviewer: {a.verdict_note}")
                if a.status == "open":
                    with st.form(f"r-{rec.id}-{a.id}-{rec.redress_round}"):
                        mode = st.radio("Your response", ["addressed", "justified"], horizontal=True,
                                        format_func=lambda m: "I addressed it" if m == "addressed"
                                        else "Justify ignoring this gap")
                        txt = st.text_area("Evidence of what you did, or your justification")
                        if st.form_submit_button("Submit response") and txt.strip():
                            if guarded(eng.respond_to_action, rec, a.id, mode, txt):
                                st.rerun()
                else:
                    st.write(f"Your response: {a.response}")
    if rec.decision_note:
        st.info(rec.decision_note)


# ------------------------------------------------------------------ manager
def manager_view() -> None:
    t_track, t_new, t_detail = st.tabs(["Tracker", "New KT", "KT detail"])

    with t_track:
        if not recs:
            st.info("No KTs yet. Create one in the New KT tab.")
        else:
            active = [r for r in recs if r.status not in ("closed", "escalated")]
            c = st.columns(6)
            c[0].metric("Active KTs", len(active))
            c[1].metric("Closed", sum(r.status == "closed" for r in recs))
            c[2].metric("Escalated", sum(r.status == "escalated" for r in recs))
            c[3].metric("Overdue", sum(row(r)["Overdue"] == "YES" for r in recs))
            c[4].metric("Waiting on givers", sum(any("giver" in w for w in waiting_on(r)) for r in active))
            c[5].metric("Waiting on takers", sum(any("taker" in w for w in waiting_on(r)) for r in active))
            st.dataframe([row(r) for r in recs], hide_index=True, width="stretch")
            st.markdown("#### Action items across all KTs")
            rows = action_rows(recs)
            st.dataframe(rows, hide_index=True, width="stretch") if rows else st.write("No action items yet.")

    with t_new:
        d = SAMPLE
        with st.form("new-kt"):
            title = st.text_input("Project name", d.title)
            desc = st.text_area("Project description", d.description)
            c1, c2, c3 = st.columns(3)
            dur = c1.number_input("KT duration (days)", 1, 120, d.duration_days)
            start = c2.date_input("Start date", date.today())
            thr = c3.slider("Target readiness to close", 50, 100, 80, step=5) / 100
            roles = st.text_area("Roles and responsibilities", d.roles)
            stack = st.text_input("Tech stack", d.tech_stack)
            dev = st.text_input("Dev environment", d.dev_env)
            test = st.text_input("Test environment", d.test_env)
            extra = st.text_area("Additional prompts for the interview (optional)", d.extra)
            g1, g2 = st.columns(2)
            giver = g1.text_input("KT giver", d.giver)
            taker = g2.text_input("KT taker", d.taker)
            if st.form_submit_button("Create KT and generate questions", type="primary"):
                proj = ProjectInput(title=title, description=desc, duration_days=int(dur),
                                    start_date=start.isoformat(), roles=roles, tech_stack=stack,
                                    dev_env=dev, test_env=test, extra=extra, giver=giver,
                                    taker=taker, threshold=thr)
                if guarded(eng.create_kt, proj):
                    st.success("KT created. Giver and taker can now answer independently.")
                    st.rerun()

    with t_detail:
        if not recs:
            st.info("Nothing yet.")
            return
        rec = load(st.selectbox("KT", [r.id for r in recs], format_func=labels.get))
        p = rec.project
        m = st.columns(5)
        m[0].metric("Stage", STATUS_LABEL[rec.status])
        m[1].metric("Readiness", f"{readiness(rec):.0%}" if rec.assessments else "-", delta=f"target {p.threshold:.0%}", delta_color="off")
        m[2].metric("Deadline", deadline(rec).isoformat())
        m[3].metric("In stage (days)", time_in_stage_days(rec))
        m[4].metric("Waiting on", ", ".join(waiting_on(rec)) or "-")
        if rec.decision_note:
            (st.success if rec.status == "closed" else st.warning)(rec.decision_note)

        with st.expander("Project inputs"):
            st.write(f"**{p.title}**: {p.description}")
            st.write(f"Roles: {p.roles}  \nStack: {p.tech_stack}  \nDev: {p.dev_env}  \nTest: {p.test_env}  \nNotes: {p.extra or '-'}")
        st.markdown("#### Timeline")
        st.dataframe([{"stage": STATUS_LABEL[s["stage"]], "entered": s["at"]} for s in rec.stage_log],
                     hide_index=True, width="stretch")
        if rec.readiness_log:
            st.line_chart({"readiness": [e["readiness"] for e in rec.readiness_log]})
        if rec.assessments:
            st.markdown("#### Angle assessment")
            st.dataframe([{"angle": ANGLE_TITLE[a.angle], "status": a.status,
                           "mismatch": "yes" if a.mismatch else "", "resolved": a.resolution,
                           "note": a.note} for a in rec.assessments], hide_index=True, width="stretch")
        if rec.actions:
            st.markdown("#### Action items")
            st.dataframe(action_rows([rec]), hide_index=True, width="stretch")
        with st.expander("Independent Q&A transcripts (manager only)"):
            for aud in ("giver", "taker"):
                st.markdown(f"**{aud.title()}**")
                for q in (q for q in rec.qa if q.audience == aud):
                    st.write(f"R{q.round} · {ANGLE_TITLE[q.angle]}: {q.question}")
                    st.caption(q.answer or "(unanswered)")

        st.markdown("#### Manager actions")
        b = st.columns(4)
        note = st.text_input("Note for override", key=f"note-{rec.id}")
        if b[0].button("Force close") and note:
            eng.manager_override(rec, "closed", note); st.rerun()
        if b[1].button("Escalate now") and note:
            eng.manager_override(rec, "escalated", note); st.rerun()
        st.markdown("#### Demo tools (scripted giver/taker personas)")
        s = st.columns(3)
        if s[0].button("Auto-answer as giver"):
            guarded(sim.step, rec, "giver"); st.rerun()
        if s[1].button("Auto-answer as taker"):
            guarded(sim.step, rec, "taker"); st.rerun()
        if s[2].button("Run this KT to the end"):
            guarded(sim.run_to_end, rec); st.rerun()


if view == "Manager":
    manager_view()
else:
    participant_view("giver" if view == "KT giver" else "taker")
