"""The bounded failure catalogue used by the Lesson 12 incident lab.

Commands are data, rather than opaque scripts, so both students and an incident
agent can inspect exactly what a scenario is allowed to do.  No command runs
unless the CLI receives ``--apply``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Command:
    """One bounded command, with a human-readable purpose."""

    label: str
    argv: tuple[str, ...]


@dataclass(frozen=True)
class Scenario:
    """A single independently activatable classroom incident."""

    id: str
    title: str
    category: str
    safety_boundary: str
    timebox_seconds: int
    symptom: str
    evidence: tuple[str, ...]
    fix: str
    prevention: str
    activate: tuple[Command, ...]
    reset: tuple[Command, ...]
    probes: tuple[Command, ...]


def _compose(*args: str) -> tuple[str, ...]:
    """Use Lesson 12's self-contained stack without changing its Compose file."""
    return ("docker", "compose", "-f", "{compose_file}", *args)


def _exec(service: str, *args: str) -> tuple[str, ...]:
    return _compose("exec", "-T", service, *args)


_POISON_TOPIC = "l12.poison-boundary"
_RETENTION_TOPIC = "l12.retention-risk"


SCENARIOS: dict[str, Scenario] = {
    "poison-deserialization": Scenario(
        id="poison-deserialization",
        title="Poison record at the Avro deserialization boundary",
        category="application/data",
        safety_boundary=(
            "Writes one five-byte Confluent-shaped record to an isolated topic, never "
            "to cdc.public.orders. Only the profile-gated poison probe consumes it."
        ),
        timebox_seconds=60,
        symptom=(
            "The probe/processor repeatedly fails while resolving an unknown schema ID; "
            "the healthy orders topic and checkpoint remain untouched."
        ),
        evidence=(
            "The record starts with Confluent magic byte 0 but declares schema ID 999999.",
            "Schema Registry GET /schemas/ids/999999 returns 404.",
            "A failing consumer retries the same offset until an explicit quarantine decision.",
        ),
        fix=(
            "Validate framing and schema lookup before decode, then route the record plus "
            "offset and error to a dead-letter/quarantine path."
        ),
        prevention=(
            "Alert on deserialization failures and DLQ growth; never silently discard a "
            "record merely because its schema ID is unknown."
        ),
        activate=(
            Command(
                "create the isolated poison topic",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-topics.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--create",
                    "--if-not-exists",
                    "--topic",
                    _POISON_TOPIC,
                    "--partitions",
                    "1",
                    "--replication-factor",
                    "1",
                    "--config",
                    "retention.ms=3600000",
                ),
            ),
            Command(
                "publish exactly one unknown-schema fixture",
                _exec(
                    "kafka",
                    "sh",
                    "-lc",
                    # Confluent framing: magic byte 0 + big-endian schema ID
                    # 999999 (0x000f423f). There is deliberately no payload.
                    "printf '\\000\\000\\017\\102\\077' | "
                    "/opt/kafka/bin/kafka-console-producer.sh --bootstrap-server localhost:9092 "
                    f"--topic {_POISON_TOPIC}",
                ),
            ),
            Command(
                "start the isolated Avro probe and let its bounded restart policy expose the loop",
                _compose("--profile", "scenarios", "up", "-d", "poison-probe"),
            ),
        ),
        reset=(
            Command(
                "remove the isolated crash-loop probe",
                _compose("--profile", "scenarios", "rm", "-s", "-f", "poison-probe"),
            ),
            Command(
                "delete the isolated poison topic",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-topics.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--delete",
                    "--topic",
                    _POISON_TOPIC,
                ),
            ),
        ),
        probes=(
            Command(
                "show the probe restart and deserialization error",
                _compose(
                    "--profile", "scenarios", "logs", "--no-color", "--tail", "80", "poison-probe"
                ),
            ),
            Command(
                "show the fixture topic and its bounded retention",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-configs.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--entity-type",
                    "topics",
                    "--entity-name",
                    _POISON_TOPIC,
                    "--describe",
                ),
            ),
        ),
    ),
    "partition-hotspot": Scenario(
        id="partition-hotspot",
        title="Kafka partition hotspot",
        category="capacity/throughput",
        safety_boundary=(
            "Makes 300 updates to one existing order in one transaction. The key is stable, "
            "so all resulting CDC records land on one partition; the workload ends by itself."
        ),
        timebox_seconds=90,
        symptom=(
            "One Kafka partition advances far faster than the other two and Spark lag is "
            "concentrated on that partition."
        ),
        evidence=(
            "Kafka offsets show one partition receiving nearly all new records.",
            "The sink shows many versions of one order_id.",
            "The aggregate pipeline lag hides the distribution unless inspected by partition.",
        ),
        fix=(
            "Choose a key with sufficient cardinality, or deliberately shard an entity while "
            "preserving per-entity ordering where it matters."
        ),
        prevention=(
            "Alert on partition-skew ratio, not only total consumer/Spark lag; load-test hot keys."
        ),
        activate=(
            Command(
                "write 300 bounded updates for one Kafka key",
                _exec(
                    "postgres",
                    "psql",
                    "-U",
                    "lesson12",
                    "-d",
                    "orders",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "DO $l12$ DECLARE target_id bigint; i integer; BEGIN "
                    "SELECT id INTO target_id FROM orders ORDER BY id LIMIT 1; "
                    "IF target_id IS NULL THEN RAISE EXCEPTION 'need one order'; END IF; "
                    "FOR i IN 1..300 LOOP UPDATE orders SET updated_at=clock_timestamp() "
                    "WHERE id=target_id; END LOOP; END $l12$;",
                ),
            ),
        ),
        reset=(),
        probes=(
            Command(
                "inspect broker end offsets per partition",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-get-offsets.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--topic",
                    "cdc.public.orders",
                ),
            ),
        ),
    ),
    "paused-connector-slot-risk": Scenario(
        id="paused-connector-slot-risk",
        title="Paused Debezium connector and replication-slot risk",
        category="source/CDC",
        safety_boundary=(
            "Pauses only Kafka Connect, creates at most 120 tiny Postgres updates, then "
            "requires unpausing it. It demonstrates retained-WAL risk without attempting "
            "to fill disk."
        ),
        timebox_seconds=120,
        symptom=(
            "Postgres continues accepting writes while Debezium's confirmed LSN stops; the "
            "replication slot's retained WAL distance grows modestly."
        ),
        evidence=(
            "Connect reports a paused process / no connector progress.",
            "pg_replication_slots shows restart_lsn and confirmed_flush_lsn falling "
            "behind pg_current_wal_lsn().",
            "Kafka and Spark stop receiving new source changes even though Postgres rows change.",
        ),
        fix=(
            "Restore the connector, wait for it to catch up, and verify the slot "
            "advances before declaring recovery."
        ),
        prevention=(
            "Alert on replication-slot retained bytes and connector/task state; set a tested "
            "runbook and disk headroom policy."
        ),
        activate=(
            Command("pause Kafka Connect", _compose("pause", "connect")),
            Command(
                "generate a bounded WAL backlog",
                _exec(
                    "postgres",
                    "psql",
                    "-U",
                    "lesson12",
                    "-d",
                    "orders",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "DO $l12$ DECLARE target_id bigint; i integer; BEGIN "
                    "SELECT id INTO target_id FROM orders ORDER BY id LIMIT 1; "
                    "IF target_id IS NULL THEN RAISE EXCEPTION 'need one order'; END IF; "
                    "FOR i IN 1..120 LOOP UPDATE orders SET updated_at=clock_timestamp() "
                    "WHERE id=target_id; END LOOP; END $l12$;",
                ),
            ),
        ),
        reset=(Command("unpause Kafka Connect", _compose("unpause", "connect")),),
        probes=(
            Command(
                "show that only Kafka Connect is paused",
                _compose("ps", "connect"),
            ),
            Command(
                "measure retained WAL without reading files or changing the slot",
                _exec(
                    "postgres",
                    "psql",
                    "-U",
                    "lesson12",
                    "-d",
                    "orders",
                    "-c",
                    "SELECT slot_name, active, restart_lsn, confirmed_flush_lsn, "
                    "pg_size_pretty(pg_wal_lsn_diff(pg_current_wal_lsn(), restart_lsn)) "
                    "AS retained_wal FROM pg_replication_slots "
                    "WHERE slot_name='lesson12_orders_slot';",
                ),
            ),
        ),
    ),
    "silent-data-contract": Scenario(
        id="silent-data-contract",
        title="Silent schema/data-quality fault",
        category="application/data",
        safety_boundary=(
            "Snapshots and changes at most 12 source rows in a dedicated restore table. "
            "Avro remains fully valid and Schema Registry compatibility is unchanged."
        ),
        timebox_seconds=120,
        symptom=(
            "Every component is green and events decode normally, but revenue is inflated by "
            "a valid-looking cents-versus-dollars semantic error."
        ),
        evidence=(
            "Schema Registry versions and compatibility remain valid.",
            "The affected source rows changed amount by exactly 100x.",
            "ClickHouse and the API faithfully reproduce the wrong but well-typed value.",
        ),
        fix=(
            "Correct the source data from the recorded original values, then issue compensating "
            "CDC updates and validate the business invariant."
        ),
        prevention=(
            "Treat units, currencies, and meanings as data contracts; add range/distribution "
            "checks and business-level reconciliation alongside schema compatibility."
        ),
        activate=(
            Command(
                "snapshot then inject a bounded semantic-unit fault",
                _exec(
                    "postgres",
                    "psql",
                    "-U",
                    "lesson12",
                    "-d",
                    "orders",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "BEGIN; CREATE TABLE IF NOT EXISTS l12_scenario_amount_restore "
                    "(order_id bigint PRIMARY KEY, original_amount numeric(10,2) NOT NULL); "
                    "INSERT INTO l12_scenario_amount_restore "
                    "SELECT id, amount FROM orders ORDER BY id LIMIT 12 ON CONFLICT (order_id) "
                    "DO NOTHING; UPDATE orders o SET amount=LEAST(o.amount*100, 99999999.99), "
                    "updated_at=clock_timestamp() FROM l12_scenario_amount_restore r "
                    "WHERE o.id=r.order_id; COMMIT;",
                ),
            ),
        ),
        reset=(
            Command(
                "restore the recorded source values and remove the restore table",
                _exec(
                    "postgres",
                    "psql",
                    "-U",
                    "lesson12",
                    "-d",
                    "orders",
                    "-v",
                    "ON_ERROR_STOP=1",
                    "-c",
                    "BEGIN; UPDATE orders o SET amount=r.original_amount, "
                    "updated_at=clock_timestamp() "
                    "FROM l12_scenario_amount_restore r WHERE o.id=r.order_id; "
                    "DROP TABLE IF EXISTS l12_scenario_amount_restore; COMMIT;",
                ),
            ),
        ),
        probes=(
            Command(
                "find the semantic-unit outliers at the source",
                _exec(
                    "postgres",
                    "psql",
                    "-U",
                    "lesson12",
                    "-d",
                    "orders",
                    "-c",
                    "SELECT id, amount, updated_at FROM orders ORDER BY amount DESC LIMIT 15;",
                ),
            ),
        ),
    ),
    "clickhouse-tiny-parts": Scenario(
        id="clickhouse-tiny-parts",
        title="ClickHouse tiny-parts pressure",
        category="sink/storage",
        safety_boundary=(
            "Creates exactly 40 one-row parts by copying existing current-state rows. "
            "It is far below a production overload and reset performs one explicit merge."
        ),
        timebox_seconds=120,
        symptom=(
            "system.parts shows a burst of active parts and background merges become visible; "
            "current-state reads remain correct because rows retain their versions."
        ),
        evidence=(
            "system.parts active-part count rises for lesson12.orders_current.",
            "system.merges shows background merge work while the scenario is active.",
            "FINAL reads stay semantically correct despite duplicate physical versions.",
        ),
        fix=(
            "Batch inserts at the Spark sink and let normal merges keep up; use a one-off OPTIMIZE "
            "only as controlled recovery, not as the ingestion design."
        ),
        prevention=(
            "Monitor active parts, merge backlog, and insert batch size; cap small-insert rates "
            "before the parts limit becomes an outage."
        ),
        activate=(
            Command(
                "issue 40 intentionally tiny, bounded inserts",
                _exec(
                    "clickhouse",
                    "sh",
                    "-lc",
                    "i=1; while [ $i -le 40 ]; do "
                    "clickhouse-client --user lesson12 --password lesson12 --query "
                    "'INSERT INTO lesson12.orders_current SELECT * FROM lesson12.orders_current "
                    "LIMIT 1'; i=$((i+1)); done",
                ),
            ),
        ),
        reset=(
            Command(
                "compact the small teaching table once",
                _exec(
                    "clickhouse",
                    "clickhouse-client",
                    "--user",
                    "lesson12",
                    "--password",
                    "lesson12",
                    "--query",
                    "OPTIMIZE TABLE lesson12.orders_current FINAL;",
                ),
            ),
        ),
        probes=(
            Command(
                "inspect active parts and their size",
                _exec(
                    "clickhouse",
                    "clickhouse-client",
                    "--user",
                    "lesson12",
                    "--password",
                    "lesson12",
                    "--query",
                    "SELECT count() AS active_parts, sum(rows) AS rows, "
                    "formatReadableSize(sum(bytes_on_disk)) "
                    "AS bytes FROM system.parts WHERE active AND database='lesson12' "
                    "AND table='orders_current';",
                ),
            ),
        ),
    ),
    "kafka-retention-risk": Scenario(
        id="kafka-retention-risk",
        title="Kafka retention/storage risk",
        category="broker/storage",
        safety_boundary=(
            "Creates a separate one-partition topic with dangerous-looking infinite time retention "
            "but a 1 MiB byte limit, then writes only 128 KiB. It never changes cdc.public.orders."
        ),
        timebox_seconds=60,
        symptom=(
            "Topic configuration advertises an unsafe retention policy while disk use stays "
            "deliberately tiny and bounded."
        ),
        evidence=(
            "kafka-configs shows retention.ms=-1 and retention.bytes=1048576 on the fixture topic.",
            "kafka-log-dirs reports only the bounded fixture payload, not a filled broker disk.",
            "The production-like question is capacity math, not waiting for a laptop to fail.",
        ),
        fix=(
            "Set a retention time and byte budget from measured ingress, recovery window, "
            "replication factor, and headroom."
        ),
        prevention=(
            "Alert on broker disk forecast and topic retention drift; test deletion/compaction "
            "policy with small fixture topics before production."
        ),
        activate=(
            Command(
                "create the isolated retention-risk topic",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-topics.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--create",
                    "--if-not-exists",
                    "--topic",
                    _RETENTION_TOPIC,
                    "--partitions",
                    "1",
                    "--replication-factor",
                    "1",
                    "--config",
                    "retention.ms=-1",
                    "--config",
                    "retention.bytes=1048576",
                ),
            ),
            Command(
                "write a bounded 128 KiB sample",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-producer-perf-test.sh",
                    "--topic",
                    _RETENTION_TOPIC,
                    "--num-records",
                    "128",
                    "--record-size",
                    "1024",
                    "--throughput",
                    "100",
                    "--producer-props",
                    "bootstrap.servers=localhost:9092",
                ),
            ),
        ),
        reset=(
            Command(
                "delete the isolated retention-risk topic",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-topics.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--delete",
                    "--topic",
                    _RETENTION_TOPIC,
                ),
            ),
        ),
        probes=(
            Command(
                "inspect the teaching topic's retention policy",
                _exec(
                    "kafka",
                    "/opt/kafka/bin/kafka-configs.sh",
                    "--bootstrap-server",
                    "localhost:9092",
                    "--entity-type",
                    "topics",
                    "--entity-name",
                    _RETENTION_TOPIC,
                    "--describe",
                ),
            ),
        ),
    ),
}
