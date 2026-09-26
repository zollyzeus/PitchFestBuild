# Relook — ATS Rejection Audit: Planning Doc

> **Status note:** this is the original plan. See [../RUN.md](../RUN.md) for what was actually built, measured results and known caveats. Deviations: LLM is Gemini (not Claude); UI is Streamlit; no rapidfuzz (stdlib difflib grounding); free-tier API limit means a fresh 16-CV run takes ~2 min, not the <90 s originally targeted for 30 CVs.

Sep 26, 2026 · @Anand

## Problem framing and assumptions

Relook re-screens the candidates a keyword ATS rejected and surfaces the qualified ones it missed, with cited evidence and bias flags. It is the employer-side answer to the problem Greyin exists for: senior talent filtered out by keyword software.

**Problem statement.** Enterprise talent teams run keyword and knock-out filters because they cannot read every CV. Those filters reject candidates whose experience is real but phrased differently: career changers, returners after a gap, senior people whose titles predate current buzzwords. The enterprise loses candidates it already paid to attract, lengthens time-to-hire, and carries legal exposure where a filter acts as an age or gap proxy.

**Brief questions it answers**

- Identify missed opportunities that are difficult for employees to spot manually (the rejected pile nobody reads).
- Help managers make faster, better decisions using unstructured data (CVs, job descriptions).
- Identify risks (screening patterns that correlate with age or career gaps).

**Assumptions to state at the demo**

1. The enterprise can export applicants and ATS outcomes as CSV or PDF CVs. Relook reads exports; it does not integrate with a live ATS in the prototype.
2. All CVs and job descriptions are synthetic, generated for the demo. No real personal data is used.
3. The keyword baseline imitates a typical ATS knock-out filter (required-keyword match plus a minimum-score threshold). Real ATS logic varies by vendor.
4. Relook recommends a human second review. It never auto-rejects or auto-hires anyone.
5. Bias flags are signals for a reviewer, not a legal bias audit.
6. Any Greyin code used must be public and disclosed; the prototype is built fresh during the challenge window.

## Users, journey and demo script

The primary user is a recruiter or talent-acquisition lead who owns a requisition with a large rejected pile. Hiring managers and HR compliance consume the output.

| User | Need | What Relook gives them |
| --- | --- | --- |
| Recruiter / TA lead | Find good candidates the filter dropped, without reading 200 CVs | A ranked "rescue list" with evidence quotes per requirement |
| Hiring manager | Trust the shortlist quickly | A one-screen card per candidate: fit score, evidence, open questions to ask |
| HR compliance / DEI | Know whether the filter behaves like an age or gap proxy | Rejection-pattern report: which rules removed which groups, with bias flags |

**Core journey**

1. Recruiter pastes or uploads a job description.
2. Relook extracts a requirements rubric (must-have, nice-to-have, each with acceptable evidence) and lets the recruiter edit it.
3. Recruiter uploads the applicant CVs plus ATS outcomes (or runs the built-in keyword baseline).
4. Each CV is scored against the rubric with quoted evidence; transferable skills are mapped to requirements.
5. The UI shows the ATS shortlist beside the Relook shortlist and highlights "rescued" candidates.
6. The recruiter opens a rescued candidate and sees evidence, gaps, bias flags and suggested interview questions.
7. A pattern report summarises which filter rules caused false rejections.

**7-minute demo script**

| Time | Beat | On screen |
| --- | --- | --- |
| 0:00-0:45 | The problem, one slide | Qualified people rejected by keyword filters, with the Greyin link (use only a sourced statistic) |
| 0:45-1:30 | Paste a job description; AI builds the rubric live | Editable rubric table |
| 1:30-3:00 | Run 30 synthetic CVs through the keyword filter and Relook | Two columns; rescued candidates highlighted |
| 3:00-4:30 | Open two rescued candidates: a career changer and a returner after a 3-year gap | Evidence quotes mapped to each requirement, bias flags, interview questions |
| 4:30-5:30 | Judge's turn: judge edits a requirement or pastes their own JD; rerun | Results change live, proving no hardcoding |
| 5:30-6:15 | Pattern report | "Rule 'must mention Kubernetes' removed 6 qualified candidates, 4 of them 45+ by inferred career length" |
| 6:15-7:00 | Architecture and what's next | Architecture diagram from this doc |

The judge-input beat is the most important: the brief penalises simulated intelligence, and a live rerun on the judge's input is the proof.

## Requirements

The prototype must do seven things live, on inputs the judge can change; everything else is stretch.

**Functional (must have for the demo)**

| ID | Requirement | Acceptance check |
| --- | --- | --- |
| F1 | Parse a job description into a structured rubric: must-haves, nice-to-haves, weight, acceptable evidence | Rubric appears in under 15 s and is editable |
| F2 | Ingest CVs as PDF, DOCX or pasted text; batch of at least 30 | 30 CVs parsed without manual fixes |
| F3 | Run a transparent keyword baseline that imitates an ATS knock-out filter | Shows which keyword rule rejected each candidate |
| F4 | Score every CV per rubric item with a verbatim evidence quote and a confidence | Every score cites a quote found in the CV text |
| F5 | Flag rescued candidates: rejected by the baseline, scored at or above the shortlist bar by Relook | Rescued list with reason in one line each |
| F6 | Detect bias signals: graduation year, total years, gaps, age-coded words, non-linear careers | Flags shown per candidate with the triggering text |
| F7 | Generate 3 targeted interview questions per rescued candidate to probe unverified requirements | Questions reference the candidate's own gaps |

**Functional (stretch)**

- F8 Rejection-pattern report across the batch: which rule removed how many qualified candidates, by segment.
- F9 Export shortlist and evidence as CSV or PDF for the hiring manager.
- F10 Anonymised review mode: hide name, dates and photo while scoring.
- F11 Synthetic data generator in the UI so judges can create a fresh candidate pool.

**Non-functional**

| Area | Requirement |
| --- | --- |
| Performance | 30 CVs scored in under 90 s using parallel calls; UI streams results as they arrive |
| Laptop fit | Runs on the i5-8250U / 8 GB laptop with under 1 GB RAM for the app; no local model |
| Grounding | A score with no verifiable quote is shown as "unverified", never as a pass |
| Explainability | Every number on screen can be expanded to the text that produced it |
| Privacy | Synthetic data only; API calls send CV text only, no names needed when anonymised mode is on |
| Resilience | Results cached to disk by content hash so a network drop during the demo does not blank the screen |
| Human in the loop | No automatic reject or advance action exists in the product |

## Proposed architecture

A single Python process runs a deterministic pipeline with three LLM steps; everything the model says passes a code-level grounding check before it reaches the screen.

*(Diagram: Relook pipeline — 9 components)*

The keyword baseline and the Evidence scorer see the same parsed CVs, so the side-by-side comparison is fair.

| Component | Responsibility | Implementation |
| --- | --- | --- |
| CV parser | Turn PDF/DOCX/text into clean text with section hints | pypdf, python-docx; plain-text fallback |
| Rubric extractor | JD to JSON rubric: requirement, type (must/nice), weight, evidence examples, synonyms | Sonnet 5, structured output; one call per JD |
| Keyword baseline | Imitate an ATS: required keywords, min years, knock-out rules; logs which rule fired | Pure Python, keywords taken from the rubric |
| Evidence scorer | Per CV: for each requirement return met / partial / not met, verbatim quote, transferable-skill reasoning, confidence | Haiku 4.5, parallel via asyncio, prompt-cached rubric |
| Grounding check | Reject any quote not found in the CV text (fuzzy ratio at least 90); downgrade to "unverified" | rapidfuzz |
| Bias signal check | Detect graduation years, total experience, gaps, age-coded words, non-linear careers; explain impact on baseline | Regex rules plus one LLM pass for context (for example gap explained as caregiving) |
| Rescue + report | Compute rescued set; write per-candidate summary, interview questions and batch pattern report | Sonnet 5, one call per rescued candidate plus one for the batch |
| Cache | Store every LLM result by hash of (prompt version, rubric, CV) | SQLite via sqlite3 |
| UI | Upload, rubric editing, streaming results, candidate cards | Streamlit |

## Tech stack and dependencies

Python only, with inference through the Claude API: the laptop (i5-8250U, 8 GB RAM, about 3 GB free, no GPU, no Node or Docker) cannot run a useful local model.

| Layer | Choice | Why |
| --- | --- | --- |
| Runtime | Python 3.12 via `uv` | System Python is 3.14; some wheels lag, so pin 3.12 in a uv venv |
| UI | Streamlit | Tables, file upload, expanders and streaming with no front-end build |
| LLM (reasoning) | Claude Sonnet 5 (`claude-sonnet-5`) | Rubric extraction, synthesis, pattern report |
| LLM (bulk) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Per-CV scoring at low latency and cost |
| Structured output | Pydantic models + tool/JSON-schema output | Schema-validated scores; retry once on invalid JSON |
| Concurrency | `asyncio` + `AsyncAnthropic`, semaphore of 8 | 30 CVs in parallel without rate-limit errors |
| Parsing | pypdf, python-docx | Pure Python, light on RAM |
| Grounding | rapidfuzz | Fast fuzzy quote matching |
| Storage | sqlite3 (standard library) | Cache and run history, zero setup |
| Synthetic data | Claude-generated CVs + Faker for names | Realistic variety, no real personal data |

**Install**

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install streamlit anthropic pydantic pypdf python-docx rapidfuzz pandas faker python-dotenv
```

**External dependencies and risks**

- Anthropic API key with enough rate limit for about 70 calls per run; set a spend cap.
- Venue wifi: pre-run the demo pool so the cache holds results; keep a phone hotspot and a recorded backup video.
- No other services, accounts or databases are required.

## AI design

The model reads for evidence, the code enforces it: every judgement the LLM makes must point at text that code can verify.

**Step 1: rubric extraction (Sonnet 5, once per JD).** Output schema:

```json
{"requirements": [{"id": "R1", "text": "Runs production Kubernetes clusters",
  "type": "must", "weight": 3,
  "evidence_examples": ["operated EKS/GKE", "container orchestration at scale"],
  "equivalents": ["Nomad", "ECS", "Mesos"], "min_years": null}]}
```

The `equivalents` list is what separates Relook from keyword matching: it encodes transferable evidence the JD never spelled out.

**Step 2: evidence scoring (Haiku 4.5, one call per CV).** The rubric sits in a cached system prompt; the CV is the user turn. Output per requirement:

```json
{"req_id": "R1", "verdict": "met|partial|not_met", "quote": "verbatim span from CV",
 "reasoning": "Ran 40-node Mesos cluster for 6 years; orchestration concepts transfer",
 "transferable": true, "confidence": 0.8}
```

Prompt rules: quote verbatim or return `not_met`; never infer age; judge recency of skills, not age of the person; ignore name, gender and photo cues.

**Step 3: grounding and scoring in code.** A quote that fuzzy-matches the CV below 90 is downgraded to unverified. Fit score = weighted sum over requirements (met = 1, partial = 0.5, transferable met = 0.8), must-haves gate the shortlist. Deterministic code, not the LLM, computes the number.

**Step 4: bias signals.** Regex finds graduation years, date ranges, gaps over 6 months and age-coded phrases ("digital native", "recent graduate", "25+ years"). An LLM pass classifies each gap's stated reason. The report shows whether the baseline's rejections correlate with these signals.

**Step 5: synthesis (Sonnet 5).** For rescued candidates only: a 3-sentence summary, the strongest evidence, the 3 interview questions targeting partial or unverified requirements. One batch call writes the pattern report from aggregated numbers computed in code.

**Evaluation, built on the day**

- Generate the synthetic pool with planted ground truth: 30 CVs labelled qualified / not qualified, with 8 qualified ones written to fail the keyword filter (synonyms, older titles, gaps).
- Metric 1: recall of planted qualified candidates (target 7 of 8 rescued).
- Metric 2: false rescues of planted unqualified candidates (target at most 1).
- Metric 3: grounding rate, the share of quotes verified in the CV text (target at least 95%).
- Show these three numbers on the slide: they turn "trust us" into a measured result.

**Guardrails**

- Temperature 0 for scoring; prompt version stored with every result.
- The model never sees the ATS outcome while scoring, so it cannot anchor on it.
- Every output is a recommendation for human review, stated in the UI.

## Technical and AI moat

The prompt is not the moat; the moat is the data loop and the position in the workflow: auditing the rejected pile, with verified evidence, fed by Greyin's senior-talent graph.

**Defensible today (in the prototype)**

1. **Rejected-pile position.** Incumbents rank applicants going forward. Relook audits decisions already made, a slot nobody owns and the one compliance teams care about.
2. **Evidence grounding in code.** Scores are computed from verified quotes, not from model opinion. That makes output auditable, which is what a bias-audit or AI-regulation reviewer asks for.
3. **Counterfactual comparison.** Showing baseline versus evidence-based decisions per rule is itself the audit artefact; ranking tools do not produce it.

**Defensible over time (with Greyin)**

1. **Transferable-skill equivalence graph.** Every recruiter edit to a rubric's `equivalents`, and every rescued candidate who is later hired, teaches which old skills map to which new ones (Mesos to Kubernetes, mainframe batch to data pipelines). This proprietary graph compounds per role family.
2. **Outcome labels.** Rescued-then-hired-then-retained is a label no keyword ATS collects. It lets Relook calibrate scores against real performance, not CV wording.
3. **Verified-evidence supply.** Greyin's Verified Expert status (earned via FlexPro, StackWorks and GreyMatters work) is external evidence a CV cannot fake. Relook can pull it in as a stronger signal than self-reported text.
4. **Two-sided flywheel.** Enterprises that use Relook see rescued senior candidates; those candidates are routed to Greyin's DeepEdge pool; a larger pool makes DeepEdge more valuable to the same enterprises.
5. **Compliance workflow lock-in.** Once audit reports feed HR's regulatory evidence (for example NYC Local Law 144 bias audits or EU AI Act high-risk obligations for hiring tools), switching means redoing the audit trail.

## Competitive landscape and differentiation

Incumbents either rank candidates going forward or audit tools statistically; none of the products reviewed re-reads individual rejected candidates, and the bias audit reviewed does not cover age. Relook fills both gaps.

| Product | What it does | Gap Relook fills |
| --- | --- | --- |
| [Workday Recruiting with HiredScore](https://www.workday.com/en-us/products/talent-management/ai-recruiting.html) | AI candidate grading and talent rediscovery from existing databases, inside Workday | Rediscovery aims at future openings; it does not audit why a specific rejection happened. It is also the vendor named in the age-discrimination case below |
| [Eightfold AI](https://eightfold.ai/) | Talent intelligence: skills inference, matching, AI interviewer; sold to Fortune 500 | Ranks and matches; an enterprise platform replacement, not a light audit over an existing ATS |
| [Warden AI](https://www.warden-ai.com/nyc-local-law-144) | Independent NYC Local Law 144 bias audits: selection-rate and impact-ratio statistics by race, ethnicity and sex | Aggregate statistics only, no age attribute, no per-candidate evidence or rescue |
| Holistic AI and similar AI-governance platforms | Bias-audit reports for LL144 compliance ([Warden and Holistic AI both surfaced in LL144 search](https://www.warden-ai.com/resources/nyc-bias-audit)) | Same: compliance reporting, not candidate recovery |
| Manual false-negative sampling | Guides recommend to "sample rejected candidates to estimate missed qualified candidates" ([MiHCM](https://mihcm.com/resources/blog/resume-screening-in-2026-a-guide-to-ai-powered-screening-ats-integration-bias-governance/)) | Relook automates this practice across the whole rejected pile, not a sample |

**Why now.** In [Mobley v. Workday](https://www.maynardnexsen.com/publication-emerging-liability-for-ai-driven-hiring-tools-key-developments-in-mobley-v-workday-inc), the court conditionally certified an age-discrimination (ADEA, 40+) collective on May 16, 2025. The alleged proxies are exactly what Relook flags: employment gaps, years of experience, educational background. California, Illinois, Colorado and Texas have AI hiring laws, so employers face exposure in several jurisdictions.

**Positioning in one line.** Relook is an evidence-based second reader that sits beside any ATS, recovers qualified people the filter dropped, and produces the per-candidate audit trail compliance needs, with age and career gaps in scope.

**Differentiators to say out loud**

1. Works on exports from any ATS; no platform replacement.
2. Per-candidate, quote-backed evidence, not a black-box grade.
3. Covers age and gap proxies, which LL144-style audits leave out.
4. Connects to Greyin's verified senior-talent pool, a supply no ATS vendor has.

## Build plan, risks and next steps

**Feasibility check: one builder, one idea.** A solo builder cannot take both Relook and Baton to a demoable state in one day; committing fully to Relook is the plan (see the [Baton doc](https://claude.ai/artifact/A5Dxf4SZjbNH6u8G4DFXBQ) note below on why it's parked, not built, today). The schedule below assumes a 9:30 am start, one person, and a hard stop for coding at 4:00 pm so the last 90 minutes go to the slide, rehearsal and a backup video before the 5:30 pm demo.

| Time | Block | Task | Exit check |
| --- | --- | --- | --- |
| 9:30-9:50 | Setup | uv venv (Python 3.12), install deps, verify API key, repo skeleton, SQLite schema | `streamlit run app.py` shows an empty page |
| 9:50-10:30 | Data | Generate 3 JDs, 30 synthetic CVs with planted ground truth (8 hard rescues), via Claude | CVs saved as files, ground-truth CSV written |
| 10:30-11:10 | Baseline | CV/JD parsers (pypdf, python-docx), keyword baseline that imitates an ATS knock-out filter | Baseline shortlist reproducible from CLI |
| 11:10-12:10 | Core AI (1) | Pydantic schemas, rubric extractor, evidence scorer with parallel calls | One CV scored end to end with a real quote |
| 12:10-12:40 | Break | Food, stretch, re-read the demo script | — |
| 12:40-13:10 | Core AI (2) | Grounding check (rapidfuzz), fit scoring, rescued-set logic | Rescued list differs visibly from the baseline |
| 13:10-14:10 | UI (1) | Streamlit: upload, editable rubric, two-column shortlist | Full pipeline runs from the UI on 30 CVs |
| 14:10-14:50 | UI (2) | Candidate card: evidence, bias flags, interview questions | One rescued candidate's card looks demo-ready |
| 14:50-15:20 | Evaluation | Run the recall / false-rescue / grounding-rate script; capture the three numbers | Numbers exist and are defensible |
| 15:20-16:00 | Buffer | Bug fixes and prompt tuning against the eval failures; F8 pattern report only if ahead of schedule | Core F1-F7 all work without a crash |
| 16:00-16:30 | Slide | The one slide: problem, AI approach, key technical choices, eval numbers, what's next | Slide done, no more edits after this |
| 16:30-16:50 | Rehearse | Run the 7-minute script twice against a timer, alone | Finishes at or under 7:00 both times |
| 16:50-17:05 | Backup | Warm the cache on the demo pool; record a full backup run on video | Video plays back cleanly |
| 17:05-17:20 | Ship | Final commit, upload code to the submission link | Link confirmed working |
| 17:20-17:30 | Buffer | Walk to the judge table, breathe | — |

**Checkpoints, not a switch:** if the 11:10 or 13:10 exit checks are missed, cut scope further (drop F6/F7/F8, keep only the rescue comparison) rather than switching ideas — a half-built Relook beats two unfinished ones.

**Risks and mitigations**

| Risk | Mitigation |
| --- | --- |
| Rate limits or slow API during the demo | Semaphore of 8, disk cache, pre-warmed demo pool; live rerun only for the judge's input |
| Model invents evidence | Code-level quote verification; unverified never counts as met |
| Judges read it as a bias tool that itself discriminates | Model never infers age; flags describe the filter's behaviour, a human decides |
| Python 3.14 package incompatibility | uv venv with Python 3.12, set up before the event |
| Scope creep | F1 to F7 only until 3:30 pm; F8 onward is stretch |

**What we would build next (for the slide)**

1. Live ATS connectors (Greenhouse, Lever, Workday) that re-screen rejections nightly.
2. Greyin Verified Expert evidence as an input signal alongside the CV.
3. Outcome learning: rescued, hired and retained labels to calibrate scores and grow the equivalence graph.
4. Compliance pack: impact ratios by inferred age band and gap status, exportable for audit files.
5. Candidate-side feedback: tell rescued candidates what evidence was missing, routed through Greyin.
6. Baton (the departing-expert knowledge handover concept, parked today for lack of a second builder) as the next enterprise problem to prototype.

## Sources

- [Workday AI recruiting (HiredScore)](https://www.workday.com/en-us/products/talent-management/ai-recruiting.html)
- [Eightfold AI](https://eightfold.ai/)
- [Warden AI: NYC Local Law 144](https://www.warden-ai.com/nyc-local-law-144)
- [Warden AI: NYC bias audit guide](https://www.warden-ai.com/resources/nyc-bias-audit)
- [MiHCM: resume screening in 2026](https://mihcm.com/resources/blog/resume-screening-in-2026-a-guide-to-ai-powered-screening-ats-integration-bias-governance/)
- [Maynard Nexsen: Mobley v. Workday developments](https://www.maynardnexsen.com/publication-emerging-liability-for-ai-driven-hiring-tools-key-developments-in-mobley-v-workday-inc)
- [Greyin](https://www.greyin.net) and [DeepEdge](https://deepedge.greyin.net)
