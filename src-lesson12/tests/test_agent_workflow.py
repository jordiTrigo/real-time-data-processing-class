from __future__ import annotations

import unittest

from agent.investigators import ScriptedInvestigator, ScriptedStep
from agent.models import Approval, IncidentState, Phase, RemediationProposal, Severity
from agent.tools import FixtureDiagnostics, ToolResult
from agent.workflow import ApprovalRequired, IncidentWorkflow


class IncidentWorkflowTests(unittest.TestCase):
    def setUp(self) -> None:
        proposal = RemediationProposal(
            action_id="restart-processor",
            description="Restart the bounded Lesson 12 processor profile.",
            rollback="Restore the healthy profile.",
            expected_recovery_signal="Lag drains.",
            risk="Requires instructor approval.",
        )
        self.workflow = IncidentWorkflow(
            FixtureDiagnostics(
                {"processor_metrics": ToolResult("processor_metrics", True, "lag=42", "lag=42")}
            ),
            ScriptedInvestigator(
                severity=Severity.P2,
                root_cause="A bounded test failure.",
                diagnosis="Evidence proves the test failure.",
                steps=(ScriptedStep("processor_metrics", "Lag is growing.", "Inspect metrics."),),
                remediation=proposal,
            ),
        )

    def test_evidence_is_linked_to_hypothesis_and_report(self) -> None:
        state = self.workflow.run(IncidentState("test", "Lag rises"))
        self.assertEqual(state.phase, Phase.AWAITING_APPROVAL)
        self.assertEqual(state.hypotheses[0].status, "supported")
        self.assertEqual(state.hypotheses[0].evidence_ids, ("e1",))
        self.assertEqual(state.report.evidence_ids, ("e1",))

    def test_remediation_cannot_cross_approval_gate(self) -> None:
        state = self.workflow.run(IncidentState("test", "Lag rises"))
        with self.assertRaises(ApprovalRequired):
            self.workflow.verify_recovery(state, lambda: ToolResult("probe", True, "ok", "ok"))
        self.workflow.approve(state, Approval("restart-processor", "instructor", True))
        self.workflow.verify_recovery(state, lambda: ToolResult("probe", True, "lag=0", "lag=0"))
        self.assertEqual(state.phase, Phase.COMPLETE)

    def test_wrong_approval_is_rejected(self) -> None:
        state = self.workflow.run(IncidentState("test", "Lag rises"))
        with self.assertRaises(ApprovalRequired):
            self.workflow.approve(state, Approval("drop-everything", "instructor", True))

    def test_retrieved_guidance_is_not_labeled_live_evidence(self) -> None:
        workflow = IncidentWorkflow(
            FixtureDiagnostics(
                {
                    "runbook_context": ToolResult(
                        "runbook_context",
                        True,
                        "guidance",
                        "text",
                        "retrieved_guidance",
                    )
                }
            ),
            ScriptedInvestigator(
                severity=Severity.P3,
                root_cause="Test",
                diagnosis="Test",
                steps=(ScriptedStep("runbook_context", "Read guidance", "Plan only"),),
                remediation=RemediationProposal("test", "test", "test", "test", "test"),
            ),
        )
        state = workflow.run(IncidentState("test", "test"))
        self.assertEqual(state.evidence[0].source_kind, "retrieved_guidance")

    def test_report_without_live_evidence_is_blocked(self) -> None:
        proposal = RemediationProposal("test", "test", "test", "test", "test")
        workflow = IncidentWorkflow(
            FixtureDiagnostics({}),
            ScriptedInvestigator(
                severity=Severity.P3,
                root_cause="Unsupported claim",
                diagnosis="No live observation.",
                steps=(),
                remediation=proposal,
            ),
        )
        state = workflow.run(IncidentState("test", "test"))
        self.assertEqual(state.phase, Phase.BLOCKED)
        self.assertIn("live observation", state.errors[0])
