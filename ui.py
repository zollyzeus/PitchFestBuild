"""Second Look -- Streamlit demo UI.

Run with:  .venv/bin/streamlit run app/app.py
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from app.envload import load_dotenv

load_dotenv()

from app.data_gen import DATASET_PATH, generate_dataset  # noqa: E402
from app.pipeline import eval_metrics, run_all  # noqa: E402
from app.rubric_extract import extract_rubric  # noqa: E402
from app.schemas import Candidate, Rubric  # noqa: E402

st.set_page_config(page_title="Second Look", layout="wide")
st.title("Second Look")
st.caption(
    "Re-screens the CVs a keyword ATS rejected, surfaces the qualified ones it missed, "
    "with cited evidence and bias flags."
)


def _load_dataset() -> tuple[str, str, list[Candidate]]:
    if DATASET_PATH.exists():
        data = json.loads(DATASET_PATH.read_text())
        candidates = [Candidate.model_validate(c) for c in data["candidates"]]
        return data["role_title"], data["jd_text"], candidates
    return "", "", []


if "jd_text" not in st.session_state:
    role_title, jd_text, candidates = _load_dataset()
    st.session_state["role_title"] = role_title
    st.session_state["jd_text"] = jd_text
    st.session_state["candidates"] = candidates
    st.session_state["rubric"] = None
    st.session_state["results"] = None

with st.sidebar:
    st.header("Demo data")
    if st.button("Regenerate synthetic dataset (uses quota)"):
        with st.spinner("Generating JD + 16 synthetic CVs..."):
            ds = generate_dataset()
            DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
            DATASET_PATH.write_text(ds.model_dump_json(indent=2))
            st.session_state["role_title"] = ds.role_title
            st.session_state["jd_text"] = ds.jd_text
            st.session_state["candidates"] = ds.candidates
            st.session_state["rubric"] = None
            st.session_state["results"] = None
        st.success(f"Generated {len(ds.candidates)} candidates.")

    n = len(st.session_state["candidates"])
    st.metric("Candidates loaded", n)
    if n == 0:
        st.warning(
            "No dataset yet. Click the button above, or run "
            "`.venv/bin/python -m app.data_gen` from a terminal."
        )

st.subheader("1. Job description")
jd_text = st.text_area(
    "Paste or edit the job description (the judge can replace this entirely)",
    value=st.session_state["jd_text"],
    height=180,
)
st.session_state["jd_text"] = jd_text

col_a, col_b = st.columns([1, 3])
with col_a:
    extract_clicked = st.button("Extract rubric", type="primary", disabled=not jd_text.strip())

if extract_clicked:
    try:
        with st.spinner("Extracting rubric..."):
            st.session_state["rubric"] = extract_rubric(jd_text)
            st.session_state["results"] = None
    except Exception as e:  # noqa: BLE001
        st.error(f"Rubric extraction failed (API hiccup) — try the button again. Detail: {e}")

rubric: Rubric | None = st.session_state["rubric"]

if rubric:
    st.subheader("2. Rubric (editable)")
    for req in rubric.requirements:
        with st.expander(f"{req.id} [{req.type}, w={req.weight}] {req.text}"):
            st.write(f"**Keywords (what a keyword ATS looks for):** {', '.join(req.keywords) or '-'}")
            st.write(f"**Equivalents (transferable, ATS misses these):** {', '.join(req.equivalents) or '-'}")

    st.subheader("3. Run screening")
    candidates: list[Candidate] = st.session_state["candidates"]
    run_disabled = not candidates
    if st.button("Run Second Look on all candidates", disabled=run_disabled, type="primary"):
        progress = st.progress(0.0, text="Scoring candidates...")

        def _cb(done, total):
            progress.progress(done / total, text=f"Scoring candidates... {done}/{total}")

        try:
            with st.spinner("Running baseline + Second Look scoring..."):
                results = run_all(candidates, rubric, progress_cb=_cb)
            st.session_state["results"] = results
        except Exception as e:  # noqa: BLE001
            st.error(f"Scoring hit an API hiccup partway through — click Run again "
                     f"(cached candidates won't re-cost quota). Detail: {e}")
        finally:
            progress.empty()

    results = st.session_state["results"]
    if results:
        baseline_pass = [r for r in results if r.baseline.passed]
        ai_pass = [r for r in results if r.rescued or (r.baseline.passed and r.score.fit_score >= 0.6)]
        rescued = [r for r in results if r.rescued]

        m = eval_metrics(results)
        st.subheader("4. Shortlists side by side")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("ATS baseline shortlist", len(baseline_pass))
        mc2.metric("Second Look shortlist", len(ai_pass), delta=f"+{len(rescued)} rescued")
        mc3.metric("Grounding rate", f"{m['grounding_rate']*100:.0f}%")

        if m["hard_rescue_recall"] is not None:
            st.info(
                f"Live eval on this dataset's planted ground truth: recovered "
                f"{m['hard_rescue_recovered']}/{m['hard_rescue_total']} hard-rescue candidates "
                f"(recall {m['hard_rescue_recall']*100:.0f}%), with {m['false_rescues']}/"
                f"{m['planted_unqualified_total']} false rescues."
            )

        col1, col2 = st.columns(2)
        with col1:
            st.markdown("### ATS baseline shortlist")
            for r in sorted(baseline_pass, key=lambda r: -r.score.fit_score):
                st.write(f"- **{r.candidate.name}** ({r.candidate.id})")
        with col2:
            st.markdown("### Second Look shortlist")
            for r in sorted(ai_pass, key=lambda r: -r.score.fit_score):
                badge = " 🟢 RESCUED" if r.rescued else ""
                st.write(f"- **{r.candidate.name}** ({r.candidate.id}) — fit {r.score.fit_score:.2f}{badge}")

        st.subheader("5. Candidate detail")
        by_id = {r.candidate.id: r for r in results}
        pick = st.selectbox(
            "Choose a candidate",
            options=list(by_id.keys()),
            format_func=lambda cid: f"{by_id[cid].candidate.name} ({cid})"
            + (" — rescued" if by_id[cid].rescued else ""),
        )
        r = by_id[pick]
        st.markdown(f"**Fit score:** {r.score.fit_score:.2f}  ·  "
                    f"**Baseline:** {'passed' if r.baseline.passed else 'rejected'}"
                    + (f" — {', '.join(r.baseline.fired_rules)}" if r.baseline.fired_rules else ""))

        req_by_id = {req.id: req for req in rubric.requirements}
        for sr in r.score.requirements:
            req = req_by_id.get(sr.req_id)
            label = req.text if req else sr.req_id
            verdict_shown = sr.verdict if sr.grounded else "unverified"
            st.markdown(f"**{sr.req_id} — {label}**: `{verdict_shown}`"
                        + (" · transferable" if sr.transferable else ""))
            if sr.quote:
                st.markdown(f"> {sr.quote}")
            st.caption(sr.reasoning)

        if r.score.bias_signals:
            st.markdown("**Bias signals**")
            for b in r.score.bias_signals:
                st.write(f"- `{b.type}`: {b.evidence}" + (f" — {b.note}" if b.note else ""))

        if r.score.interview_questions:
            st.markdown("**Suggested interview questions**")
            for q in r.score.interview_questions:
                st.write(f"- {q}")

st.divider()
st.caption(
    "Assumptions: synthetic candidates only; recommends a human second review and never "
    "auto-rejects/auto-hires; bias flags are signals for a reviewer, not a legal audit."
)
