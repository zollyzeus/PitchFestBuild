"""Code-level check that every quote the model claims as evidence actually
appears in the candidate's CV text. A score with no verifiable quote is never
allowed to count as 'met' -- this is what keeps the pipeline from hardcoding
or hallucinating its way to a good-looking demo."""
from __future__ import annotations

import difflib
import re

from app.schemas import CandidateScore


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


def is_grounded(quote: str, cv_text: str) -> bool:
    quote = quote.strip()
    if not quote:
        return False
    q, t = _normalize(quote), _normalize(cv_text)
    if q in t:
        return True
    # Near-verbatim fallback: the model paraphrased whitespace/punctuation
    # slightly. Require the longest common run to cover most of the quote.
    match = difflib.SequenceMatcher(None, q, t).find_longest_match(0, len(q), 0, len(t))
    return match.size >= max(12, int(0.85 * len(q)))


def apply_grounding(score: CandidateScore, cv_text: str) -> CandidateScore:
    for r in score.requirements:
        r.grounded = is_grounded(r.quote, cv_text)
    return score
