# Baton — Departing-Expert Knowledge Handover: Planning Doc

Sep 26, 2026 · @Anand

**Status: rebuilt as a corporate knowledge-transfer (KT) workflow, on Gemini.** The page `pages/2_Baton.py` (code in `baton/kt_*.py`) supersedes the departing-expert design described below; the earlier document-interview prototype is kept at `pages/3_Baton_Doc_Interview.py`. The sections below are the earlier design and are not updated.

**KT workflow (as built)**
1. **Brief (project manager):** project description, duration, roles and responsibilities, tech stack, dev and test environment, extra prompts, KT giver and taker, target readiness (default 80%).
2. **Independent Q&A:** Gemini writes one giver question and one taker question for each of 12 KT angles (architecture, code, environments, CI/CD, testing, data, incidents, business context, security, in-flight work, tribal knowledge, documentation). Giver and taker answer in separate views and never see each other's answers. If round 1 leaves weak angles, round 2 asks sharper follow-ups on those only.
3. **Assessment:** each angle is covered, partial or gap by comparing both sides, with a mismatch flag. Evidence quotes are checked in code; no verifiable quote from both sides means no "covered". Readiness is a weighted share of the 12 angles.
4. **Action items:** gaps become actions for the giver or the taker with severity and due date. Each owner responds with proof ("addressed") or a justification to ignore.
5. **Review and decision:** Gemini reviews responses; code applies the rule. Close if every action is accepted and readiness meets the target. Otherwise keep open for one redress round (rejected items return to their owner with the reviewer's note). Still unresolved: escalate to the manager. The manager can override with a note.
6. **Tracker:** per KT stage, day n of N, deadline, days left, overdue, who it is waiting on, open actions, readiness, time in stage; plus an action list across all KTs.

**Measured (one run, simulated giver and taker with 4 planted weak angles, synthetic project):** 4/4 planted weaknesses flagged in the first assessment; 0 of 8 other angles flagged as hard gaps; readiness 57% then 66% (after round 2), 95% and 97% (after action-item reviews); 6/6 actions accepted; closed after one redress round; 69 seconds end to end. The personas are cooperative by construction, so this shows the loop works, not how real people behave.

**5 KTs seeded in `data/kt/` for the demo,** covering every real branch of the decision rule: Q&A round 1 in progress (Claims Portal Frontend), mid action-items (Data Lake Ingestion), closed on the first pass (Fraud Alerts Notification Service), closed after one redress round (Payments Reconciliation Service), and escalated after a redress round when the taker kept justifying gaps away instead of closing them (Legacy Mainframe Batch Interface). See [demo-7min.md](demo-7min.md) for the pitch script built around these.

**Run:** `.venv/bin/streamlit run Relook.py`, open Baton. Eval: `.venv/bin/python -m baton.kt_eval`. Slides: `slide_src/generate_baton_slide.py`.

## Problem framing and assumptions

Baton is an AI interviewer that captures what a departing senior employee knows, checks it against their documents, and hands the successor a structured handover plus a Q&A assistant grounded in it. It is the enterprise-side version of Greyin's story: when experienced people are restructured out or retire, their knowledge leaves with them.

**Problem statement.** Senior employees hold undocumented knowledge: why a system is configured a certain way, which vendor contact actually fixes things, which monthly report breaks and how. Exits are usually short (two to four weeks), handover notes are written in a rush, and successors are left with a folder of documents and no context. The cost shows up months later as incidents, repeated mistakes and slow ramp-up.

**Brief questions it answers**

- Help employees find, understand and act on information spread across documents and people.
- Convert meetings (an interview) and documents into clear actions, decisions and workflows.
- Improve coordination across teams during role transitions.
- Identify risks: single points of failure and knowledge that exists in only one head.

**Assumptions to state at the demo**

1. The departing employee is cooperative and gives 2 to 3 interview sessions of about 30 minutes each.
2. The interview runs in text in the prototype; voice input is stretch.
3. The employee uploads their own working documents (runbooks, emails exported as text, spreadsheets). No live access to email, Slack or Confluence in the prototype.
4. All documents and personas are synthetic, for example a retiring finance operations manager who owns the month-end close.
5. The departing employee reviews and approves the handover before the successor sees it.
6. Any Greyin code used must be public and disclosed; the prototype is built fresh during the challenge window.

## Users, journey and demo script

Three people touch Baton: the expert who leaves, the successor who inherits, and the manager who needs to know what is at risk.

| User | Need | What Baton gives them |
| --- | --- | --- |
| Departing expert | Hand over well without writing a 40-page document | A guided interview that asks only what their documents don't already answer |
| Successor | Know what to do in week 1, and ask "why" later | Structured handover (duties, calendar, systems, contacts, known issues, decisions) plus a cited Q&A assistant |
| Manager / HR | See knowledge risk before the last day | Coverage map: what is documented, what was only in the person's head, what is still unknown |

**Core journey**

1. Manager starts a handover: role, departure date, successor.
2. The expert uploads documents; Baton builds a draft knowledge map (duties, systems, recurring tasks, people) from them.
3. Baton finds gaps: tasks with no runbook, systems with no owner, contradictions between documents, dates that fall after the departure.
4. The interview agent asks targeted questions about those gaps, one at a time, and follows up on vague answers.
5. Each answer is written into the handover with its source (interview turn or document) and confidence.
6. The expert reviews and approves; the manager sees the coverage score and remaining risks.
7. The successor gets the handover and asks the Q&A assistant questions; every answer cites the doc or the interview quote.

**7-minute demo script**

| Time | Beat | On screen |
| --- | --- | --- |
| 0:00-0:45 | The problem, one slide | A retiring finance ops manager, 3 weeks' notice, owns month-end close |
| 0:45-1:45 | Upload 6 synthetic documents; knowledge map builds live | Duties, systems and people extracted, with gaps marked red |
| 1:45-3:30 | Interview: Baton asks about a gap ("The close checklist skips step 7 in March; why?"); presenter answers vaguely; Baton follows up | Chat plus the handover section updating as answers arrive |
| 3:30-4:30 | Coverage view | Coverage before and after the interview (computed live), plus open risks listed |
| 4:30-5:45 | Judge's turn: judge types a successor question; Baton answers with citations, or says it doesn't know and logs it as a gap | Q&A with source chips |
| 5:45-6:15 | Export | Handover document and a 30-60-90 day plan for the successor |
| 6:15-7:00 | Architecture and what's next | Diagram from this doc |

The honest "I don't know, logged as a gap" answer is a strength in the demo: it proves the assistant is grounded, not bluffing.

## Requirements

The prototype must do eight things live; the interview must visibly adapt to the answers it gets.

**Functional (must have for the demo)**

| ID | Requirement | Acceptance check |
| --- | --- | --- |
| F1 | Ingest PDF, DOCX, XLSX/CSV, TXT and exported emails (.eml or text) | 6 synthetic documents ingested and chunked |
| F2 | Extract a knowledge map: duties, recurring tasks with cadence, systems, people and vendors, decisions | Map shown as a table with source links per item |
| F3 | Detect gaps: undocumented tasks, missing owners, contradictions between documents, commitments after the last day | At least 5 gaps, each with its evidence |
| F4 | Run an adaptive interview: prioritise gaps by risk, ask one question at a time, follow up on vague answers, stop when the gap is closed | A vague answer triggers a follow-up; a clear one closes the gap |
| F5 | Write answers into a structured handover with source (document chunk or interview turn) and confidence | Every handover line has a source chip |
| F6 | Show a coverage score and remaining risks, recomputed after each answer | Score changes during the demo |
| F7 | Successor Q&A grounded only in the handover, documents and interview transcript, with citations; refuses and logs a gap when unsupported | Unsupported question returns "not captured" and appears in the gap list |
| F8 | Export the handover as Markdown/PDF with a 30-60-90 day plan for the successor | File downloads |

**Functional (stretch)**

- F9 Voice interview: speech-to-text for answers.
- F10 Handover approval flow: the expert edits and signs off before release.
- F11 Single-point-of-failure view across several departing people in one team.
- F12 Calendar import (.ics) to detect recurring duties automatically.

**Non-functional**

| Area | Requirement |
| --- | --- |
| Latency | Interview question in under 6 s; Q&A answer in under 8 s |
| Laptop fit | Under 1.5 GB RAM including local embeddings; no local LLM |
| Grounding | Every Q&A answer cites at least one chunk or interview turn; no citation means no answer |
| Privacy | Synthetic data only; per-handover data stored locally in SQLite; delete-on-request |
| Resilience | Sessions persist to disk so a browser refresh or crash does not lose the interview |
| Consent | The expert sees and approves everything attributed to them |

## Proposed architecture

A single Python process with a loop at its centre: documents seed a knowledge map, gaps drive the interview, answers fill the handover, and the handover is re-checked for new gaps.

*(Diagram: Baton pipeline — 9 components, one interview loop)*

The successor Q&A reads both the document chunks and the handover store, so it can cite either an original document or an interview answer.

| Component | Responsibility | Implementation |
| --- | --- | --- |
| Ingest + index | Parse files, chunk (about 800 tokens with overlap), embed, full-text index | pypdf, python-docx, openpyxl, email stdlib; fastembed (bge-small, ONNX, CPU); SQLite FTS5 for keyword search |
| Knowledge mapper | Extract duties, cadence, systems, people, vendors, decisions with source chunk ids | Sonnet 5, structured output, map-reduce over chunks |
| Gap detector | Rules: task with no runbook, system with no owner, date after last day. LLM: contradictions between documents, vague steps | Python rules plus one Sonnet 5 pass |
| Interview agent | Pick the highest-risk open gap, ask one question, judge the answer (closed / vague / new gap), follow up or move on | Sonnet 5 with tool calls: `record_answer`, `open_gap`, `close_gap` |
| Handover store | Versioned handover sections, each line with source and confidence | SQLite tables: items, sources, gaps, turns |
| Coverage + risks | Share of duties with a runbook-level answer, weighted by criticality and frequency; list of open risks | Deterministic Python |
| Successor Q&A | Hybrid retrieval (embeddings plus FTS5), answer with citations, refuse when unsupported and log a gap | Haiku 4.5 for answers, citation check in code |
| Export | Handover document and a 30-60-90 day plan | Sonnet 5 plus Markdown to PDF |
| UI | Four views: setup, interview chat, handover, successor Q&A | Streamlit with `st.chat_message` |

## Tech stack and dependencies

Python with the Claude API for reasoning and a small CPU embedding model for retrieval; this fits the i5-8250U / 8 GB laptop, where about 3 GB is free.

| Layer | Choice | Why |
| --- | --- | --- |
| Runtime | Python 3.12 via `uv` | System Python is 3.14; pin 3.12 so onnxruntime and other wheels install cleanly |
| UI | Streamlit (`st.chat_message`, `st.chat_input`, tabs) | Chat and tables with no front-end build |
| LLM (reasoning) | Claude Sonnet 5 (`claude-sonnet-5`) | Mapping, gap detection, the interview agent, export |
| LLM (fast) | Claude Haiku 4.5 (`claude-haiku-4-5-20251001`) | Successor Q&A answers and answer classification |
| Embeddings | fastembed with `BAAI/bge-small-en-v1.5` (ONNX, about 130 MB, CPU) | Local, no PyTorch; about 1 second per page batch on this CPU (to verify on setup) |
| Keyword search | SQLite FTS5 (standard library) | Exact names, codes and vendor terms that embeddings miss |
| Vector search | NumPy cosine over a few thousand chunks | No vector database needed at demo scale |
| Parsing | pypdf, python-docx, openpyxl, `email` stdlib | Covers runbooks, sheets and exported mail |
| Structured output | Pydantic + tool use | Interview agent actions are tool calls, validated in code |
| Export | Markdown, then PDF via `markdown` + `weasyprint` or browser print | Handover and 30-60-90 plan |
| Speech (stretch) | Browser recording plus a cloud speech-to-text API | Local Whisper is too slow on this CPU |

**Install**

```bash
uv venv --python 3.12 && source .venv/bin/activate
uv pip install streamlit anthropic pydantic fastembed numpy pypdf python-docx openpyxl markdown python-dotenv
```

**External dependencies and risks**

- Anthropic API key and spend cap; an interview session is about 20 to 40 calls.
- The fastembed model downloads on first run: download it before the event.
- Venue wifi: the interview needs the API, so keep a phone hotspot and a recorded backup video.

## AI design

The interview is document-led: Baton asks only about what the documents leave out, which keeps sessions short and makes every question visibly specific to this person.

**Step 1: knowledge map (Sonnet 5, map-reduce).** Each chunk batch yields items; a reduce pass merges duplicates. Item schema:

```json
{"id": "D4", "kind": "duty|system|person|vendor|decision|recurring_task",
 "title": "Month-end accruals review", "cadence": "monthly, working day 3",
 "criticality": "high", "sources": ["chunk:close_checklist.xlsx#12"],
 "known": {"what": true, "how": false, "why": false, "who": true}}
```

The `known` flags are the core idea: a duty is covered only when what, how, why and who are all answered.

**Step 2: gap detection.** Code creates a gap for every false `known` flag, every system with no owner and every date after the last working day. One Sonnet 5 pass finds contradictions between documents and vague steps ("fix the feed if it breaks"). Gap priority = criticality x frequency x (1 if no other employee is named on it, else 0.5).

**Step 3: interview agent loop (Sonnet 5 with tools).**

1. Pick the top open gap; ask one question that quotes the evidence ("Your checklist says 'adjust FX if needed' on day 3; how do you decide it's needed?").
2. Classify the answer: `closes_gap`, `vague` (ask a follow-up for a threshold, example or name), `new_gap` (answer mentions an unknown system or person), or `skip` (the expert doesn't know).
3. Call `record_answer(item_id, field, text, turn_id)` and `close_gap` or `open_gap` as tools; code updates the store and coverage.
4. Stop a thread after 2 follow-ups; cap a session at about 25 questions.

**Step 4: successor Q&A (Haiku 4.5).** Hybrid retrieval of the top 8 chunks or handover items, then an answer that must cite ids. Code checks every cited id was retrieved. No valid citation means the answer is replaced by "Not captured in the handover" and a gap is logged for the expert, while they are still around.

**Step 5: export (Sonnet 5).** Handover document by section, plus a 30-60-90 day plan ordered by upcoming cadence dates and criticality.

**Evaluation, built on the day**

- Synthetic scenario with planted truth: 6 documents for a retiring finance ops manager, 10 hidden facts known only to a scripted "expert" persona (a second Claude instance answering from a fact sheet).
- Metric 1: gap recall, the share of the 10 hidden facts Baton asks about (target at least 8).
- Metric 2: questions per fact captured (target at most 2).
- Metric 3: Q&A faithfulness on 15 successor questions: correct and cited, or correctly refused (target at least 13 of 15).
- The scripted expert lets you run the full evaluation unattended and show the numbers on the slide.

**Guardrails**

- The agent never invents procedures; it only records what the expert says or the documents state.
- Personal opinions about colleagues are out of scope and are not stored.
- The expert approves the handover before release.

## Technical and AI moat

Search tools find what is written down; Baton's moat is capturing what is not, at the one moment it can still be captured, and turning that into a measured coverage number.

**Defensible today (in the prototype)**

1. **Gap-first interviewing.** Questions come from the difference between the knowledge map and the documents, not a generic exit questionnaire. That needs the what/how/why/who model per duty, not a chatbot prompt.
2. **Measured coverage.** A deterministic coverage score and risk list give managers a number to act on before the last day. Enterprise search and wikis cannot tell you what is missing.
3. **Refuse-and-route Q&A.** Unanswerable successor questions become gaps sent back to the expert while they are still employed, closing the loop that ordinary RAG leaves open.

**Defensible over time (with Greyin)**

1. **Role-family question banks.** Every interview teaches which gaps matter for a role type (finance close, SRE on-call, plant maintenance). New handovers start with a better map; this compounds with usage.
2. **Alumni expert channel.** Greyin's FlexPro can offer the departed expert paid follow-up hours when a successor hits a gap. That turns an exit into a fractional engagement, a supply no knowledge-management vendor has.
3. **Restructuring timing.** Greyin already sits with senior people at the moment of redundancy or retirement; Baton gives the employer a reason to bring Greyin in at that moment.
4. **Handover as an audit artefact.** Regulated functions (finance, safety, IT operations) need evidence of controlled handover; a sourced, approved record becomes part of the control environment and is sticky.

## Competitive landscape and differentiation

The closest competitor, Exit Insights, analyses artifacts without the employee and hands you an interview guide to run yourself. Baton runs that interview with AI, driven by the gaps, and measures coverage. Enterprise search and knowledge bases only index what is already written.

| Product | What it does | Gap Baton fills |
| --- | --- | --- |
| [Exit Insights](https://www.exit-insights.com/) | Analyses a leaver's documents, chat, email and calendar exports; produces 11 documents including a knowledge transfer package, relationship map, interview guide and first-30-days plan; "the departing employee need\[s\] not participate" | Artifact-only: what was never written stays uncaptured. The interview guide is for a manual session; Baton runs the adaptive interview itself and closes gaps live |
| [Glean](https://www.glean.com/solutions/knowledge-management) | Enterprise AI search across connected apps, collections, verification and deprecation of documents | Indexes existing content; no capture of undocumented knowledge and no gap detection per role |
| [Guru](https://www.getguru.com/reference/what-is-glean-ai) | "AI Source of Truth": SME-verified knowledge, cited answers in Slack/Teams | Assumes SMEs write and verify cards; no exit workflow or interview |
| [JoySuite](https://www.joysuite.com/blog/capture-expert-knowledge-before-leave/) | Virtual experts, knowledge assistant, course studio over captured materials | Organises and retrieves what was captured; does not run the capture interview or detect gaps |
| Manual exit interviews and handover templates | HR questionnaire plus a handover document written by the leaver | Generic questions, no link to the person's documents, no coverage measure |

**Why now.** JoySuite cites a Panopto report that up to 42% of the knowledge a long-tenured employee's role needs exists only in their head ([JoySuite, citing Panopto 2018](https://www.joysuite.com/blog/capture-expert-knowledge-before-leave/)). Restructuring and retirement waves make the exit window the last chance to capture it.

**Positioning in one line.** Baton is the AI interviewer for the last three weeks: it reads the leaver's documents, asks only what they leave out, and hands the successor a sourced handover and an assistant that knows its limits.

**Differentiators to say out loud**

1. Gap-driven adaptive interview, not artifact analysis alone and not a static questionnaire.
2. A coverage score and risk list the manager sees before the last day.
3. Successor Q&A that refuses without evidence and routes the question back to the expert.
4. Greyin tie-in: the departed expert can stay reachable as a paid fractional advisor through FlexPro.

## Build plan, risks and next steps

*(Reference schedule below, for if Baton is picked up on a future two-person build — not the plan for this event.)*

The interview loop is the demo, so it gets built first and working by 1:00 pm; the schedule assumes a 9:30 am start, two people and a 5:30 pm demo.

| Time | Person A (backend and AI) | Person B (data, UI, slide) |
| --- | --- | --- |
| 9:30-10:30 | Skeleton, API client, SQLite schema, Pydantic models | Synthetic scenario: 6 documents, a fact sheet of 10 hidden facts, 15 successor questions |
| 10:30-12:00 | Ingest, chunk, embeddings plus FTS5; knowledge mapper | Streamlit layout: setup, chat, handover, Q&A tabs |
| 12:00-13:00 | Gap detector and interview agent with tool calls | Handover view with source chips; coverage widget |
| 13:00-14:30 | Answer classification, follow-ups, coverage scoring | Scripted-expert persona for testing and evaluation |
| 14:30-15:30 | Successor Q&A with citation check and refuse-and-route | Export: handover document and 30-60-90 plan |
| 15:30-16:30 | Run the evaluation, tune prompts | The one slide with evaluation numbers; rehearse twice |
| 16:30-17:15 | Freeze; record backup video | Upload code to the submission link |

**Risks and mitigations**

| Risk | Mitigation |
| --- | --- |
| Interview feels generic | Every question must quote a document span or a gap id; reject and regenerate questions without one |
| Interview latency over 6 s | Stream the question text; use Haiku 4.5 for answer classification |
| Embedding model slow or RAM-heavy on this laptop | bge-small only; fall back to FTS5 keyword search alone |
| Live demo answers go off-script | The agent handles vague answers by design; rehearse one vague and one clear answer |
| Judges question privacy of exit interviews | State the consent and approval assumptions; synthetic data only |

**What we would build next (for the slide)**

1. Live connectors (Microsoft 365, Google Workspace, Slack, Jira) to build the knowledge map automatically.
2. Voice interview with speech-to-text and meeting-style sessions.
3. Team-level single-point-of-failure radar before anyone resigns.
4. Alumni expert channel via Greyin FlexPro for paid follow-up questions.
5. Role-family question banks learned across handovers.

## Sources

- [Exit Insights](https://www.exit-insights.com/)
- [Glean: knowledge management](https://www.glean.com/solutions/knowledge-management)
- [Guru: AI Source of Truth](https://www.getguru.com/reference/what-is-glean-ai)
- [JoySuite: capture expert knowledge before employees leave](https://www.joysuite.com/blog/capture-expert-knowledge-before-leave/)
- [Greyin](https://www.greyin.net) and [FlexPro](https://flexpro.greyin.net)
