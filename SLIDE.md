> **Superseded:** the real slide is `Relook_One_Pager.pptx` (its speaker notes hold the full Q&A sheet: baseline used, algorithm, pros/cons, corner cases, human-in-the-loop). This text is kept only for reference and is less complete.

# Slide content — Relook

*(Paste into a single slide. Keep it to headline + 4 sections; don't read it verbatim, use it as talking points.)*

---

## Relook
### Rescuing qualified people the keyword ATS rejected

**The problem**
Keyword-matching ATS software rejects real, qualified candidates whose experience is phrased differently — career changers, people returning after a gap, senior people whose old titles or tools predate today's buzzwords. Enterprises lose candidates they already paid to attract, and the pattern often correlates with age or career gaps (see *Mobley v. Workday*, an active age-discrimination case over exactly this).

**How it solves it**
- Paste a job description → Gemini extracts a rubric of *keywords* (what a blunt ATS searches for) vs *equivalents* (transferable skills the ATS misses).
- Every candidate is scored per-requirement with a **verbatim quote** as evidence — no quote, no credit.
- A code-level grounding check verifies every quote actually appears in the CV; unverified claims never count.
- Deterministic fit score (computed in Python, not asserted by the model) decides the shortlist.
- Rescued = baseline ATS rejected them, Relook shortlists them, with the evidence to show why.

**How AI is used**
- Gemini (`flash-lite-latest`) does two jobs only: (1) turn a JD into a structured rubric, (2) read one CV and return evidence quotes + bias signals + interview questions — always as schema-validated JSON, never free text.
- Everything a judge would call "the decision" — the fit score, the shortlist, the grounding check — is plain deterministic code, not the model. The model finds evidence; the code decides.

**Key technical choices**
- Runs entirely on a laptop with no GPU (Gemini API for reasoning, no local model).
- Structured output via `response_schema` (Pydantic) — zero JSON-parsing fragility.
- Disk cache by content hash so a live demo never re-pays for or re-waits on an already-seen (rubric, candidate) pair.
- Live eval on the synthetic demo pool (n=16, small): **5/7 (71%) hard-rescue recall, 0/6 false rescues, 66/67 (99%) claimed quotes verified in the CV text.** Reproducible: temperature 0, 112/112 verdicts identical across independent runs.

**What we'd build next**
- Live ATS connectors (Greenhouse/Lever/Workday) to re-screen real rejection queues.
- Outcome learning: rescued → hired → retained labels to calibrate the equivalence graph over time.
- Baton: an AI interviewer that captures a departing expert's undocumented knowledge before they leave — the enterprise-side sequel to this problem, fully scoped but not built today (one builder, one deadline).

**Assumptions stated up front**
Synthetic data only · PDF/DOCX/TXT CVs supported (text-based; scanned PDFs are skipped, no OCR) · small evaluation (n=16) · recommends a human second review, never auto-decides · bias flags are signals, not a legal audit.
