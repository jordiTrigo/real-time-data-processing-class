"""Deterministic and model-backed choices for the investigation node."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .models import (
    Hypothesis,
    IncidentReport,
    IncidentState,
    RemediationProposal,
    Severity,
)


@dataclass(frozen=True)
class InvestigationDecision:
    tool_name: str | None = None
    hypothesis: Hypothesis | None = None
    report: IncidentReport | None = None


class Investigator(Protocol):
    def decide(
        self, state: IncidentState, available_tools: tuple[str, ...]
    ) -> InvestigationDecision: ...


@dataclass(frozen=True)
class ScriptedStep:
    tool_name: str
    claim: str
    rationale: str


class ScriptedInvestigator:
    """Offline, repeatable investigator used for tests and rubric demonstrations."""

    def __init__(
        self,
        *,
        severity: Severity,
        root_cause: str,
        diagnosis: str,
        steps: tuple[ScriptedStep, ...],
        remediation: RemediationProposal,
        confidence: float = 0.9,
    ) -> None:
        self.severity = severity
        self.root_cause = root_cause
        self.diagnosis = diagnosis
        self.steps = steps
        self.remediation = remediation
        self.confidence = confidence

    def decide(
        self, state: IncidentState, available_tools: tuple[str, ...]
    ) -> InvestigationDecision:
        index = len(state.tool_calls)
        if index < len(self.steps):
            step = self.steps[index]
            if step.tool_name not in available_tools:
                return InvestigationDecision()
            return InvestigationDecision(
                tool_name=step.tool_name,
                hypothesis=Hypothesis(
                    id=f"h{index + 1}", claim=step.claim, rationale=step.rationale
                ),
            )
        return InvestigationDecision(
            report=IncidentReport(
                incident_id=state.incident_id,
                severity=self.severity,
                root_cause=self.root_cause,
                confidence=self.confidence,
                evidence_ids=state.evidence_ids(),
                diagnosis=self.diagnosis,
                proposed_remediation=self.remediation,
                expected_recovery_signal=self.remediation.expected_recovery_signal,
                safety_note="Remediation is a proposal until a named human approves it.",
            )
        )
