"""Optional real LangGraph runtime for the same evidence-first workflow.

Install ``langgraph`` in the Lesson 12 environment to use this module. The normal
offline lesson and unit tests use :class:`agent.workflow.IncidentWorkflow`, which
has identical node decisions and needs no network/model dependency.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypedDict

from .models import (
    Approval,
    Evidence,
    Hypothesis,
    IncidentReport,
    IncidentState,
    Phase,
    RemediationProposal,
    Severity,
    ToolCall,
)

if TYPE_CHECKING:
    from .investigators import Investigator
    from .tools import ToolCatalog


class GraphState(TypedDict):
    incident: IncidentState


def build_graph(
    diagnostics: ToolCatalog, investigator: Investigator, checkpointer: Any = None
) -> Any:
    """Build an executable ``StateGraph``.

    The approval node pauses with LangGraph ``interrupt()`` and resumes only with
    ``{"approved": bool, "approved_by": str, "note": str}``. No graph node can
    run a remediation command after an approval.
    """

    try:
        from langgraph.graph import END, START, StateGraph
        from langgraph.types import interrupt
    except ImportError as error:  # pragma: no cover - optional classroom extra
        raise RuntimeError("Install 'langgraph' to run the durable graph runtime.") from error

    # Reuse the exact collection semantics of the stdlib fallback.
    from .workflow import IncidentWorkflow

    fallback = IncidentWorkflow(diagnostics, investigator)

    def observe(data: GraphState) -> GraphState:
        data["incident"].phase = Phase.INVESTIGATE
        return data

    def investigate(data: GraphState) -> GraphState:
        state = data["incident"]
        decision = investigator.decide(state, diagnostics.names())
        if decision.hypothesis:
            state.add_hypothesis(decision.hypothesis)
        if decision.tool_name:
            fallback._collect(state, decision.tool_name)  # shared, read-only node operation
        elif decision.report:
            if not fallback.has_live_evidence(state):
                state.phase = Phase.BLOCKED
                state.errors.append(
                    "A report needs at least one live observation; retrieved guidance is not proof."
                )
            else:
                state.report = decision.report
                state.proposal = decision.report.proposed_remediation
                state.phase = Phase.AWAITING_APPROVAL if state.proposal else Phase.COMPLETE
        else:
            state.phase = Phase.BLOCKED
            state.errors.append("Investigator returned neither a tool nor a structured report.")
        return data

    def next_node(data: GraphState) -> str:
        phase = data["incident"].phase
        if phase is Phase.INVESTIGATE:
            return "investigate"
        if phase is Phase.AWAITING_APPROVAL:
            return "approval"
        return END

    def approval(data: GraphState) -> GraphState:
        state = data["incident"]
        if state.proposal is None:
            state.phase = Phase.COMPLETE
            return data
        response = interrupt(
            {
                "incident_id": state.incident_id,
                "proposal": {
                    "action_id": state.proposal.action_id,
                    "description": state.proposal.description,
                    "risk": state.proposal.risk,
                    "expected_recovery_signal": state.proposal.expected_recovery_signal,
                },
                "instruction": (
                    "Resume with approved, approved_by, and note. No remediation is executed."
                ),
            }
        )
        if not isinstance(response, dict) or not isinstance(response.get("approved"), bool):
            state.phase = Phase.BLOCKED
            state.errors.append("Approval resume payload must include boolean approved.")
            return data
        approved = response["approved"]
        state.approval = Approval(
            action_id=state.proposal.action_id,
            approved_by=str(response.get("approved_by", "unnamed-human")),
            approved=approved,
            note=str(response.get("note", "")),
        )
        # Approval changes authority, not reality. The host still has to execute
        # the separately scoped action and verify recovery before completion.
        state.phase = Phase.REMEDIATE if approved else Phase.REJECTED
        return data

    graph = StateGraph(GraphState)
    graph.add_node("observe", observe)
    graph.add_node("investigate", investigate)
    graph.add_node("approval", approval)
    graph.add_edge(START, "observe")
    graph.add_edge("observe", "investigate")
    graph.add_conditional_edges("investigate", next_node)
    graph.add_edge("approval", END)
    return graph.compile(checkpointer=checkpointer)


def build_graph_with_memory(diagnostics: ToolCatalog, investigator: Investigator) -> Any:
    """Build the graph with LangGraph's in-memory checkpoint saver for class demos."""

    try:
        from langgraph.checkpoint.memory import MemorySaver
    except ImportError as error:  # pragma: no cover - optional classroom extra
        raise RuntimeError("Install 'langgraph' to enable checkpointing.") from error
    return build_graph(diagnostics, investigator, checkpointer=MemorySaver())


def build_graph_with_sqlite(
    diagnostics: ToolCatalog, investigator: Investigator, checkpoint_path: str
) -> Any:
    """Build with durable SQLite checkpoints that survive a process restart.

    This needs the optional ``langgraph-checkpoint-sqlite`` extra in addition to
    ``langgraph``. Callers provide a Lesson 12-local path such as
    ``.state/incident-agent.sqlite`` and a stable ``thread_id`` in graph config.
    """

    try:
        import sqlite3

        from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
        from langgraph.checkpoint.sqlite import SqliteSaver
    except ImportError as error:  # pragma: no cover - optional classroom extra
        raise RuntimeError(
            "Install 'langgraph-checkpoint-sqlite' to persist incident checkpoints."
        ) from error
    connection = sqlite3.connect(checkpoint_path, check_same_thread=False)
    serde = JsonPlusSerializer(
        allowed_msgpack_modules=(
            Approval,
            Evidence,
            Hypothesis,
            IncidentReport,
            IncidentState,
            Phase,
            RemediationProposal,
            Severity,
            ToolCall,
        )
    )
    return build_graph(diagnostics, investigator, checkpointer=SqliteSaver(connection, serde=serde))
