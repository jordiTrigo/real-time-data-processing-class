"""Small, allow-listed read-only views of the Lesson 12 pipeline.

These tools deliberately expose observations rather than a shell.  A model cannot
invent a command, choose a host, or alter a query.  The only subprocesses below are
fixed read-only inspection commands from the Lesson 12 runbook.
"""

from __future__ import annotations

import json
import subprocess
from base64 import b64encode
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .resources import LexicalRunbookRetriever


@dataclass(frozen=True)
class ToolResult:
    tool_name: str
    succeeded: bool
    summary: str
    raw: str
    source_kind: str = "live_observation"


class DiagnosticTool(Protocol):
    name: str

    def invoke(self) -> ToolResult: ...


class ToolCatalog(Protocol):
    def invoke(self, name: str) -> ToolResult: ...

    def names(self) -> tuple[str, ...]: ...


def _http_get(name: str, url: str, summary: Callable[[str], str]) -> ToolResult:
    try:
        with urlopen(url, timeout=3) as response:
            raw = response.read().decode("utf-8", errors="replace")
        return ToolResult(name, True, summary(raw), raw)
    except (OSError, URLError) as error:
        return ToolResult(name, False, f"{name} unavailable: {error}", "")


def _http_post_select(name: str, url: str, query: str, username: str, password: str) -> ToolResult:
    credential = b64encode(f"{username}:{password}".encode()).decode()
    request = Request(
        url,
        data=query.encode(),
        headers={"Authorization": f"Basic {credential}"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=5) as response:
            raw = response.read().decode("utf-8", errors="replace")
        return ToolResult(name, True, raw.strip() or "query returned no rows", raw)
    except (OSError, URLError) as error:
        return ToolResult(name, False, f"{name} unavailable: {error}", "")


def _http_expect_status(name: str, url: str, expected_status: int) -> ToolResult:
    """Treat an expected HTTP error as diagnostic evidence, not a tool failure."""

    try:
        with urlopen(url, timeout=3) as response:
            raw = response.read().decode("utf-8", errors="replace")
            return ToolResult(
                name, False, f"expected HTTP {expected_status}, got {response.status}", raw
            )
    except HTTPError as error:
        raw = error.read().decode("utf-8", errors="replace")
        succeeded = error.code == expected_status
        return ToolResult(name, succeeded, f"schema lookup returned HTTP {error.code}", raw)
    except (OSError, URLError) as error:
        return ToolResult(name, False, f"{name} unavailable: {error}", "")


class Lesson12Diagnostics:
    """Read-only tools over the isolated Lesson 12 ports and ``l12-*`` stack."""

    def __init__(
        self, lesson12_dir: Path | str | None = None, context_query: str = "incident"
    ) -> None:
        self.lesson12_dir = Path(lesson12_dir or Path(__file__).parents[1])
        self.context_query = context_query
        self.runbooks = LexicalRunbookRetriever()
        self._tools: Mapping[str, Callable[[], ToolResult]] = {
            "runbook_context": self.runbook_context,
            "connect_service_status": self.connect_service_status,
            "connector_status": self.connector_status,
            "schema_versions": self.schema_versions,
            "unknown_schema_id": self.unknown_schema_id,
            "processor_metrics": self.processor_metrics,
            "poison_probe_logs": self.poison_probe_logs,
            "kafka_partition_offsets": self.kafka_partition_offsets,
            "clickhouse_part_stats": self.clickhouse_part_stats,
            "replication_slot_status": self.replication_slot_status,
            "source_business_outliers": self.source_business_outliers,
            "retention_topic_config": self.retention_topic_config,
            "kafka_log_dirs": self.kafka_log_dirs,
            "stream_processor_logs": self.stream_processor_logs,
            "pipeline_preflight": self.pipeline_preflight,
        }

    def names(self) -> tuple[str, ...]:
        return tuple(self._tools)

    def invoke(self, name: str) -> ToolResult:
        try:
            return self._tools[name]()
        except KeyError:
            return ToolResult(name, False, "tool is not in the read-only allow-list", "")

    def connector_status(self) -> ToolResult:
        return _http_get(
            "connector_status",
            "http://localhost:28083/connectors/orders-cdc/status",
            lambda raw: (
                "Debezium connector/task status retrieved" if raw else "empty connector status"
            ),
        )

    def connect_service_status(self) -> ToolResult:
        """Inspect Compose state even when the paused REST service cannot reply."""

        return self._run(
            "connect_service_status",
            ["docker", "compose", "ps", "--format", "json", "connect"],
        )

    def runbook_context(self) -> ToolResult:
        """Retrieve local guidance; it is explicitly labelled as non-live evidence."""

        raw = self.runbooks.render(self.context_query)
        return ToolResult(
            "runbook_context",
            True,
            "Retrieved local runbook guidance; validate it against live observations.",
            raw,
            source_kind="retrieved_guidance",
        )

    def schema_versions(self) -> ToolResult:
        return _http_get(
            "schema_versions",
            "http://localhost:28081/subjects/cdc.public.orders-value/versions",
            lambda raw: f"registered writer schemas: {raw}",
        )

    def unknown_schema_id(self) -> ToolResult:
        return _http_expect_status(
            "unknown_schema_id",
            "http://localhost:28081/schemas/ids/999999",
            expected_status=404,
        )

    def processor_metrics(self) -> ToolResult:
        return _http_get(
            "processor_metrics",
            "http://localhost:29108/metrics",
            lambda raw: (
                "processor Prometheus metrics retrieved" if raw else "empty metrics response"
            ),
        )

    def poison_probe_logs(self) -> ToolResult:
        return self._run(
            "poison_probe_logs",
            [
                "docker",
                "compose",
                "--profile",
                "scenarios",
                "logs",
                "--no-color",
                "--tail",
                "80",
                "poison-probe",
            ],
        )

    def kafka_partition_offsets(self) -> ToolResult:
        return self._compose_exec(
            "kafka_partition_offsets",
            [
                "kafka",
                "/opt/kafka/bin/kafka-get-offsets.sh",
                "--bootstrap-server",
                "localhost:9092",
                "--topic",
                "cdc.public.orders",
            ],
        )

    def clickhouse_part_stats(self) -> ToolResult:
        return _http_post_select(
            "clickhouse_part_stats",
            "http://localhost:28123/",
            "SELECT partition, count() AS active_parts, sum(rows) AS rows "
            "FROM system.parts WHERE active AND database = 'lesson12' AND table = 'orders_current' "
            "GROUP BY partition FORMAT TSVWithNames",
            username="lesson12",
            password="lesson12",
        )

    def replication_slot_status(self) -> ToolResult:
        return self._compose_exec(
            "replication_slot_status",
            [
                "postgres",
                "psql",
                "-U",
                "lesson12",
                "-d",
                "orders",
                "-At",
                "-c",
                (
                    "SELECT slot_name, active, pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn) "
                    "AS retained_wal_bytes FROM pg_replication_slots;"
                ),
            ],
        )

    def source_business_outliers(self) -> ToolResult:
        return self._compose_exec(
            "source_business_outliers",
            [
                "postgres",
                "psql",
                "-U",
                "lesson12",
                "-d",
                "orders",
                "-At",
                "-c",
                "SELECT id, amount, updated_at FROM orders ORDER BY amount DESC LIMIT 15;",
            ],
        )

    def retention_topic_config(self) -> ToolResult:
        return self._compose_exec(
            "retention_topic_config",
            [
                "kafka",
                "/opt/kafka/bin/kafka-configs.sh",
                "--bootstrap-server",
                "localhost:9092",
                "--entity-type",
                "topics",
                "--entity-name",
                "l12.retention-risk",
                "--describe",
            ],
        )

    def kafka_log_dirs(self) -> ToolResult:
        return self._compose_exec(
            "kafka_log_dirs",
            [
                "kafka",
                "bash",
                "-lc",
                "du -sh /var/lib/kafka/data && df -h /var/lib/kafka/data",
            ],
        )

    def stream_processor_logs(self) -> ToolResult:
        return self._run(
            "stream_processor_logs",
            [
                "docker",
                "compose",
                "logs",
                "--no-color",
                "--tail",
                "200",
                "stream-processor",
            ],
        )

    def pipeline_preflight(self) -> ToolResult:
        return self._run("pipeline_preflight", ["uv", "run", "python", "scripts/preflight.py"])

    def _compose_exec(self, name: str, service_command: list[str]) -> ToolResult:
        return self._run(name, ["docker", "compose", "exec", "-T", *service_command])

    def _run(self, name: str, command: list[str]) -> ToolResult:
        try:
            completed = subprocess.run(
                command,
                cwd=self.lesson12_dir,
                text=True,
                capture_output=True,
                timeout=10,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            return ToolResult(name, False, f"{name} unavailable: {error}", "")
        raw = (completed.stdout + completed.stderr).strip()
        return ToolResult(name, completed.returncode == 0, raw[:500] or "completed", raw)


class FixtureDiagnostics:
    """In-memory catalog used by unit tests and the six offline scenario evals."""

    def __init__(self, fixtures: Mapping[str, ToolResult]) -> None:
        self.fixtures = dict(fixtures)
        self.invocations: list[str] = []

    def names(self) -> tuple[str, ...]:
        return tuple(self.fixtures)

    def invoke(self, name: str) -> ToolResult:
        self.invocations.append(name)
        return self.fixtures.get(name, ToolResult(name, False, "fixture not supplied", ""))


def result_from_json(name: str, raw: str) -> ToolResult:
    """Useful for MCP callers that pass a pre-collected response into a lesson demo."""

    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        value = raw
    return ToolResult(name, True, str(value), raw)
