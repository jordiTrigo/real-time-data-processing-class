"""A small LangGraph-shaped incident workflow with a safe stdlib fallback.

Nodes are explicit so students can draw this on a whiteboard or map it directly to
``langgraph.graph.StateGraph`` later.  Checkpoint persistence is left to the host
application; all state is serializable dataclass data.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

from .investigators import Investigator
from .models import Approval, Evidence, IncidentState, Phase
from .tools import ToolCatalog, ToolResult


class ApprovalRequired(RuntimeError):
    pass


class IncidentWorkflow:
    def __init__(self, diagnostics: ToolCatalog, investigator: Investigator) -> None:
        self.diagnostics = diagnostics
        self.investigator = investigator

    def run(self, state: IncidentState, max_steps: int = 12) -> IncidentState:
        """Observe → investigate → propose → wait for human approval.

        This method cannot execute a remediation.  The host must call
        ``approve`` then separately invoke its own tightly-scoped remediation
        handler after inspecting the proposed action.
        """

        state.phase = Phase.INVESTIGATE
        for _ in range(max_steps):
            decision = self.investigator.decide(state, self.diagnostics.names())
            if decision.hypothesis:
                state.add_hypothesis(decision.hypothesis)
            if decision.tool_name:
                self._collect(state, decision.tool_name)
                continue
            if decision.report:
                if not self.has_live_evidence(state):
                    state.phase = Phase.BLOCKED
                    state.errors.append(
                        "A report needs at least one live observation; "
                        "retrieved guidance is not proof."
                    )
                    return state
                state.report = decision.report
                state.proposal = decision.report.proposed_remediation
                state.phase = Phase.AWAITING_APPROVAL if state.proposal else Phase.COMPLETE
                return state
            state.phase = Phase.BLOCKED
            state.errors.append("Investigator returned neither a tool nor a structured report.")
            return state
        state.phase = Phase.BLOCKED
        state.errors.append(f"Investigation exceeded the {max_steps}-step safety limit.")
        return state

    @staticmethod
    def has_live_evidence(state: IncidentState) -> bool:
        return any(item.source_kind == "live_observation" for item in state.evidence)

    def approve(self, state: IncidentState, approval: Approval) -> IncidentState:
        if state.phase is not Phase.AWAITING_APPROVAL or state.proposal is None:
            raise ApprovalRequired("There is no pending remediation proposal to approve.")
        if approval.action_id != state.proposal.action_id:
            raise ApprovalRequired("Approval action_id does not match the proposed remediation.")
        state.approval = approval
        state.phase = Phase.REMEDIATE if approval.approved else Phase.COMPLETE
        return state

    def verify_recovery(
        self, state: IncidentState, probe: Callable[[], ToolResult]
    ) -> IncidentState:
        if state.approval is None or not state.approval.approved:
            raise ApprovalRequired("Recovery verification is allowed only after explicit approval.")
        state.phase = Phase.VERIFY
        result = probe()
        state.recovery_observations.append(self._evidence_from(result, "recovery"))
        state.phase = Phase.COMPLETE if result.succeeded else Phase.BLOCKED
        return state

    def _collect(self, state: IncidentState, tool_name: str) -> None:
        result = self.diagnostics.invoke(tool_name)
        state.tool_calls.append(self._tool_call(result))
        evidence = self._evidence_from(result, str(len(state.evidence) + 1))
        state.add_evidence(evidence)
        if state.hypotheses:
            current = state.hypotheses[-1]
            status = "supported" if result.succeeded else "rejected"
            state.hypotheses[-1] = type(current)(
                id=current.id,
                claim=current.claim,
                rationale=current.rationale,
                status=status,
                evidence_ids=(evidence.id,),
            )

    @staticmethod
    def _tool_call(result: ToolResult):
        from .models import ToolCall

        return ToolCall(result.tool_name, {}, result.succeeded, result.summary)

    @staticmethod
    def _evidence_from(result: ToolResult, suffix: str) -> Evidence:
        return Evidence(
            id=f"e{suffix}",
            tool_name=result.tool_name,
            observation=result.summary,
            raw=result.raw,
            collected_at=datetime.now(UTC).isoformat(),
            source_kind=result.source_kind,
        )
