# PitchFest Build — Planning Docs

> **Actual implementation status and measured results live in [../RUN.md](../RUN.md).** The specs below are the original plans; F1–F11 of Second Look are now built (F9 export is CSV-only, F10 anonymization is best-effort).

**One person is building this.** A solo builder cannot take both ideas below to a demoable state in a single ~8-hour day, so the plan is to commit fully to **Second Look** and treat **Baton** as the fully-scoped next problem (mentioned as "what we'd build next" on the slide), not something built today.

| Doc | Idea | Status | One-line pitch |
| --- | --- | --- | --- |
| [01-second-look-plan.md](01-second-look-plan.md) | **Second Look** | **Build this** | Re-screens ATS-rejected candidates, surfaces qualified ones the keyword filter dropped, with cited evidence and bias flags. |
| [02-baton-plan.md](02-baton-plan.md) | **Baton** | Parked (reference only) | AI interviewer that captures a departing expert's undocumented knowledge and hands the successor a sourced handover + grounded Q&A. |

Both docs still cover the full spec each: problem framing & assumptions, users/journey/demo script, functional & non-functional requirements, architecture (diagram + components), tech stack & dependencies, AI design (prompts/schemas/eval), technical & AI moat, competitive landscape & differentiation, and a build plan.

**Second Look's build plan now has a solo, hour-by-hour schedule** (setup → data → baseline → core AI → UI → eval → slide → rehearsal → backup video → upload), with a hard 4:00 pm stop for coding and named checkpoints (11:10, 13:10) that trigger cutting scope further rather than switching ideas.

Runs on this laptop (Intel i5-8250U, 8 GB RAM, no GPU, no Node/Docker) — Python + Claude API only, no local model.

Live, editable versions (with the architecture diagrams rendered) are also on claude.ai:
- Second Look: https://claude.ai/artifact/4RW5cxQJ9qhQbL5Kt59y12
- Baton: https://claude.ai/artifact/A5Dxf4SZjbNH6u8G4DFXBQ
