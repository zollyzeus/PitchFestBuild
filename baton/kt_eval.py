"""Unattended KT evaluation with planted weaknesses.

    .venv/bin/python -m baton.kt_eval
"""
from __future__ import annotations

from datetime import date

from baton import kt_engine as eng
from baton import kt_sim as sim
from baton.kt_models import ANGLE_KEYS, ProjectInput
from baton.kt_store import readiness

SAMPLE = ProjectInput(
    title="Payments Reconciliation Service",
    description="Java/Spring service that reconciles card settlement files against the ledger nightly "
                "and raises breaks to Finance Ops. Being handed over as the lead moves to a new programme.",
    duration_days=14, start_date=date.today().isoformat(),
    roles="Giver: tech lead, owns design, releases, on-call. Taker: senior engineer, will own delivery and support.",
    tech_stack="Java 17, Spring Boot, PostgreSQL, Kafka, Jenkins, Docker, Kubernetes (EKS), Grafana",
    dev_env="Docker Compose locally plus shared dev namespace on EKS; secrets in HashiCorp Vault",
    test_env="Shared UAT namespace with masked prod data, refreshed monthly; Selenium and Postman suites in Jenkins",
    extra="Focus on release process, incident handling and anything that is not written down.",
    giver="Meera Rao", taker="Arjun Nair",
)


def evaluate_run(rec) -> dict:
    return {"status": rec.status, "readiness_log": rec.readiness_log, "redress_rounds": rec.redress_round,
            "q_rounds": rec.q_round, "actions": len(rec.actions),
            "accepted": sum(a.verdict == "accepted" for a in rec.actions), "note": rec.decision_note}


def main() -> None:
    rec = eng.create_kt(SAMPLE)
    print("created", rec.id)
    # Round-1 detection: answer round 1 then read the first assessment
    for aud in ("giver", "taker"):
        sim.step(rec, aud)
    first = {a.angle: (a.status, a.mismatch) for a in rec.assessments}
    flagged = [k for k in sim.PLANTED if first[k][0] != "covered" or first[k][1]]
    false_alarms = [k for k in ANGLE_KEYS if k not in sim.PLANTED and (first[k][0] == "gap")]
    sim.run_to_end(rec)
    m = evaluate_run(rec)
    print(f"Planted-weakness recall (first assessment): {len(flagged)}/{len(sim.PLANTED)}  missed: "
          f"{[k for k in sim.PLANTED if k not in flagged]}")
    print(f"Unplanted angles flagged as hard gaps: {len(false_alarms)}/{len(ANGLE_KEYS) - len(sim.PLANTED)}  {false_alarms}")
    print("Readiness trail:", [(e['stage'], e['readiness']) for e in m['readiness_log']])
    print(f"Q rounds {m['q_rounds']}, redress {m['redress_rounds']}, actions {m['accepted']}/{m['actions']} accepted")
    print("Outcome:", m["status"], "|", m["note"], "| final readiness", f"{readiness(rec):.0%}")


if __name__ == "__main__":
    main()
