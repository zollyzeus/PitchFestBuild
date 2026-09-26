"""Pydantic data models shared across the pipeline."""
from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field


class Requirement(BaseModel):
    id: str
    text: str
    type: Literal["must", "nice"]
    weight: int = 1
    # Literal words/phrases a blunt keyword ATS would search for (what the JD says).
    keywords: list[str] = Field(default_factory=list)
    # Other real-world skills/tools/titles that satisfy the same requirement,
    # even though the JD never used those words. This is what a keyword ATS misses.
    equivalents: list[str] = Field(default_factory=list)
    evidence_examples: list[str] = Field(default_factory=list)


class Rubric(BaseModel):
    role_title: str
    requirements: list[Requirement]


class ScoredRequirement(BaseModel):
    req_id: str
    verdict: Literal["met", "partial", "not_met"]
    quote: str = ""
    reasoning: str = ""
    transferable: bool = False
    confidence: float = 0.0
    # Filled in by code (grounding.py), never by the model.
    grounded: bool = False


class BiasSignal(BaseModel):
    type: str
    evidence: str
    note: str = ""


class CandidateScore(BaseModel):
    candidate_id: str
    requirements: list[ScoredRequirement] = Field(default_factory=list)
    bias_signals: list[BiasSignal] = Field(default_factory=list)
    interview_questions: list[str] = Field(default_factory=list)
    # Computed in code (pipeline.py), never by the model.
    fit_score: float = 0.0
    must_have_gate_passed: bool = False


class Candidate(BaseModel):
    id: str
    name: str
    text: str
    # Ground truth planted by the synthetic data generator, for the live eval panel.
    # Never shown to the scoring model.
    planted_qualified: Optional[bool] = None
    planted_reason: str = ""


class BaselineResult(BaseModel):
    candidate_id: str
    passed: bool
    fired_rules: list[str] = Field(default_factory=list)
    # Structured ids of the must-have requirements that rejected this candidate,
    # so the pattern report can aggregate per rule without parsing strings.
    fired_req_ids: list[str] = Field(default_factory=list)


class Dataset(BaseModel):
    role_title: str
    jd_text: str
    candidates: list[Candidate]


# --- Schemas used ONLY as the Gemini response_schema for structured output ---
# (kept separate from the domain models above so bias/interview fields don't
# need `grounded`/`fit_score` etc. at generation time)


class RawScoredRequirement(BaseModel):
    req_id: str
    verdict: Literal["met", "partial", "not_met"]
    quote: str
    reasoning: str
    transferable: bool
    confidence: float


class RawCandidateScore(BaseModel):
    requirements: list[RawScoredRequirement]
    bias_signals: list[BiasSignal]
    interview_questions: list[str]


class RawDataset(BaseModel):
    role_title: str
    jd_text: str
    candidates: list[Candidate]
