"""Turn a job description into a structured rubric (Gemini call #1, once per JD)."""
from __future__ import annotations

from app.cache import get_or_compute
from app.llm import MODEL_REASONING, call_structured
from app.schemas import Rubric

SYSTEM = """\
You turn a job description into a structured hiring rubric for two readers at once: \
an old-fashioned keyword ATS, and a fair, evidence-based human reviewer.

Produce 5-8 requirements. For EVERY requirement give:
- "keywords": the literal words/phrases a blunt keyword ATS would search for \
(exactly what the JD itself says, e.g. "Kubernetes", "5+ years").
- "equivalents": OTHER real-world skills, tools, platforms or titles that satisfy the \
SAME underlying requirement even though the JD never used those words \
(e.g. Mesos/Nomad/ECS/Docker Swarm as equivalents of "Kubernetes"; \
"batch data pipelines" as an equivalent of "data engineering"; an older job title that \
covered the same work). This equivalents list is the whole point: a naive keyword filter \
misses these, a fair reviewer should not.
- "evidence_examples": 2-3 short phrases showing what a CV would say if this requirement \
is genuinely met (used to guide the scorer later).

Mark the 3-5 truly non-negotiable requirements as type "must" (weight 3), the rest as \
"nice" (weight 1). Give each requirement a short id like "R1", "R2".
"""


def extract_rubric(jd_text: str) -> Rubric:
    return get_or_compute(
        "rubric",
        Rubric,
        lambda: call_structured(
            model=MODEL_REASONING,
            system=SYSTEM,
            user_content=jd_text,
            response_schema=Rubric,
            deterministic=True,
        ),
        jd_text,
    )
