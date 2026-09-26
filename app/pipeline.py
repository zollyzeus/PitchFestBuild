"""Orchestrates baseline + AI scoring + grounding + the deterministic fit score
that decides the Second Look shortlist. The score NUMBER is always computed
here in plain Python from grounded verdicts -- never asserted by the model."""
from __future__ import annotations

from dataclasses import dataclass

from app.anonymize import anonymize_text
from app.baseline import run_baseline
from app.grounding import apply_grounding
from app.schemas import BaselineResult, Candidate, CandidateScore, Rubric
from app.scorer import score_candidate

import re  # noqa: E402

_REDACTION_ARTIFACT = re.compile(r"placeholder|redact|anonymi[sz]", re.I)

VERDICT_VALUE = {"met": 1.0, "partial": 0.5, "not_met": 0.0}
TRANSFERABLE_MET_VALUE = 0.85
FIT_THRESHOLD = 0.6


@dataclass
class CandidateResult:
    candidate: Candidate
    baseline: BaselineResult
    score: CandidateScore
    rescued: bool  # baseline rejected it, Second Look shortlists it
    shortlisted: bool = False  # Second Look's actual decision (fit bar AND must-have gate)


def compute_fit(score: CandidateScore, rubric: Rubric) -> bool:
    """Fills in score.fit_score / must_have_gate_passed in place; returns
    whether the candidate clears the Second Look shortlist bar."""
    weight_by_id = {r.id: r.weight for r in rubric.requirements}
    must_ids = {r.id for r in rubric.requirements if r.type == "must"}
    total_w = sum(weight_by_id.values()) or 1
    numerator = 0.0
    must_gate_ok = True
    for r in score.requirements:
        w = weight_by_id.get(r.req_id, 1)
        if not r.grounded:
            value = 0.0  # unverified claim never counts, regardless of verdict
        elif r.transferable and r.verdict == "met":
            value = TRANSFERABLE_MET_VALUE
        else:
            value = VERDICT_VALUE.get(r.verdict, 0.0)
        numerator += w * value
        if r.req_id in must_ids and value == 0.0:
            must_gate_ok = False
    score.fit_score = round(numerator / total_w, 3)
    score.must_have_gate_passed = must_gate_ok
    return must_gate_ok and score.fit_score >= FIT_THRESHOLD


def run_one(
    candidate: Candidate, rubric: Rubric, anonymize: bool = False, guidance: str = ""
) -> CandidateResult:
    # The ATS baseline always sees the full CV (it is the thing being audited). In
    # anonymized mode only the *model* is blinded, and grounding is checked against
    # exactly the text the model was shown.
    baseline = run_baseline(candidate, rubric)
    model_view = (
        candidate.model_copy(update={"text": anonymize_text(candidate.text, candidate.name)})
        if anonymize
        else candidate
    )
    score = score_candidate(rubric, model_view, anonymized=anonymize, guidance=guidance)
    if anonymize:
        # Belt and braces: drop any signal that is really about our own redaction tokens.
        score.bias_signals = [
            b for b in score.bias_signals
            if not _REDACTION_ARTIFACT.search(f"{b.type} {b.note}")
        ]
    apply_grounding(score, model_view.text)
    shortlisted = compute_fit(score, rubric)
    rescued = (not baseline.passed) and shortlisted
    return CandidateResult(
        candidate=candidate, baseline=baseline, score=score, rescued=rescued, shortlisted=shortlisted
    )


def run_all(
    candidates: list[Candidate], rubric: Rubric, progress_cb=None, anonymize: bool = False,
    guidance: str = "",
) -> list[CandidateResult]:
    results = []
    for i, c in enumerate(candidates):
        results.append(run_one(c, rubric, anonymize=anonymize, guidance=guidance))
        if progress_cb:
            progress_cb(i + 1, len(candidates))
    return results


# --- Live evaluation against the synthetic dataset's planted ground truth ---


def eval_metrics(results: list[CandidateResult]) -> dict:
    planted_qualified = [r for r in results if r.candidate.planted_qualified is True]
    planted_unqualified = [r for r in results if r.candidate.planted_qualified is False]
    hard_rescues = [r for r in planted_qualified if not r.baseline.passed]

    rescued_of_hard = [r for r in hard_rescues if r.rescued]
    false_rescues = [r for r in planted_unqualified if r.rescued]

    # Only count requirements where the model actually claimed evidence (verdict != not_met);
    # an empty quote on a not_met verdict isn't a grounding failure, there was nothing to ground.
    claimed = [rq for r in results for rq in r.score.requirements if rq.verdict != "not_met"]
    grounded_flags = [rq.grounded for rq in claimed]
    grounding_rate = (sum(grounded_flags) / len(grounded_flags)) if grounded_flags else 0.0

    return {
        "hard_rescue_total": len(hard_rescues),
        "hard_rescue_recovered": len(rescued_of_hard),
        "hard_rescue_recall": (len(rescued_of_hard) / len(hard_rescues)) if hard_rescues else None,
        "false_rescues": len(false_rescues),
        "planted_unqualified_total": len(planted_unqualified),
        "grounding_rate": grounding_rate,
    }


# --- F8: rejection-pattern report ---


def pattern_report(results: list[CandidateResult], rubric: Rubric) -> list[dict]:
    """Per must-have rule: how many candidates the keyword baseline rejected on it,
    how many of those Second Look rescued, how many were genuinely qualified per the
    planted ground truth (if present), and how many carry a bias signal. This is the
    'which filter rule is silently removing good people' view a compliance team wants."""
    rows = []
    for req in rubric.requirements:
        if req.type != "must":
            continue
        hit = [r for r in results if req.id in r.baseline.fired_req_ids]
        if not hit:
            continue
        rows.append(
            {
                "rule": f"{req.id}: {req.text}",
                "keywords_the_ATS_scanned_for": ", ".join(req.keywords) or "-",
                "rejected_by_rule": len(hit),
                "rescued_by_second_look": sum(1 for r in hit if r.rescued),
                "truly_qualified_(ground_truth)": sum(
                    1 for r in hit if r.candidate.planted_qualified is True
                ),
                "with_bias_signal": sum(1 for r in hit if r.score.bias_signals),
            }
        )
    rows.sort(key=lambda row: -row["rejected_by_rule"])
    return rows


def rescued_bias_summary(results: list[CandidateResult]) -> dict[str, int]:
    """Bias-signal types flagged among the RESCUED candidates only."""
    counts: dict[str, int] = {}
    for r in results:
        if not r.rescued:
            continue
        for b in r.score.bias_signals:
            counts[b.type] = counts.get(b.type, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


# --- F9: CSV export ---


def results_to_csv(results: list[CandidateResult], guidance: str = "") -> str:
    import csv
    import io

    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(
        [
            "candidate_id", "name", "ats_baseline", "ats_rules_fired", "fit_score",
            "second_look_shortlisted", "rescued", "evidence_quotes", "bias_signals",
            "interview_questions", "planted_qualified_ground_truth", "screening_guidance",
        ]
    )
    for r in sorted(results, key=lambda r: -r.score.fit_score):
        evidence = " || ".join(
            f"{rq.req_id} ({rq.verdict}{'' if rq.grounded else ', UNVERIFIED'}): {rq.quote}"
            for rq in r.score.requirements
            if rq.quote
        )
        bias = " || ".join(f"{b.type}: {b.evidence}" for b in r.score.bias_signals)
        w.writerow(
            [
                r.candidate.id,
                r.candidate.name,
                "passed" if r.baseline.passed else "rejected",
                ", ".join(r.baseline.fired_req_ids),
                f"{r.score.fit_score:.2f}",
                "yes" if r.shortlisted else "no",
                "yes" if r.rescued else "no",
                evidence,
                bias,
                " | ".join(r.score.interview_questions),
                "" if r.candidate.planted_qualified is None else r.candidate.planted_qualified,
                guidance,
            ]
        )
    return buf.getvalue()
