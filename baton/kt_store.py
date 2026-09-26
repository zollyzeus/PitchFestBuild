"""File-backed KT records (one JSON per KT) and manager tracking views."""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from pathlib import Path

from baton.kt_models import ANGLE_WEIGHT, STATUS_LABEL, KTRecord

KT_DIR = Path("data/kt")
ACTION_DAYS = 2  # days an owner has to respond to an action item
ACTIVE_ACTION_STATES = ("action_items", "open_redress")


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def new_id(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")[:24] or "kt"
    return f"{slug}-{datetime.now():%H%M%S}"


def save(rec: KTRecord) -> None:
    KT_DIR.mkdir(parents=True, exist_ok=True)
    (KT_DIR / f"{rec.id}.json").write_text(rec.model_dump_json(indent=1))


def load(kt_id: str) -> KTRecord:
    return KTRecord.model_validate_json((KT_DIR / f"{kt_id}.json").read_text())


def list_all() -> list[KTRecord]:
    if not KT_DIR.exists():
        return []
    recs = [KTRecord.model_validate_json(p.read_text()) for p in sorted(KT_DIR.glob("*.json"))]
    return sorted(recs, key=lambda r: r.created_at, reverse=True)


def set_status(rec: KTRecord, status: str) -> None:
    rec.status = status  # type: ignore[assignment]
    rec.stage_log.append({"stage": status, "at": now()})


def readiness(rec: KTRecord) -> float:
    num = den = 0.0
    for a in rec.assessments:
        base = {"covered": 1.0, "partial": 0.5, "gap": 0.0}[a.status]
        if a.mismatch:
            base = min(base, 0.5)
        if a.resolution == "addressed":
            base = 1.0
        elif a.resolution == "accepted_risk":
            base = max(base, 0.75)
        w = ANGLE_WEIGHT.get(a.angle, 1)
        num += w * base
        den += w
    return num / den if den else 0.0


def deadline(rec: KTRecord) -> date:
    return date.fromisoformat(rec.project.start_date) + timedelta(days=rec.project.duration_days)


def waiting_on(rec: KTRecord) -> list[str]:
    """Who the KT is currently blocked on."""
    p = rec.project
    if rec.status in ("qa_round_1", "qa_round_2"):
        n = rec.q_round
        return [f"KT giver ({p.giver})" if aud == "giver" else f"KT taker ({p.taker})"
                for aud in ("giver", "taker") if f"R{n}-{aud}" not in rec.submitted]
    if rec.status in ACTIVE_ACTION_STATES:
        owners = {a.owner for a in rec.actions if a.status == "open"}
        return [f"KT giver ({p.giver})" if o == "giver" else f"KT taker ({p.taker})" for o in sorted(owners)]
    if rec.status == "escalated":
        return ["Manager"]
    return []


def time_in_stage_days(rec: KTRecord) -> float:
    at = rec.stage_log[-1]["at"] if rec.stage_log else rec.created_at
    return round((datetime.now() - datetime.fromisoformat(at)).total_seconds() / 86400, 2)


def is_overdue(rec: KTRecord) -> bool:
    return rec.status not in ("closed",) and date.today() > deadline(rec)


def row(rec: KTRecord) -> dict:
    p, dl = rec.project, deadline(rec)
    elapsed = (date.today() - date.fromisoformat(p.start_date)).days + 1
    pending = [a for a in rec.actions if a.status == "open"]
    return {
        "KT": p.title, "Giver": p.giver, "Taker": p.taker,
        "Stage": STATUS_LABEL[rec.status] + (f" #{rec.redress_round}" if rec.status == "open_redress" else ""),
        "Day": f"{max(elapsed, 1)} of {p.duration_days}",
        "Deadline": dl.isoformat(), "Days left": (dl - date.today()).days,
        "Overdue": "YES" if is_overdue(rec) else "",
        "Waiting on": ", ".join(waiting_on(rec)) or "-",
        "Open actions": len(pending),
        "Readiness": f"{readiness(rec):.0%}" if rec.assessments else "-",
        "In stage (days)": time_in_stage_days(rec),
    }


def action_rows(recs: list[KTRecord]) -> list[dict]:
    out = []
    for r in recs:
        for a in r.actions:
            name = r.project.giver if a.owner == "giver" else r.project.taker
            out.append({
                "KT": r.project.title, "Action": a.description, "Angle": a.angle,
                "Owner": f"{a.owner} ({name})", "Severity": a.severity, "Due": a.due,
                "Overdue": "YES" if a.status == "open" and date.fromisoformat(a.due) < date.today() else "",
                "State": a.status if not a.verdict else f"{a.status} / {a.verdict}",
            })
    return out
