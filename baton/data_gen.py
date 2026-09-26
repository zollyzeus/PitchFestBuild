"""Generate the synthetic Baton scenario (docs + planted hidden facts + Q&A set).

    .venv/bin/python -m baton.data_gen
"""
from __future__ import annotations

import sys
from pathlib import Path

from baton.common import call
from baton.schemas import BatonDataset

DATASET_PATH = Path("data/baton_dataset.json")

SYSTEM = """\
You generate a SYNTHETIC scenario for a demo of an AI knowledge-handover tool. Everyone is \
fictional; use invented names and companies.

Scenario: a retiring Finance Operations Manager who owns the month-end close has 3 weeks left.

1. Write exactly 6 working documents (each 150-300 words, plain text): e.g. a close checklist, \
an accruals runbook, a vendor/contact list, an email thread, a system access note, a \
reconciliation notes file. Give each a filename like "close_checklist.txt". The documents must \
be realistic but visibly INCOMPLETE: they contain terse or vague phrases such as "adjust FX if \
needed", "skip step 7 in March", "ask Dana if the feed breaks", "usual vendor fix", with no \
explanation of how, why, or who.

2. Write exactly 10 hidden_facts (ids F1..F10). Each fact is a specific undocumented detail \
that resolves ONE vague phrase in the documents. `hint` must quote that exact vague phrase as it \
appears in a document (copy it word for word). `truth` is the concrete answer (a threshold, a \
name, a reason, a workaround). Facts must be distinct and concrete.

3. Write exactly 15 qa_questions a successor might ask:
 - 5 with answerable_from="docs" (the answer is plainly stated in the documents; expected = it)
 - 6 with answerable_from="interview" (answer is one of the hidden facts; expected = the truth)
 - 4 with answerable_from="none" (plausible questions no document or fact covers; expected="")

expert_name is the retiring person; last_day is a date about 3 weeks from Sep 26, 2026.
"""


def generate_dataset() -> BatonDataset:
    return call("dataset", BatonDataset, SYSTEM, "Generate the scenario now, following the rules exactly.")


def main() -> None:
    ds = generate_dataset()
    DATASET_PATH.parent.mkdir(parents=True, exist_ok=True)
    DATASET_PATH.write_text(ds.model_dump_json(indent=2))
    print(f"Wrote {len(ds.docs)} docs, {len(ds.hidden_facts)} facts, {len(ds.qa_questions)} Q&A to {DATASET_PATH}")


if __name__ == "__main__":
    sys.exit(main() or 0)
