"""Typed state and outputs for the incident-investigation graph."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class Phase(StrEnum):
    OBSERVE = "observe"
    INVESTIGATE = "investigate"
    PROPOSE = "propose_remediation"
    AWAITING_APPROVAL = "awaiting_human_approval"
    REMEDIATE = "remediate"
    VERIFY = "verify_recovery"
    COMPLETE = "complete"
    REJECTED = "remediation_rejected"
    BLOCKED = "blocked"


class Severity(StrEnum):
    P1 = "P1"
    P2 = "P2"
    P3 = "P3"
    P4 = "P4"


@dataclass(frozen=True)
class Evidence:
    """An observation linked to exactly one read-only tool result."""

    id: str
    tool_name: str
    observation: str
    raw: str
    collected_at: str
    source_kind: str = "live_observation"  # live_observation or retrieved_guidance


@dataclass(frozen=True)
class Hypothesis:
    id: str
    claim: str
    rationale: str
    status: str = "open"  # open, supported, rejected
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True)
class ToolCall:
    tool_name: str
    arguments: dict[str, Any]
    succeeded: bool
    summary: str


@dataclass(frozen=True)
class RemediationProposal:
    """A proposal is data, never an instruction to execute arbitrary commands."""

    action_id: str
    description: str
    rollback: str
    expected_recovery_signal: str
    risk: str
    requires_human_approval: bool = True


@dataclass(frozen=True)
class Approval:
    action_id: str
    approved_by: str
    approved: bool
    note: str = ""


@dataclass(frozen=True)
class IncidentReport:
    incident_id: str
    severity: Severity
    root_cause: str
    confidence: float
    evidence_ids: tuple[str, ...]
    diagnosis: str
    proposed_remediation: RemediationProposal | None
    expected_recovery_signal: str
    safety_note: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class IncidentState:
    """The graph's checkpointable state.  It contains no hidden chat transcript."""

    incident_id: str
    symptom: str
    phase: Phase = Phase.OBSERVE
    evidence: list[Evidence] = field(default_factory=list)
    hypotheses: list[Hypothesis] = field(default_factory=list)
    tool_calls: list[ToolCall] = field(default_factory=list)
    proposal: RemediationProposal | None = None
    approval: Approval | None = None
    report: IncidentReport | None = None
    recovery_observations: list[Evidence] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_evidence(self, evidence: Evidence) -> None:
        self.evidence.append(evidence)

    def add_hypothesis(self, hypothesis: Hypothesis) -> None:
        self.hypotheses.append(hypothesis)

    def evidence_ids(self) -> tuple[str, ...]:
        return tuple(item.id for item in self.evidence)
