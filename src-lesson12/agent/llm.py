"""Optional LLM adapter configuration.

The course never assumes a particular provider or a "current" model.  Production
adapters should turn a model response into :class:`InvestigationDecision`; tests
use ScriptedInvestigator instead.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from urllib.request import Request, urlopen

from .investigators import InvestigationDecision, Investigator
from .models import (
    Hypothesis,
    IncidentReport,
    IncidentState,
    RemediationProposal,
    Severity,
)

DecisionFunction = Callable[[IncidentState, tuple[str, ...], str], InvestigationDecision]


@dataclass
class EnvironmentLLMInvestigator(Investigator):
    """Provider-neutral adapter whose model identifier comes only from the environment."""

    model: str
    decide_with_model: DecisionFunction

    @classmethod
    def from_environment(cls, decide_with_model: DecisionFunction) -> EnvironmentLLMInvestigator:
        model = os.environ.get("INCIDENT_AGENT_MODEL")
        if not model:
            raise RuntimeError("Set INCIDENT_AGENT_MODEL to enable a real LLM investigator.")
        return cls(model=model, decide_with_model=decide_with_model)

    def decide(
        self, state: IncidentState, available_tools: tuple[str, ...]
    ) -> InvestigationDecision:
        return self.decide_with_model(state, available_tools, self.model)


@dataclass
class OpenAICompatibleInvestigator(Investigator):
    """Optional real model adapter using an OpenAI-compatible chat endpoint.

    It is deliberately configured entirely by ``INCIDENT_AGENT_BASE_URL``,
    ``INCIDENT_AGENT_API_KEY``, and ``INCIDENT_AGENT_MODEL``. The model can select
    only listed read-only tools or return a structured proposal; it has no shell or
    remediation tool to call.
    """

    base_url: str
    api_key: str
    model: str

    @classmethod
    def from_environment(cls) -> OpenAICompatibleInvestigator:
        values = {
            "base_url": os.environ.get("INCIDENT_AGENT_BASE_URL"),
            "api_key": os.environ.get("INCIDENT_AGENT_API_KEY"),
            "model": os.environ.get("INCIDENT_AGENT_MODEL"),
        }
        missing = [name for name, value in values.items() if not value]
        if missing:
            raise RuntimeError(
                "Set INCIDENT_AGENT_BASE_URL, INCIDENT_AGENT_API_KEY, and INCIDENT_AGENT_MODEL."
            )
        return cls(**values)  # type: ignore[arg-type]

    def decide(
        self, state: IncidentState, available_tools: tuple[str, ...]
    ) -> InvestigationDecision:
        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are an evidence-first incident investigator. Return JSON only. "
                        "Either return {tool_name, claim, rationale}; choose exactly one supplied "
                        "read-only tool. Or return {report: {severity, root_cause, diagnosis, "
                        "confidence, remediation, recovery_signal}}. Guidance is not proof; "
                        "do not request or execute remediation."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "incident_id": state.incident_id,
                            "symptom": state.symptom,
                            "tools": available_tools,
                            "evidence": [item.observation for item in state.evidence],
                        }
                    ),
                },
            ],
        }
        url = f"{self.base_url.rstrip('/')}/chat/completions"
        request = Request(
            url,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urlopen(request, timeout=30) as response:
            raw = json.loads(response.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
        decision = json.loads(content)
        tool_name = decision.get("tool_name")
        if tool_name:
            if tool_name not in available_tools:
                raise ValueError("Model selected a tool outside the allow-list.")
            return InvestigationDecision(
                tool_name=tool_name,
                hypothesis=Hypothesis(
                    id=f"h{len(state.hypotheses) + 1}",
                    claim=str(decision.get("claim", "Collect evidence.")),
                    rationale=str(decision.get("rationale", "Validate the current hypothesis.")),
                ),
            )
        report_data = decision.get("report")
        if not isinstance(report_data, dict):
            raise TypeError(
                "Model response must contain an allow-listed tool or a structured report."
            )
        remediation_text = str(report_data.get("remediation", "No remediation proposed."))
        recovery = str(report_data.get("recovery_signal", "Define a recovery signal."))
        proposal = RemediationProposal(
            action_id=f"llm-proposal-{state.incident_id}",
            description=remediation_text,
            rollback="A human must define and approve the rollback before execution.",
            expected_recovery_signal=recovery,
            risk="Model-proposed remediation requires named human approval.",
        )
        return InvestigationDecision(
            report=IncidentReport(
                incident_id=state.incident_id,
                severity=Severity(str(report_data.get("severity", "P3"))),
                root_cause=str(report_data.get("root_cause", "Insufficient evidence.")),
                confidence=float(report_data.get("confidence", 0.0)),
                evidence_ids=state.evidence_ids(),
                diagnosis=str(report_data.get("diagnosis", "No diagnosis supplied.")),
                proposed_remediation=proposal,
                expected_recovery_signal=recovery,
                safety_note="The model cannot execute this proposal.",
            )
        )
