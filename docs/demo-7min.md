# 7-minute combined demo: Relook + Baton

Both prototypes run on Gemini `flash-lite-latest`, free tier, **500 requests/model/day**. That cap was hit once already today from testing; a fresh key is now in `.env`. Budget accordingly — see "Quota safety" at the end before you go on stage.

**Start both apps before the room fills up:**
```bash
.venv/bin/streamlit run Relook.py   # Relook (renamed from Second Look), sidebar also lists the Baton pages
```
Streamlit's sidebar shows all three pages: Relook, Baton (2), Baton_Doc_Interview (3) — hide the third from the nav if you don't want questions about it (`.streamlit/config.toml` → `[client] showSidebarNavigation = false`, or just don't click it).

## Timeline

| Time | Beat | Screen | New API calls? |
|---|---|---|---|
| 0:00–0:20 | Hook | One line: "Two places good people and good decisions get lost: hiring, and the day someone leaves." | none |
| 0:20–2:30 | **Relook** | JD pre-filled → Extract rubric → Run on all 16 candidates → point at rescued badges + live eval line → open one rescued candidate's evidence | **0** (fully cached) |
| 2:30–2:45 | Transition | "Relook fixes a decision. Baton makes sure the next one is even needed — did the knowledge actually transfer?" | none |
| 2:45–3:45 | **Baton: Manager tracker** | Open Baton → Manager → Tracker tab. 5 KTs already at every real stage: Q&A round 1, action items, closed on the first pass, closed after a redress round, escalated. Point at Waiting-on, Days left, Open actions columns. | **0** |
| 3:45–5:15 | **Baton: live Q&A** | Switch sidebar to "KT taker" → pick **Claims Portal Frontend** → answer 3–4 of the 12 round-1 questions live (giver's side is already answered) → Submit → flip back to Manager tracker, show the stage/readiness just moved | **~2–3 calls** (assessment, maybe round 2 questions) |
| 5:15–6:15 | **Baton: gaps → action → decision** | Manager → KT detail → **Data Lake Ingestion** (mid action-items) or **Legacy Mainframe Batch Interface** (escalated): show the angle assessment table, one action item with a rejected justification, and the decision note explaining why it escalated | **0** (all pre-seeded) |
| 6:15–6:45 | Judge's turn | Let a judge type a successor-style question as KT taker, or pick which KT to open — their choice proves it isn't a fixed script | **0–1 calls** |
| 6:45–7:00 | Close | One slide: what's next for both ideas, the ask | none |

## Why this order
- Relook goes first because it is fully rehearsed and zero-risk: everything is cached, so it cannot fail on stage even with no wifi.
- Baton's tracker (3:45) is shown before any live typing, so the judges see the full lifecycle before watching one KT move through it live.
- The one live-typing moment (3:45–5:15) is the only segment that spends quota. Keep it short: 3–4 answers is enough to trigger a visible state change.

## The 5 seeded KTs (`data/kt/`) and what each proves

| KT | Stage | Shows |
|---|---|---|
| Claims Portal Frontend | Q&A round 1 (taker not yet answered) | The independent-answer moment, live |
| Data Lake Ingestion | Action items, 6 open | Gaps → action items mid-flight, owners assigned |
| Fraud Alerts Notification Service | Closed (first pass) | The happy path: readiness cleared target on round 1 |
| Payments Reconciliation Service | Closed after 1 redress round | A rejected response, then fixed, then closed |
| Legacy Mainframe Batch Interface | Escalated after 1 redress round | The taker kept giving weak justifications; code refused to close and escalated to the manager |

## Quota safety
- **Automatic cross-provider fallback is now live** ([app/llm.py](../app/llm.py)): every call tries Gemini first; on any Gemini failure (daily quota, rate limit, or an outage) it retries once against **Groq** (`openai/gpt-oss-120b`, OpenAI-compatible API) if `GROQ_API_KEY` is set in `.env`. Verified live by forcing a broken Gemini key and confirming a real, schema-valid Groq response came back — including on Baton's KT assessment schema, not just a toy example.
- This is real redundancy, not just a second Gemini key: it survives Google's API being down entirely, not only this key's quota.
- Nothing else changes on screen when it fires — same JSON schema, same Pydantic validation, so a fallback answer looks identical to a Gemini one. The only sign is in the terminal log (the Gemini exception is swallowed silently on success), so if you want to *show* the fallback firing, temporarily break `GEMINI_API_KEY` in `.env` and run one call.
- Caveats: Groq's free-tier model list is per-account and changed under us once already today (`llama-3.3-70b-versatile` 404'd; `openai/gpt-oss-120b` is what this account currently has). If Groq also 404s on model access, re-check `GET https://api.groq.com/openai/v1/models` with the key in `.env` and update `GROQ_MODEL`. Groq quality/latency has not been rehearsed in the full demo flow, only spot-checked — if it fires live on stage, expect a few extra seconds and slightly different phrasing than the Gemini-cached answers.
- If **both** providers are out: every screen except the 3:45–5:15 live-typing segment still works, since it's pre-seeded/cached. Skip that segment and narrate it from the table above instead.
