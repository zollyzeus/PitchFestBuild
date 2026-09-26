"""Markdown handover document + 30-60-90 day plan."""
from __future__ import annotations

from baton.common import call
from baton.interview import open_risks
from baton.mapper import coverage
from baton.schemas import Plan, Session

SYSTEM = """\
You write a 30-60-90 day plan for a successor taking over a role, from the handover items and \
knowledge map given. 3-5 concrete bullets per period; order by upcoming cadence and criticality; \
mention only duties, systems and people that appear in the input."""


def build_markdown(s: Session, role: str, expert: str, last_day: str) -> str:
    plan = call("plan", Plan, SYSTEM, f"MAP:\n{s.kmap.model_dump_json()}\n\nHANDOVER:\n"
                + "\n".join(f"- {h.item_id} {h.field}: {h.text}" for h in s.handover))
    L = [f"# Handover: {role}", f"From {expert}, last day {last_day}. "
         f"Coverage {coverage(s.kmap):.0%} (was {s.baseline_coverage:.0%} from documents alone).", "",
         "## Duties, systems and people"]
    for it in s.kmap.items:
        L.append(f"### {it.title} ({it.kind}, {it.criticality}{', ' + it.cadence if it.cadence else ''})")
        for h in (h for h in s.handover if h.item_id == it.id):
            L.append(f"- **{h.field}**: {h.text} _(source: {h.source})_")
        L.append(f"_Documents: {', '.join(it.sources) or '-'}_\n")
    L += ["## Open risks"] + [f"- {r}" for r in open_risks(s)] + ["", "## 30-60-90 day plan"]
    for label, days in (("First 30 days", plan.days_30), ("Days 31-60", plan.days_60), ("Days 61-90", plan.days_90)):
        L += [f"### {label}"] + [f"- {d}" for d in days]
    return "\n".join(L)
