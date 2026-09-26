"""Generate one synthetic demo dataset (JD + candidate CVs, with planted ground
truth) via a single Gemini call. Run standalone to pre-warm before the demo:

    .venv/bin/python -m app.data_gen
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from app.envload import load_dotenv
from app.llm import MODEL_REASONING, call_structured
from app.schemas import RawDataset

load_dotenv()

DATASET_PATH = Path("data/dataset.json")

SYSTEM = """\
You generate a SYNTHETIC test set for a demo of an AI hiring tool. Everyone in it is \
entirely fictional -- invented names, invented companies -- with no resemblance to real \
people. Do not use any real person's name.

Write a job description for a mid-to-senior "Backend Engineer, Distributed Systems" role \
(6-10 short paragraphs/bullets, realistic, naming specific required technologies).

Then write exactly 16 candidate CVs (each 250-450 words, first person resume style: \
summary, experience with employers/dates/bullets, skills) for this role, made up of:

- 5 candidates who are CLEARLY qualified and use the exact keywords/tech the JD names \
(planted_qualified=true, planted_reason="clear match").
- 6 candidates who are GENUINELY qualified for the role but phrase it in a way a blunt \
keyword ATS would reject: e.g. they used an older or different tool that does the same \
job (Mesos/Nomad/ECS/self-hosted tooling instead of the JD's named stack), or their title \
predates current buzzwords, or they have a clearly-explained 1-3 year employment gap \
(caregiving, health, a sabbatical, a startup that shut down), or they are a career-changer \
whose prior field taught transferable skills. (planted_qualified=true; planted_reason must \
name the specific trap, e.g. "used Mesos not Kubernetes" or "18-month caregiving gap in \
2022, explained in the CV").
- 5 candidates who are GENUINELY NOT qualified for this specific role (wrong seniority, \
wrong domain, or missing the core skills entirely), including at least 2 who superficially \
mention a couple of matching buzzwords without real depth, to test for false positives. \
(planted_qualified=false; planted_reason explains what's actually missing).

Give each candidate a short fictional full name and an id like "C01".."C16".
"""


def generate_dataset() -> RawDataset:
    return call_structured(
        model=MODEL_REASONING,
        system=SYSTEM,
        user_content="Generate the dataset now, following the rules exactly.",
        response_schema=RawDataset,
        max_retries=5,
    )


def main() -> None:
    print(f"Generating synthetic dataset with {MODEL_REASONING} ...")
    ds = generate_dataset()
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_PATH.write_text(ds.model_dump_json(indent=2))
    print(f"Wrote {len(ds.candidates)} candidates to {DATASET_PATH}")
    n_qual = sum(1 for c in ds.candidates if c.planted_qualified)
    print(f"  planted_qualified=True: {n_qual}, False: {len(ds.candidates) - n_qual}")


if __name__ == "__main__":
    sys.exit(main() or 0)
