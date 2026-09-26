"""F10: best-effort anonymization of the CV text the *model* sees.

Removes names, contact details and dates/years so the scoring can be re-run 'blind'
to the usual age/identity proxies. This is a heuristic scrub, NOT a guarantee:
free text can still carry identifying details. The UI says so.
"""
from __future__ import annotations

import re

_NOISE_WORDS = {
    "resume", "cv", "curriculum", "vitae", "profile", "final", "updated", "new", "copy",
}
# Words that mark a heading line rather than a person's name.
_HEADING_WORDS = {
    "summary", "professional", "experience", "skills", "education", "objective", "contact",
    "work", "history", "employment", "projects", "certifications", "curriculum", "vitae",
    "resume", "profile", "about", "career", "technical", "engineer", "developer",
}

_URL = re.compile(r"(?:https?://\S+|www\.\S+|(?:linkedin|github)\.com/\S+)", re.I)
_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_PHONE = re.compile(r"(?<![\w.])\+?\d[\d\s().-]{7,}\d(?![\w])")
_MONTHS = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)
_MONTH_YEAR = re.compile(rf"\b{_MONTHS}\.?,?\s+(?:19|20)\d{{2}}\b", re.I)
_YEAR = re.compile(r"\b(?:19|20)\d{2}\b")


def _phone_sub(m: re.Match) -> str:
    # Only treat it as a phone number if it has enough digits; a bare date range like
    # "2019-2023" has 8 digits and must be left for the year rule.
    return "[PHONE]" if sum(ch.isdigit() for ch in m.group(0)) >= 10 else m.group(0)


def _name_tokens(name: str, text: str) -> set[str]:
    toks = {
        t for t in re.split(r"[\s_\-]+", name)
        if len(t) >= 3 and t.isalpha() and t.lower() not in _NOISE_WORDS
    }
    first = next((ln.strip() for ln in text.splitlines() if ln.strip()), "")
    words = first.replace(",", " ").split()
    looks_like_name = (
        2 <= len(words) <= 4
        and all(re.fullmatch(r"[A-Z][A-Za-z'’.-]+", w) for w in words)
        and not any(w.lower().strip(".") in _HEADING_WORDS for w in words)
    )
    if looks_like_name:
        toks |= {w.strip(".") for w in words if len(w.strip(".")) >= 3}
    return toks


def anonymize_text(text: str, name: str = "") -> str:
    out = _URL.sub("[URL]", text)
    out = _EMAIL.sub("[EMAIL]", out)
    out = _PHONE.sub(_phone_sub, out)
    out = _MONTH_YEAR.sub("[DATE]", out)
    out = _YEAR.sub("[YEAR]", out)
    for tok in sorted(_name_tokens(name, text), key=len, reverse=True):
        out = re.sub(rf"\b{re.escape(tok)}\b", "[NAME]", out, flags=re.I)
    return out
