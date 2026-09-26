"""Orchestrates baseline + AI scoring + grounding + the deterministic fit score
that decides the Second Look shortlist. The score NUMBER is always computed
here in plain Python from grounded verdicts -- never asserted by the model."""
from __future__ import annotations

from dataclasses import dataclass

from app.baseline import run_baseline
from app.grounding import apply_grounding
from app.schemas import BaselineResult, Candidate, CandidateScore, Rubric
from app.scorer import score_candidate

VERDICT_VALUE = {"met": 1.0, "partial": 0.5, "not_met": 0.0}
TRANSFERABLE_MET_VALUE = 0.85
FIT_THRESHOLD = 0.6


@dataclass
class CandidateResult:
    candidate: Candidate
    baseline: BaselineResult
    score: CandidateScore
    rescued: bool  # baseline rejected it, Second Look shortlists it


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


def run_one(candidate: Candidate, rubric: Rubric) -> CandidateResult:
    baseline = run_baseline(candidate, rubric)
    score = score_candidate(rubric, candidate)
    apply_grounding(score, candidate.text)
    shortlisted = compute_fit(score, rubric)
    rescued = (not baseline.passed) and shortlisted
    return CandidateResult(candidate=candidate, baseline=baseline, score=score, rescued=rescued)


def run_all(candidates: list[Candidate], rubric: Rubric, progress_cb=None) -> list[CandidateResult]:
    results = []
    for i, c in enumerate(candidates):
        results.append(run_one(c, rubric))
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
