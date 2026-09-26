"""Pydantic models for Baton: dataset, knowledge map, gaps, interview session."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Doc(BaseModel):
    name: str
    text: str


class HiddenFact(BaseModel):
    id: str
    hint: str = Field(description="Which document phrase creates the gap this fact fills")
    truth: str = Field(description="The undocumented detail only the expert knows")


class QAQuestion(BaseModel):
    question: str
    answerable_from: Literal["docs", "interview", "none"]
    expected: str = Field(description="Correct answer, or empty if answerable_from is none")


class BatonDataset(BaseModel):
    role_title: str
    expert_name: str
    last_day: str
    docs: list[Doc]
    hidden_facts: list[HiddenFact]
    qa_questions: list[QAQuestion]


class MapItem(BaseModel):
    id: str
    kind: Literal["duty", "recurring_task", "system", "person", "vendor", "decision"]
    title: str
    cadence: str = ""
    criticality: Literal["high", "medium", "low"]
    sources: list[str] = Field(description="Names of documents that mention it")
    what: bool
    how: bool
    why: bool
    who: bool


class KnowledgeMap(BaseModel):
    items: list[MapItem]


class ExtraGap(BaseModel):
    item_id: str
    field: Literal["how", "why", "who", "contradiction", "vague"]
    evidence: str = Field(description="Exact quote from a document that shows the gap")


class ExtraGaps(BaseModel):
    gaps: list[ExtraGap]


class Gap(BaseModel):
    id: str
    item_id: str
    field: str
    evidence: str
    priority: float
    status: Literal["open", "closed", "skipped"] = "open"


class Question(BaseModel):
    question: str
    quoted_span: str = Field(description="Exact words copied from a document that the question quotes")


class Verdict(BaseModel):
    verdict: Literal["closes_gap", "vague", "skip"]
    captured_text: str = Field(description="One or two sentences of what the expert stated, empty if none")
    new_gap: str = Field(default="", description="Unknown system/person/step the answer mentions, else empty")


class HandoverItem(BaseModel):
    gap_id: str
    item_id: str
    field: str
    text: str
    source: str


class Turn(BaseModel):
    n: int
    gap_id: str
    question: str
    answer: str = ""
    verdict: str = ""


class Session(BaseModel):
    docs: list[Doc]
    kmap: KnowledgeMap
    gaps: list[Gap]
    handover: list[HandoverItem] = []
    turns: list[Turn] = []
    current_gap: str | None = None
    current_question: str | None = None
    followups: int = 0
    baseline_coverage: float = 0.0
    target: float = 0.8
    round: int = 1
    max_turns: int = 25
    confidence_log: list[float] = []


class QAAnswer(BaseModel):
    answer: str
    citations: list[str]
    supported: bool


class ExpertReply(BaseModel):
    answer: str


class FactCheck(BaseModel):
    fact_id: str
    captured: bool


class FactChecks(BaseModel):
    checks: list[FactCheck]


class Grade(BaseModel):
    index: int
    correct: bool


class Grades(BaseModel):
    grades: list[Grade]


class Plan(BaseModel):
    days_30: list[str]
    days_60: list[str]
    days_90: list[str]
