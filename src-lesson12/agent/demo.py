"""Projectable Lesson 12 incident-agent demo.

The default is deterministic and offline. A real model or real LangGraph runtime
is opt-in, never selected implicitly.

Examples::

    python -m agent.demo --scenario poison-deserialization
    python -m agent.demo --runtime langgraph --checkpoint .state/agent.sqlite \
        --thread-id class-a
    INCIDENT_AGENT_BASE_URL=... INCIDENT_AGENT_API_KEY=... INCIDENT_AGENT_MODEL=... \
        python -m agent.demo --investigator live --runtime langgraph

The LangGraph run pauses at its approval interrupt. Resume it with
``--decision approve --approved-by instructor --note "..."``. Approval is
recorded but no remediation command exists in this package.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from agent.investigators import Investigator
from agent.llm import OpenAICompatibleInvestigator
from agent.models import IncidentState
from agent.tools import FixtureDiagnostics, Lesson12Diagnostics, ToolCatalog
from agent.workflow import IncidentWorkflow
from evals.scenarios import SCENARIOS


def _render(state: IncidentState) -> dict[str, Any]:
    return {
        "incident_id": state.incident_id,
        "phase": state.phase.value,
        "tool_trajectory": [asdict(item) for item in state.tool_calls],
        "evidence_ledger": [asdict(item) for item in state.evidence],
        "hypothesis_ledger": [asdict(item) for item in state.hypotheses],
        "report": asdict(state.report) if state.report else None,
        "approval": asdict(state.approval) if state.approval else None,
        "errors": state.errors,
    }


def _select_components(args: argparse.Namespace, scenario: Any) -> tuple[ToolCatalog, Investigator]:
    if args.investigator == "live":
        title = getattr(scenario, "title", scenario.id)
        context_query = f"{title} {scenario.symptom}"
        return (
            Lesson12Diagnostics(context_query=context_query),
            OpenAICompatibleInvestigator.from_environment(),
        )
    return FixtureDiagnostics(scenario.fixtures), scenario.investigator


def _run_langgraph(
    diagnostics: ToolCatalog,
    investigator: Investigator,
    state: IncidentState,
    checkpoint: Path,
    thread_id: str,
) -> IncidentState:
    from agent.langgraph_runtime import build_graph_with_sqlite

    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    graph = build_graph_with_sqlite(diagnostics, investigator, str(checkpoint))
    output = graph.invoke({"incident": state}, config={"configurable": {"thread_id": thread_id}})
    return output["incident"]


def _resume_langgraph(
    diagnostics: ToolCatalog,
    investigator: Investigator,
    checkpoint: Path,
    thread_id: str,
    decision: str,
    approved_by: str,
    note: str,
) -> IncidentState:
    from langgraph.types import Command

    from agent.langgraph_runtime import build_graph_with_sqlite

    if not checkpoint.exists():
        raise FileNotFoundError(f"No durable checkpoint exists at {checkpoint}.")
    graph = build_graph_with_sqlite(diagnostics, investigator, str(checkpoint))
    output = graph.invoke(
        Command(
            resume={
                "approved": decision == "approve",
                "approved_by": approved_by,
                "note": note,
            }
        ),
        config={"configurable": {"thread_id": thread_id}},
    )
    return output["incident"]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Projectable, evidence-first Lesson 12 incident-agent demo"
    )
    parser.add_argument(
        "--scenario", choices=[item.id for item in SCENARIOS], default="poison-deserialization"
    )
    parser.add_argument("--runtime", choices=("stdlib", "langgraph"), default="stdlib")
    parser.add_argument("--investigator", choices=("scripted", "live"), default="scripted")
    parser.add_argument("--checkpoint", type=Path, default=Path(".state/incident-agent.sqlite"))
    parser.add_argument("--thread-id", default="lesson12-demo")
    parser.add_argument("--decision", choices=("approve", "reject"))
    parser.add_argument("--approved-by", default="instructor")
    parser.add_argument("--note", default="")
    args = parser.parse_args()
    scenario = next(item for item in SCENARIOS if item.id == args.scenario)
    diagnostics, investigator = _select_components(args, scenario)
    initial = IncidentState(scenario.id, scenario.symptom)
    if args.decision and args.runtime != "langgraph":
        parser.error("--decision only resumes a durable --runtime langgraph run.")
    if args.decision:
        state = _resume_langgraph(
            diagnostics,
            investigator,
            args.checkpoint,
            args.thread_id,
            args.decision,
            args.approved_by,
            args.note,
        )
    elif args.runtime == "langgraph":
        state = _run_langgraph(diagnostics, investigator, initial, args.checkpoint, args.thread_id)
    else:
        state = IncidentWorkflow(diagnostics, investigator).run(initial)
    print(json.dumps(_render(state), indent=2, default=str))
    if args.decision:
        print("Approval decision persisted; remediation was not executed.")
    elif args.runtime == "langgraph":
        print(
            "LangGraph is paused at the durable approval interrupt; remediation was not executed."
        )
    else:
        print("Offline workflow stopped at the approval gate; remediation was not executed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
