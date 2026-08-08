from __future__ import annotations

from pathlib import Path

from langgraph.types import Command

from agent.langgraph_runtime import build_graph_with_sqlite
from agent.models import IncidentState, Phase
from agent.tools import FixtureDiagnostics
from evals.scenarios import SCENARIOS


def test_durable_graph_interrupts_and_records_named_approval(tmp_path: Path) -> None:
    scenario = SCENARIOS[0]
    graph = build_graph_with_sqlite(
        FixtureDiagnostics(scenario.fixtures),
        scenario.investigator,
        str(tmp_path / "agent.sqlite"),
    )
    config = {"configurable": {"thread_id": "approval-test"}}

    paused = graph.invoke(
        {"incident": IncidentState(scenario.id, scenario.symptom)},
        config=config,
    )
    assert paused["incident"].phase is Phase.AWAITING_APPROVAL
    assert paused.get("__interrupt__"), "the graph must pause at a real LangGraph interrupt"

    resumed = graph.invoke(
        Command(
            resume={
                "approved": True,
                "approved_by": "test-instructor",
                "note": "bounded fixture",
            }
        ),
        config=config,
    )
    incident = resumed["incident"]
    assert incident.phase is Phase.REMEDIATE
    assert incident.approval is not None
    assert incident.approval.approved_by == "test-instructor"
    assert incident.approval.note == "bounded fixture"

