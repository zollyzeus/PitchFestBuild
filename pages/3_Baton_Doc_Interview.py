"""Baton -- Streamlit page: gap-driven handover interview + grounded successor Q&A."""
from __future__ import annotations

from pathlib import Path

import streamlit as st

from app.envload import load_dotenv

load_dotenv()

from baton import qa  # noqa: E402
from baton.eval import evaluate, load_dataset, run_interview  # noqa: E402
from baton.export import build_markdown  # noqa: E402
from baton.confidence import score  # noqa: E402
from baton.interview import open_risks, start_session, submit_answer  # noqa: E402
from baton.mapper import coverage  # noqa: E402
from baton.schemas import Session  # noqa: E402

SESSION_PATH = Path("data/baton_session.json")

st.set_page_config(page_title="Baton", layout="wide")
st.title("Baton")
st.caption("AI interviewer for a departing expert: reads their documents, asks only what the "
           "documents leave out, and hands the successor a sourced handover.")


def save(s: Session) -> None:
    SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
    SESSION_PATH.write_text(s.model_dump_json())


ds = load_dataset()
if "baton" not in st.session_state:
    # a refresh or crash does not lose the interview
    st.session_state["baton"] = (Session.model_validate_json(SESSION_PATH.read_text())
                                 if SESSION_PATH.exists() else None)
s: Session | None = st.session_state["baton"]

with st.sidebar:
    st.header("Scenario")
    st.write(f"**{ds.role_title}**  \nExpert: {ds.expert_name}  \nLast day: {ds.last_day}")
    st.caption("Synthetic documents only. The expert reviews everything attributed to them; "
               "the text interview stands in for voice.")
    target = st.slider("Target confidence", 50, 100, 80, step=5,
                       help="If the first interview round ends below this, Baton runs one "
                            "refinement round on the highest-priority unanswered gaps, then stops.") / 100
    if s:
        s.target = target
    if s and st.button("Reset session"):
        SESSION_PATH.unlink(missing_ok=True)
        st.session_state["baton"] = None
        st.rerun()

t_docs, t_int, t_hand, t_qa, t_eval = st.tabs(
    ["1. Documents & map", "2. Interview", "3. Handover", "4. Successor Q&A", "5. Evaluation"])

with t_docs:
    for d in ds.docs:
        with st.expander(d.name):
            st.text(d.text)
    if st.button("Build knowledge map & find gaps", type="primary"):
        try:
            with st.spinner("Reading documents, mapping duties, detecting gaps..."):
                s = start_session(ds.docs, ds.last_day, target)
            st.session_state["baton"] = s
            save(s)
        except Exception as e:  # noqa: BLE001
            st.error(f"API hiccup: click again (finished calls are cached). Detail: {e}")
    if s:
        st.metric("Coverage from documents alone", f"{s.baseline_coverage:.0%}")
        st.dataframe([{"id": i.id, "kind": i.kind, "item": i.title, "criticality": i.criticality,
                       "cadence": i.cadence, "sources": ", ".join(i.sources)} for i in s.kmap.items],
                     hide_index=True, width="stretch")
        st.subheader(f"{len(s.gaps)} gaps found")
        st.dataframe([{"id": g.id, "field": g.field, "priority": g.priority, "status": g.status,
                       "evidence": g.evidence} for g in s.gaps], hide_index=True, width="stretch")

with t_int:
    if not s:
        st.info("Build the knowledge map first.")
    else:
        sc = score(s)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Confidence", f"{sc['confidence']:.0%}", delta=f"target {s.target:.0%}", delta_color="off")
        c2.metric("Round", f"{s.round} of 2")
        c3.metric("Gaps resolved", f"{sc['resolution']:.0%}")
        c4.metric("Answers faithful", f"{sc['faithfulness']:.0%}")
        if s.round == 2:
            st.info(f"Round 1 ended at {s.confidence_log[0]:.0%}, below the {s.target:.0%} target, so "
                    "Baton reopened the highest-priority unanswered gaps for one refinement round.")
        for t in s.turns:
            with st.chat_message("assistant"):
                st.write(t.question)
            if t.answer:
                with st.chat_message("user"):
                    st.write(t.answer)
                st.caption(f"turn {t.n}: {t.verdict}")
        if s.current_question:
            ans = st.chat_input("Answer as the departing expert...")
            if ans:
                try:
                    with st.spinner("Judging answer..."):
                        submit_answer(s, ans)
                    save(s)
                except Exception as e:  # noqa: BLE001
                    st.error(f"API hiccup: send the answer again. Detail: {e}")
                st.rerun()
        else:
            final = score(s)["confidence"]
            (st.success if final >= s.target else st.warning)(
                f"Interview complete. Final confidence {final:.0%} vs target {s.target:.0%}"
                + ("" if final >= s.target else ": the risks below still need a human follow-up."))

with t_hand:
    if not s:
        st.info("Nothing yet.")
    else:
        st.metric("Confidence", f"{score(s)['confidence']:.0%}", delta=f"target {s.target:.0%}", delta_color="off")
        st.dataframe([{"item": h.item_id, "field": h.field, "captured": h.text, "source": h.source}
                      for h in s.handover], hide_index=True, width="stretch")
        st.subheader("Open risks")
        for r in open_risks(s)[:15]:
            st.write(f"- {r}")
        if st.button("Generate handover document + 30-60-90 plan"):
            try:
                st.session_state["baton_md"] = build_markdown(s, ds.role_title, ds.expert_name, ds.last_day)
            except Exception as e:  # noqa: BLE001
                st.error(f"API hiccup: click again. Detail: {e}")
        if "baton_md" in st.session_state:
            st.download_button("Download handover (Markdown)", st.session_state["baton_md"],
                               file_name="handover.md", mime="text/markdown")
            st.markdown(st.session_state["baton_md"])

with t_qa:
    if not s:
        st.info("Nothing yet.")
    else:
        q = st.text_input("Ask as the successor", placeholder="e.g. What do I do when the bank feed breaks?")
        if q:
            try:
                a = qa.ask(s, q)
                save(s)
                (st.write if a.supported else st.warning)(a.answer)
                if a.citations:
                    st.caption("Sources: " + " ".join(f"`{c}`" for c in a.citations))
            except Exception as e:  # noqa: BLE001
                st.error(f"API hiccup: try again. Detail: {e}")
        st.caption("Unsupported questions return 'Not captured' and are logged as gaps for the expert.")

with t_eval:
    st.write("A scripted expert answers the whole interview from the hidden fact sheet, then the "
             "result is scored. Takes several minutes on the free API tier; cached afterwards.")
    if st.button("Run unattended evaluation"):
        bar = st.progress(0.0, text="Interviewing scripted expert...")
        try:
            es = run_interview(ds, target=target, progress=lambda n: bar.progress(min(n / 25, 1.0), text=f"question {n}"))
            st.session_state["baton_eval"] = evaluate(ds, es)
        except Exception as e:  # noqa: BLE001
            st.error(f"API hiccup: click again. Detail: {e}")
        bar.empty()
    m = st.session_state.get("baton_eval")
    if m:
        st.write(f"Confidence by round: {' -> '.join(f'{c:.0%}' for c in m['confidence_log'])} "
                 f"(final {m['confidence']:.0%}, target {m['target']:.0%}, {m['rounds']} round(s))")
        a, b, c = st.columns(3)
        a.metric("Gap recall", f"{m['facts_captured']}/{m['facts_total']}")
        b.metric("Questions per fact", m["questions_per_fact"])
        c.metric("Q&A faithfulness", f"{m['qa_correct']}/{m['qa_total']}")
        st.dataframe(m["qa_results"], hide_index=True, width="stretch")
