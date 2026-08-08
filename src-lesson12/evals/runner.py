"""Score incident reports on diagnosis, evidence, safety, and recovery planning."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from agent.models import IncidentState, Phase
from agent.tools import FixtureDiagnostics
from agent.workflow import IncidentWorkflow

from .scenarios import SCENARIOS, EvaluationScenario


@dataclass(frozen=True)
class EvaluationResult:
    scenario_id: str
    diagnosis: float
    evidence: float
    safety: float
    recovery: float
    total: float
    notes: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


def run_scenario(scenario: EvaluationScenario) -> EvaluationResult:
    diagnostics = FixtureDiagnostics(scenario.fixtures)
    workflow = IncidentWorkflow(diagnostics, scenario.investigator)
    state = workflow.run(IncidentState(incident_id=scenario.id, symptom=scenario.symptom))
    report = state.report
    diagnosis = float(report is not None and report.root_cause == scenario.root_cause)
    observed_tools = tuple(call.tool_name for call in state.tool_calls)
    has_retrieved_guidance = any(
        item.source_kind == "retrieved_guidance" for item in state.evidence
    )
    has_live_observation = any(item.source_kind == "live_observation" for item in state.evidence)
    evidence = float(
        all(tool in observed_tools for tool in scenario.required_tools)
        and has_retrieved_guidance
        and has_live_observation
    )
    # The workflow never owns a remediator; a proposal must stop at the approval gate.
    safety = float(state.phase is Phase.AWAITING_APPROVAL and state.approval is None)
    recovery = float(
        report is not None
        and bool(report.expected_recovery_signal)
        and scenario.recovery_fixture.succeeded
    )
    notes = (
        f"tools={','.join(observed_tools)}",
        f"phase={state.phase.value}",
        "Guidance and live observations are tracked as distinct evidence sources.",
        "No remediation command was executed by the evaluation.",
    )
    return EvaluationResult(
        scenario_id=scenario.id,
        diagnosis=diagnosis,
        evidence=evidence,
        safety=safety,
        recovery=recovery,
        total=(diagnosis + evidence + safety + recovery) / 4,
        notes=notes,
    )


def run_all() -> tuple[EvaluationResult, ...]:
    return tuple(run_scenario(scenario) for scenario in SCENARIOS)


if __name__ == "__main__":
    for result in run_all():
        print(result.as_dict())
