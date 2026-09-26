"""Per-candidate evidence scoring (Gemini call #2, one call per CV)."""
from __future__ import annotations

from app.cache import get_or_compute
from app.guidance import clean_guidance, guidance_prompt_block
from app.llm import MODEL_FAST, call_structured
from app.schemas import (
    BiasSignal,
    Candidate,
    CandidateScore,
    RawCandidateScore,
    Rubric,
    ScoredRequirement,
)


def _rubric_as_text(rubric: Rubric) -> str:
    lines = [f"Role: {rubric.role_title}", ""]
    for r in rubric.requirements:
        lines.append(
            f"- {r.id} [{r.type}, weight {r.weight}]: {r.text}\n"
            f"    keywords: {', '.join(r.keywords) or '(none)'}\n"
            f"    equivalents that also satisfy it: {', '.join(r.equivalents) or '(none)'}"
        )
    return "\n".join(lines)


def _system_prompt(rubric: Rubric, anonymized: bool = False, guidance: str = "") -> str:
    base = f"""\
You are an evidence-based CV reviewer. Your job is to rescue qualified candidates that a \
blunt keyword ATS would wrongly reject, WITHOUT inventing anything.

{_rubric_as_text(rubric)}

Rules, strictly:
- For every requirement above, return one entry with req_id set to its id.
- "quote" must be a VERBATIM span copied character-for-character from the candidate's CV \
text below. If nothing in the CV supports the requirement, set verdict "not_met" and quote \
to an empty string. Never paraphrase or invent a quote.
- Mark "transferable": true when the evidence is an equivalent skill/tool/title (not the \
literal keyword) that still satisfies the requirement.
- Never infer, mention, or reason about the candidate's age, generation, or how many years \
since graduation. Judge only whether the underlying skill is current and real.
- "bias_signals": separately flag anything in the CV text that a biased filter might \
penalize -- an employment gap, a graduation year, an unusual/non-linear career path, or \
age-coded phrasing -- each with the exact evidence span and, if the CV itself explains it \
(e.g. caregiving, a sabbatical), a one-line note of that explanation.
- "interview_questions": exactly 3 short, specific questions a recruiter should ask THIS \
candidate, targeting whichever requirements came back partial, not_met, or low-confidence.
"""
    base += guidance_prompt_block(guidance)
    if anonymized:
        base += """
This CV has been ANONYMIZED. Tokens such as [NAME], [YEAR], [DATE], [EMAIL], [PHONE] and \
[URL] are deliberate redactions, not part of the candidate's writing. Never mention them, \
never treat them as evidence of anything, and never report them as bias signals. Only report \
a bias signal when the CV's own words describe it (for example a stated career break or a \
non-linear career path); you cannot assess dates, so do not try.
"""
    return base


def score_candidate(
    rubric: Rubric, candidate: Candidate, anonymized: bool = False, guidance: str = ""
) -> CandidateScore:
    guidance = clean_guidance(guidance)
    raw: RawCandidateScore = get_or_compute(
        "score",
        RawCandidateScore,
        lambda: call_structured(
            model=MODEL_FAST,
            system=_system_prompt(rubric, anonymized, guidance),
            user_content=candidate.text,
            response_schema=RawCandidateScore,
            deterministic=True,
        ),
        rubric.model_dump_json(),
        candidate.id,
        candidate.text,
        "anonymized" if anonymized else "full",
        *([f"guidance:{guidance}"] if guidance else []),
    )
    return CandidateScore(
        candidate_id=candidate.id,
        requirements=[ScoredRequirement.model_validate(r.model_dump()) for r in raw.requirements],
        bias_signals=[BiasSignal.model_validate(b.model_dump()) for b in raw.bias_signals],
        interview_questions=list(raw.interview_questions[:3]),
    )
