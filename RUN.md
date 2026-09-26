# Second Look — run guide & honest status

## Start it
```bash
cd /home/anand/Downloads/PitchFestBuild
.venv/bin/streamlit run ui.py          # http://localhost:8501
```
`.env` holds `GEMINI_API_KEY` (gitignored). `data/dataset.json` is the demo pool (1 JD + 16 synthetic CVs with planted ground truth). `data/cache/` holds every scored result, so a re-run of the demo pool is **instant and free**.

Regenerate the demo dataset (uses quota): `.venv/bin/python -m app.data_gen`

## What is built (vs the original spec in docs/01)
| ID | Requirement | Status |
|---|---|---|
| F1 | JD → rubric, **editable** (type, weight, keywords, equivalents) | Built + tested. Editing keywords changes the ATS baseline; edits invalidate results (stale-notice) |
| F2 | Ingest CVs as PDF / DOCX / TXT | Built + tested on real files. Scanned/image-only PDFs have no text layer: skipped with a warning (no OCR) |
| F3 | Keyword-ATS baseline, shows which rule fired | Built + tested |
| F4 | Per-requirement verdict with verbatim quote, verified in code | Built + tested |
| F5 | Rescued = ATS rejected, Second Look shortlists | Built + tested |
| F6 | Bias signals (gaps, non-linear careers, age-coded wording) | Built; tested on real flagged candidates |
| F7 | 3 interview questions per candidate | Built (rendered in candidate detail) |
| F8 | Rejection-pattern report per ATS rule | Built + tested |
| F9 | Export | **CSV only** (no PDF export) |
| F10 | Anonymized review | Built, opt-in, **best-effort** (see caveats) |
| F11 | Fresh synthetic pool from the UI | Built (sidebar button) |

## Measured results (demo pool, n=16: 7 hard-rescue cases, 6 unqualified, 3 easy passes)
- Hard-rescue recall **5/7 (71%)**, false rescues **0/6**.
- Quotes verified in the CV text: **66/67 (98.5%)**, shown as 99% in the UI. The one failure is a real example of the check working: the model joined two genuine sentences from the CV in the *wrong order*, so it wasn't verbatim and wasn't counted.
- **Reproducible:** temperature 0 + fixed seed. 112/112 verdicts identical across two independent runs; normal mode also reproduced the earlier session's shortlist exactly from fresh calls.
- The 2 hard-rescue candidates not recovered lack any evidence of performance-optimization work (a must-have), so the gate holds them back correctly.
- **Anonymized vs normal:** 106/112 (94.6%) verdicts agree; rescued sets overlap 4 of 5 (C05 in, C09 out); recall 5/7 and 0 false rescues in both. So anonymization does **not** leave the shortlist unchanged; the differences are borderline-verdict flips, not a systematic effect.
- Judge-input path proven through the real UI: an unrelated Data Analyst JD produced a different rubric and near-zero fit for the backend CVs.

## Things to say out loud (caveats)
1. **Small evaluation:** n=16, 7 hard cases, synthetic data written by an LLM. Recall 5/7 is indicative, not statistical proof. Synthetic CVs are also short and clean.
2. **Free-tier API limit (15 requests/min).** The app throttles itself to 12/min. A *fresh* 16-candidate run takes **~2 minutes**; cached runs are instant. Pre-run anything you plan to show. Enabling billing on the Gemini key removes this.
3. Anonymization is a heuristic scrub of names / contact details / dates in the text the *model* sees (the ATS baseline is unchanged). Free text can still identify someone; a bare 7-digit local phone number is only partly masked. Date-based bias signals can't fire in this mode.
4. The keyword baseline imitates a typical ATS knock-out filter; real ATS logic varies by vendor.
5. Recommends only; never auto-rejects or auto-hires. Bias flags are signals for a reviewer, not a legal audit.
6. Synthetic/public CVs only (hackathon rule).

## Demo flow (7 min)
1. JD is pre-filled → **Extract rubric** (cached, instant). Show `keywords` (what the ATS scans) vs `equivalents` (what it misses).
2. **Run Second Look** (cached) → two shortlists, 🟢 RESCUED badges, live eval line.
3. **Rejection pattern report**: one rule ("performance under heavy loads") rejected 13 candidates; 7 were genuinely qualified.
4. Open a rescued candidate: quotes, bias signals (caregiving break shown as *explained*), interview questions.
5. **Live edit:** add two synonyms to that rule's keywords → the ATS shortlist changes (3 → 6 when tested). Shows how brittle keyword lists are.
6. **Judge's turn:** paste any other JD → different rubric. (Fresh scoring ~2 min: pre-warm any JD you expect, or say so up front.)
7. Optional: upload a PDF/DOCX CV, tick **Anonymized review**, **Download CSV**.

## If the API hiccups
The app retries 503s with backoff and honors the server's "retry in Ns" on 429s. On a final failure it shows a message; click again — finished candidates are cached, only the failed one is retried.

## Layout
`ui.py` (Streamlit entrypoint, must stay at repo root) · `app/` (schemas, llm, cache, rubric_extract, rubric_edit, baseline, scorer, grounding, pipeline, ingest, anonymize, data_gen) · `slide_src/generate_slide.py` → `Second_Look_One_Pager.pptx` · `docs/` (planning specs). NOTE: a `baton/` package exists from a separate session; it is not covered or tested by this guide.
