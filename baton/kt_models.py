"""Models for the corporate Knowledge Transfer (KT) workflow."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

# (key, title, weight, what it covers). Weight = business risk if this angle is left uncovered.
ANGLES = [
    ("architecture", "Architecture & design decisions", 3, "system design, components, why key decisions were made"),
    ("code", "Codebase, repos & standards", 2, "repo layout, branching, coding standards, code ownership"),
    ("environments", "Environments & access", 3, "dev/test/prod setup, config, access requests, data refresh"),
    ("deploy", "Build, CI/CD & release", 3, "pipelines, release steps, rollback, release calendar"),
    ("testing", "Testing & QA", 2, "test suites, test data, test environment quirks, sign-off"),
    ("data", "Data, integrations & dependencies", 2, "upstream/downstream systems, data flows, vendors, SLAs"),
    ("support", "Incidents, support & runbooks", 3, "on-call, recurring incidents, runbooks, escalation paths"),
    ("business", "Business context & stakeholders", 2, "why the project exists, stakeholders, priorities, expectations"),
    ("security", "Security, credentials & compliance", 3, "secrets, access reviews, audit and compliance duties"),
    ("inflight", "In-flight work & known issues", 3, "open tickets, half-done work, tech debt, known bugs, commitments"),
    ("tribal", "Undocumented know-how", 2, "workarounds, gotchas, unwritten rules, who really fixes what"),
    ("docs", "Documentation & contacts", 1, "where docs live, how current they are, who to ask"),
]
ANGLE_KEYS = [a[0] for a in ANGLES]
ANGLE_TITLE = {a[0]: a[1] for a in ANGLES}
ANGLE_WEIGHT = {a[0]: a[2] for a in ANGLES}
ANGLE_DESC = {a[0]: a[3] for a in ANGLES}

Status = Literal["qa_round_1", "qa_round_2", "action_items", "open_redress", "closed", "escalated"]
STATUS_LABEL = {
    "qa_round_1": "Q&A round 1", "qa_round_2": "Q&A round 2 (follow-up)",
    "action_items": "Action items", "open_redress": "Open: redress round",
    "closed": "Closed", "escalated": "Escalated to manager",
}
MAX_REDRESS = 1  # after one redress round, unresolved items escalate


class ProjectInput(BaseModel):
    title: str
    description: str
    duration_days: int
    start_date: str
    roles: str
    tech_stack: str
    dev_env: str
    test_env: str
    extra: str = ""
    giver: str
    taker: str
    threshold: float = 0.8


class QA(BaseModel):
    id: str
    round: int
    angle: str
    audience: Literal["giver", "taker"]
    question: str
    answer: str = ""
    answered_at: str = ""


class AngleAssessment(BaseModel):
    angle: str
    status: Literal["covered", "partial", "gap"]
    giver_evidence: str = ""
    taker_evidence: str = ""
    mismatch: bool = False
    note: str = ""
    resolution: Literal["", "addressed", "accepted_risk"] = ""


class Action(BaseModel):
    id: str
    angle: str
    owner: Literal["giver", "taker"]
    description: str
    severity: Literal["high", "medium", "low"]
    due: str
    status: Literal["open", "addressed", "justified"] = "open"
    response: str = ""
    responded_at: str = ""
    verdict: Literal["", "accepted", "rejected"] = ""
    verdict_note: str = ""
    prev_responses: list[str] = []


class KTRecord(BaseModel):
    id: str
    project: ProjectInput
    status: Status = "qa_round_1"
    created_at: str
    stage_log: list[dict] = []
    qa: list[QA] = []
    assessments: list[AngleAssessment] = []
    actions: list[Action] = []
    q_round: int = 1
    redress_round: int = 0
    submitted: dict[str, str] = {}
    readiness_log: list[dict] = []
    decision_note: str = ""


# ---- LLM output schemas ----
class AngleQuestions(BaseModel):
    angle: str
    giver_question: str
    taker_question: str


class QuestionSet(BaseModel):
    items: list[AngleQuestions]


class LLMAssessment(BaseModel):
    angle: str
    status: Literal["covered", "partial", "gap"]
    giver_evidence: str = Field(description="Short verbatim quote from the giver's answers, or empty")
    taker_evidence: str = Field(description="Short verbatim quote from the taker's answers, or empty")
    mismatch: bool
    note: str


class AssessmentSet(BaseModel):
    items: list[LLMAssessment]


class NewAction(BaseModel):
    angle: str
    owner: Literal["giver", "taker"]
    description: str
    severity: Literal["high", "medium", "low"]


class ActionSet(BaseModel):
    items: list[NewAction]


class ReviewVerdict(BaseModel):
    action_id: str
    accepted: bool
    note: str


class ReviewSet(BaseModel):
    items: list[ReviewVerdict]


class SimAnswer(BaseModel):
    qid: str
    answer: str


class SimAnswers(BaseModel):
    items: list[SimAnswer]


class SimResponse(BaseModel):
    action_id: str
    mode: Literal["addressed", "justified"]
    response: str


class SimResponses(BaseModel):
    items: list[SimResponse]
