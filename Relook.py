"""Relook -- Streamlit demo UI.

Run with:  .venv/bin/streamlit run Relook.py
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import streamlit as st

from app.envload import load_dotenv

load_dotenv()

from app.data_gen import DATASET_PATH, generate_dataset  # noqa: E402
from app.ingest import SUPPORTED_EXTENSIONS, candidates_from_uploads  # noqa: E402
from app.llm import DailyQuotaExceeded  # noqa: E402
from app.guidance import MAX_CHARS as GUIDANCE_MAX, check_guidance, clean_guidance  # noqa: E402
from app.pipeline import (  # noqa: E402
    eval_metrics,
    pattern_report,
    rescued_bias_summary,
    results_to_csv,
    run_all,
)
from app.rubric_edit import rows_to_rubric, rubric_signature, rubric_to_rows  # noqa: E402
from app.rubric_extract import extract_rubric  # noqa: E402
from app.schemas import Candidate, Rubric  # noqa: E402

st.set_page_config(page_title="Relook", layout="wide")
st.title("Relook")
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

    demo_pool: list[Candidate] = st.session_state["candidates"]

    st.divider()
    st.header("Or upload CVs")
    st.caption(
        "PDF, DOCX or TXT. Hackathon rule: synthetic or public CVs only — "
        "no real personal data."
    )
    uploads = st.file_uploader(
        "CV files", type=list(SUPPORTED_EXTENSIONS), accept_multiple_files=True,
        label_visibility="collapsed",
    )
    parsed: list[Candidate] = []
    if uploads:
        parsed, upload_warnings = candidates_from_uploads([(f.name, f.getvalue()) for f in uploads])
        for w in upload_warnings:
            st.warning(w)
    active_pool = demo_pool
    if parsed:
        choice = st.radio(
            "Screen which pool?",
            [f"Uploaded CVs ({len(parsed)})", f"Demo pool ({len(demo_pool)})"],
            index=0,
        )
        if choice.startswith("Uploaded"):
            active_pool = parsed

    # A different pool invalidates any previous results.
    pool_sig = tuple((c.id, len(c.text)) for c in active_pool)
    if st.session_state.get("pool_sig") != pool_sig:
        st.session_state["pool_sig"] = pool_sig
        st.session_state["results"] = None
    st.session_state["active_candidates"] = active_pool

    st.divider()
    st.metric("Candidates loaded", len(active_pool))
    if not active_pool:
        st.warning(
            "No candidates yet. Regenerate the demo dataset above, upload CVs, or run "
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
    except DailyQuotaExceeded as e:
        st.error(str(e))
    except Exception as e:  # noqa: BLE001
        st.error(f"Rubric extraction failed (API hiccup) — try the button again. Detail: {e}")

extracted_rubric: Rubric | None = st.session_state["rubric"]
rubric: Rubric | None = extracted_rubric

if extracted_rubric:
    st.subheader("2. Rubric (editable)")
    st.caption(
        "Edit any cell, then re-run. **keywords** drive the keyword-ATS baseline (add one and "
        "watch the ATS shortlist change); **equivalents**, **type** and **weight** drive Relook."
    )
    edited_rows = st.data_editor(
        rubric_to_rows(extracted_rubric),
        # A new extracted rubric gets a fresh editor instead of inheriting stale edits.
        key=f"rubric_editor_{rubric_signature(extracted_rubric)}",
        hide_index=True,
        width="stretch",
        num_rows="fixed",
        disabled=["id"],
        column_config={
            "requirement": st.column_config.TextColumn("requirement", width="large"),
            "type": st.column_config.SelectboxColumn("type", options=["must", "nice"], required=True),
            "weight": st.column_config.NumberColumn("weight", min_value=1, max_value=5, step=1, required=True),
            "keywords": st.column_config.TextColumn(
                "keywords (ATS)", help="Comma-separated. What a keyword ATS scans for.", width="large"
            ),
            "equivalents": st.column_config.TextColumn(
                "equivalents (transferable)",
                help="Comma-separated. Skills/tools that satisfy it but use different words.",
                width="large",
            ),
        },
    )
    # `rubric` from here on is the EDITED rubric; that is what gets screened.
    rubric = rows_to_rubric(extracted_rubric, list(edited_rows))

    st.subheader("3. Run screening")
    anonymize = st.checkbox(
        "Anonymized review — hide names, contact details and dates/years from the model",
        value=False,
        help="Best-effort scrub of the text the AI sees (the ATS baseline is unchanged). "
        "Free text can still carry identifying details, so this is not a guarantee. "
        "Bias signals that depend on dates can't be detected in this mode; ones stated in the CV's own words still can.",
    )
    guidance_raw = st.text_area(
        "Additional screening instructions (optional)",
        value="",
        key="guidance",
        height=110,
        max_chars=GUIDANCE_MAX,
        placeholder="e.g. Treat Mesos, Nomad and ECS as equivalent to Kubernetes. We value fintech experience. "
        "Career gaps under 2 years should not count against a candidate.",
        help="Sent to the AI together with the rubric to steer how requirements are interpreted. It cannot "
        "override the fixed rules: quotes are still verified in code, the score is still computed in code, "
        "and instructions about age, gender, race, religion, disability or family status are rejected.",
    )
    guidance = clean_guidance(guidance_raw)
    guidance_problems = check_guidance(guidance_raw)
    for problem in guidance_problems:
        st.error(problem)
    guidance_sig = hashlib.sha256(guidance.encode()).hexdigest()[:8] if guidance else "none"
    run_sig = f"{rubric_signature(rubric)}|anon={anonymize}|guidance={guidance_sig}"
    candidates: list[Candidate] = st.session_state["active_candidates"]
    run_disabled = not candidates or bool(guidance_problems)
    if st.button("Run Relook on all candidates", disabled=run_disabled, type="primary"):
        progress = st.progress(0.0, text="Scoring candidates...")

        def _cb(done, total):
            progress.progress(done / total, text=f"Scoring candidates... {done}/{total}")

        try:
            with st.spinner("Running baseline + Relook scoring..."):
                results = run_all(candidates, rubric, progress_cb=_cb, anonymize=anonymize, guidance=guidance)
            st.session_state["results"] = results
            st.session_state["results_rubric_sig"] = run_sig
        except DailyQuotaExceeded as e:
            st.error(str(e) + " Candidates already scored are cached and kept.")
        except Exception as e:  # noqa: BLE001
            st.error(f"Scoring hit an API hiccup partway through — click Run again "
                     f"(cached candidates won't re-cost quota). Detail: {e}")
        finally:
            progress.empty()

    results = st.session_state["results"]
    if results and st.session_state.get("results_rubric_sig") != run_sig:
        st.info("The rubric, anonymization setting or instructions changed after the last run — click **Run Relook** again to re-screen.")
        results = None
    if results:
        baseline_pass = [r for r in results if r.baseline.passed]
        ai_pass = [r for r in results if r.shortlisted]
        rescued = [r for r in results if r.rescued]

        m = eval_metrics(results)
        if guidance:
            st.info(f"**Screened with your additional instructions:** {guidance}")
        st.subheader("4. Shortlists side by side")
        mc1, mc2, mc3 = st.columns(3)
        mc1.metric("ATS baseline shortlist", len(baseline_pass))
        mc2.metric("Relook shortlist", len(ai_pass), delta=f"+{len(rescued)} rescued")
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
            st.markdown("### Relook shortlist")
            for r in sorted(ai_pass, key=lambda r: -r.score.fit_score):
                badge = " 🟢 RESCUED" if r.rescued else ""
                st.write(f"- **{r.candidate.name}** ({r.candidate.id}) — fit {r.score.fit_score:.2f}{badge}")

        st.download_button(
            "Download full results (CSV)",
            data=results_to_csv(results, guidance=guidance),
            file_name="relook_results.csv",
            mime="text/csv",
        )

        st.subheader("5. Rejection pattern report")
        st.caption(
            "Which keyword rule is silently removing candidates, and how many of them "
            "Relook found to be genuinely qualified."
        )
        report_rows = pattern_report(results, rubric)
        if report_rows:
            st.dataframe(report_rows, width="stretch", hide_index=True)
            top = report_rows[0]
            st.warning(
                f"Rule **{top['rule']}** alone rejected {top['rejected_by_rule']} candidates; "
                f"Relook rescued {top['rescued_by_relook']} of them."
            )
        else:
            st.write("The keyword baseline rejected no one on this rubric.")
        bias_summary = rescued_bias_summary(results)
        if bias_summary:
            st.write(
                "**Bias signals flagged among rescued candidates:** "
                + ", ".join(f"`{k}` × {v}" for k, v in bias_summary.items())
            )

        st.subheader("6. Candidate detail")
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
