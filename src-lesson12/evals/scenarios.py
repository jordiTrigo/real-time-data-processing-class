"""The six capstone incidents as repeatable offline agent-evaluation cases."""

# ruff: noqa: E501

from __future__ import annotations

from dataclasses import dataclass

from agent.investigators import ScriptedInvestigator, ScriptedStep
from agent.models import RemediationProposal, Severity
from agent.tools import ToolResult


@dataclass(frozen=True)
class EvaluationScenario:
    id: str
    symptom: str
    root_cause: str
    required_tools: tuple[str, ...]
    fixtures: dict[str, ToolResult]
    investigator: ScriptedInvestigator
    recovery_fixture: ToolResult


def _proposal(action_id: str, description: str, recovery: str) -> RemediationProposal:
    return RemediationProposal(
        action_id=action_id,
        description=description,
        rollback="Revert the bounded Lesson 12 scenario profile and re-check the golden path.",
        expected_recovery_signal=recovery,
        risk="Changes are proposals only; an instructor must approve a scoped action.",
    )


def _scenario(
    *,
    id: str,
    symptom: str,
    root_cause: str,
    severity: Severity,
    steps: tuple[ScriptedStep, ...],
    remediation: str,
    recovery: str,
) -> EvaluationScenario:
    steps = (
        ScriptedStep(
            "runbook_context",
            "Guidance provides an investigation sequence, not proof of a root cause.",
            "Retrieve the local runbook before collecting live evidence.",
        ),
        *steps,
    )
    fixtures = {
        step.tool_name: ToolResult(
            step.tool_name,
            True,
            "Retrieved guidance; validate it against live observations."
            if step.tool_name == "runbook_context"
            else f"evidence for {root_cause}",
            f"{step.tool_name}: {root_cause}",
            source_kind="retrieved_guidance"
            if step.tool_name == "runbook_context"
            else "live_observation",
        )
        for step in steps
    }
    return EvaluationScenario(
        id=id,
        symptom=symptom,
        root_cause=root_cause,
        required_tools=tuple(step.tool_name for step in steps),
        fixtures=fixtures,
        investigator=ScriptedInvestigator(
            severity=severity,
            root_cause=root_cause,
            diagnosis=f"The evidence ledger supports: {root_cause}.",
            steps=steps,
            remediation=_proposal(f"remediate-{id}", remediation, recovery),
        ),
        recovery_fixture=ToolResult("recovery_probe", True, recovery, recovery),
    )


SCENARIOS: tuple[EvaluationScenario, ...] = (
    _scenario(
        id="poison-deserialization",
        symptom="The isolated poison probe retries an unknown Avro schema ID; the orders stream is untouched.",
        root_cause="An isolated Confluent-framed record declares schema ID 999999, which Schema Registry cannot resolve.",
        severity=Severity.P1,
        steps=(
            ScriptedStep(
                "poison_probe_logs",
                "The isolated probe fails at schema resolution.",
                "Inspect bounded probe logs.",
            ),
            ScriptedStep(
                "unknown_schema_id",
                "Schema ID 999999 is absent.",
                "Confirm Registry's expected 404.",
            ),
        ),
        remediation="Validate framing/schema lookup, then route the isolated record and offset to a quarantine path.",
        recovery="The poison probe records a bounded quarantine decision and the healthy orders canary remains unaffected.",
    ),
    _scenario(
        id="partition-hotspot",
        symptom="One Kafka partition advances far faster than the other two.",
        root_cause="A stable hot order key concentrates the bounded CDC update burst in one Kafka partition.",
        severity=Severity.P2,
        steps=(
            ScriptedStep(
                "kafka_partition_offsets",
                "One broker partition advances much faster.",
                "Inspect broker offsets by partition.",
            ),
            ScriptedStep(
                "clickhouse_part_stats",
                "Current-state storage remains healthy.",
                "Avoid blaming the sink for broker skew.",
            ),
        ),
        remediation="Choose a key with enough cardinality, or deliberately shard while preserving per-entity ordering.",
        recovery="The maximum partition lag approaches the median after a replay-safe keying rollout.",
    ),
    _scenario(
        id="paused-connector-slot-risk",
        symptom="Postgres writes continue while Debezium's slot falls behind.",
        root_cause="Paused Kafka Connect stops Debezium progress, leaving the logical replication slot behind the current WAL LSN.",
        severity=Severity.P1,
        steps=(
            ScriptedStep(
                "connect_service_status",
                "The Connect service is paused.",
                "Check service state without depending on its paused REST endpoint.",
            ),
            ScriptedStep(
                "replication_slot_status",
                "Retained WAL grows at the slot.",
                "Read slot LSN distance.",
            ),
        ),
        remediation="Restore the connector and verify slot advancement before declaring recovery.",
        recovery="The slot advances after the connector resumes and retained WAL stops growing.",
    ),
    _scenario(
        id="silent-data-contract",
        symptom="Revenue is inflated although every service is healthy and every Avro record decodes.",
        root_cause="A valid cents-versus-dollars semantic error multiplied a bounded set of source amounts by 100.",
        severity=Severity.P1,
        steps=(
            ScriptedStep(
                "source_business_outliers",
                "Source amounts contain 100x outliers.",
                "Inspect business-value distribution.",
            ),
            ScriptedStep(
                "schema_versions",
                "Schema compatibility is unchanged.",
                "Show why syntactic compatibility missed semantics.",
            ),
        ),
        remediation="Restore the recorded source amounts and add unit/range reconciliation checks beside schema compatibility.",
        recovery="Known-value amounts agree from Postgres through ClickHouse and the API.",
    ),
    _scenario(
        id="clickhouse-tiny-parts",
        symptom="Active parts and merge work rise after bounded one-row inserts.",
        root_cause="Forty bounded one-row inserts created excessive active parts and merge pressure.",
        severity=Severity.P2,
        steps=(
            ScriptedStep(
                "clickhouse_part_stats", "Active part count is excessive.", "Inspect system.parts."
            ),
            ScriptedStep(
                "processor_metrics",
                "Sink pressure is visible in batch metrics.",
                "Correlate write pressure.",
            ),
        ),
        remediation="Batch sink writes and use an approved one-off merge only as controlled recovery.",
        recovery="Active parts trend down and sink latency returns below the trigger interval.",
    ),
    _scenario(
        id="kafka-retention-risk",
        symptom="An isolated capped topic advertises infinite time retention without filling a disk.",
        root_cause="The isolated l12.retention-risk topic has retention.ms=-1 despite a bounded 1 MiB fixture limit.",
        severity=Severity.P1,
        steps=(
            ScriptedStep(
                "retention_topic_config",
                "Fixture topic retains forever by time policy.",
                "Inspect explicit topic configuration.",
            ),
            ScriptedStep(
                "kafka_log_dirs",
                "Fixture disk use is deliberately bounded.",
                "Separate capacity math from disk exhaustion.",
            ),
        ),
        remediation="Set retention time and byte budgets from measured ingress, recovery window, and headroom.",
        recovery="The fixture topic shows approved limits while its bounded sample remains inspectable.",
    ),
)
