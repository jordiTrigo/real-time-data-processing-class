# Lesson 12 — break everything, build the agent who gets paged

Lesson 12 is a self-contained operational and agentic capstone. It begins with a
healthy end-to-end streaming system, injects one bounded incident at a time, and
uses the same evidence contract for human and agent investigations.

```text
Postgres -> Debezium -> Kafka + Schema Registry -> Spark -> ClickHouse -> FastAPI
                                                               |
                                           Prometheus <---------+
                                               |
                                            Grafana

symptom -> hypothesis -> read-only tool -> evidence -> proposal
                                                    -> HUMAN APPROVAL -> verify
```

Nothing here needs `src-lesson11` at runtime. Lesson 12 has its own images,
configuration, databases, volumes, ports, scenario fixtures, agent, and tests.

## Requirements

- Docker with at least 8 GB available
- `uv`
- Python 3.11 or newer
- No model/API key for the default classroom path

The first cold start downloads the Kafka, Confluent, Spark, ClickHouse, Prometheus,
and Grafana images. Start it before class.

## Start and prove the healthy system

From `src-lesson12/`:

```bash
uv sync
docker compose up -d --build
docker compose ps -a
uv run python scripts/preflight.py
uv run python scripts/verify.py --timeout 180
```

The verifier—not a green container list—is the health contract. It must conclude:

```text
PASS: Postgres -> Debezium -> Avro/Kafka -> Spark -> ClickHouse -> API
```

Open the operational surfaces:

```bash
open dashboard.html
open http://localhost:23000
open http://localhost:29090
```

| Component | Host address |
|---|---|
| Postgres | `localhost:16432` |
| Kafka | `localhost:39092` |
| Schema Registry | `http://localhost:28081` |
| Kafka Connect | `http://localhost:28083` |
| ClickHouse HTTP / native | `localhost:28123` / `localhost:29000` |
| API | `http://localhost:28000` |
| Spark UI / metrics | `http://localhost:24040` / `http://localhost:29108` |
| Prometheus | `http://localhost:29090` |
| Grafana | `http://localhost:23000` (`admin` / `lesson12`) |

## Scenario controller

The controller is dry-run by default. It permits one active scenario and records
local controller state in `.scenario-state.json`.

```bash
uv run python -m scenarios.cli list
uv run python -m scenarios.cli manifest poison-deserialization
uv run python -m scenarios.cli activate poison-deserialization
uv run python -m scenarios.cli activate poison-deserialization --apply
uv run python -m scenarios.cli status poison-deserialization --live
uv run python -m scenarios.cli reset poison-deserialization --apply
```

The six bounded incidents are:

| ID | Demonstration | Safety boundary |
|---|---|---|
| `poison-deserialization` | unknown Avro schema ID crash-loops an isolated probe | one record, separate topic and profile; orders stream untouched |
| `partition-hotspot` | stable hot key skews Kafka partitions | exactly 300 source updates |
| `paused-connector-slot-risk` | paused CDC retains WAL | exactly 120 updates; no disk-fill attempt |
| `silent-data-contract` | valid cents/dollars semantic corruption | 12 snapshotted rows with compensating reset |
| `clickhouse-tiny-parts` | tiny inserts create MergeTree parts | exactly 40 one-row inserts |
| `kafka-retention-risk` | retention math can exceed storage | isolated 1 MiB-capped topic with 128 KiB sample |

After every reset, prove recovery:

```bash
uv run python scripts/preflight.py
uv run python scripts/verify.py --timeout 180
```

Never use `docker compose down -v` as a reset. That deletes the complete Lesson 12
state, including Postgres, Kafka, ClickHouse, Spark checkpoints, and dashboards.

## Run the safe incident agent

The default demo is offline and deterministic. It uses the same typed incident
state and evidence ledger as the real graph, stops at the approval boundary, and
never executes remediation:

```bash
uv run python -m agent.demo --scenario poison-deserialization
uv run python -m agent.demo --scenario silent-data-contract
```

Run all six evaluation cases:

```bash
uv run python -m evals.runner
```

Each case scores four independent claims:

- correct root cause;
- required retrieved guidance **and** live evidence;
- proposal stopped at human approval; and
- explicit recovery signal.

The agent has no arbitrary shell, arbitrary SQL, or remediation tool. Its live
catalog consists only of fixed read-only observations such as connector status,
slot lag, broker offsets, registry lookup, parts count, business outliers, and
preflight.

## Real LangGraph and durable checkpoints

`agent/langgraph_runtime.py` builds a real `StateGraph`. Use a stable thread ID and
the SQLite saver for a demonstration that survives a process restart. The graph
uses `interrupt()` to pause on a structured remediation proposal and resumes only
with a named human's approve/reject payload. Approval still does not grant the
graph a remediation command.

The in-memory saver exists only for short demonstrations and tests. Durable demos
should store their SQLite file under `.state/`, which Git ignores.

```bash
# Run until the durable approval interrupt.
uv run python -m agent.demo --scenario poison-deserialization \
  --runtime langgraph --checkpoint .state/class.sqlite --thread-id pair-a

# Resume the same checkpoint with a named human decision. This records approval;
# it still does not execute the proposed remediation.
uv run python -m agent.demo --scenario poison-deserialization \
  --runtime langgraph --checkpoint .state/class.sqlite --thread-id pair-a \
  --decision approve --approved-by instructor --note 'bounded fixture only'
```

## MCP server

Expose the same read-only catalog to any local MCP client over stdio:

```bash
uv run python -m mcp_server.server
```

MCP makes the capability boundary reusable; it does not replace least privilege
or approval. All advertised tools take no arbitrary command or query arguments.

## Optional real-model investigator

The offline path is the reliable classroom fallback. A live model is opt-in and
uses only environment configuration:

```bash
export INCIDENT_AGENT_BASE_URL='https://your-provider.example/v1'
export INCIDENT_AGENT_API_KEY='...'
export INCIDENT_AGENT_MODEL='your-model-id'
uv run python -m agent.demo --scenario paused-connector-slot-risk --investigator live
```

Do not put credentials or a supposedly “current” model name in repository files.
The live adapter can select only the read-only tool names it receives or return a
structured proposal.

## Teaching material

- [`LESSON_PLAN.md`](LESSON_PLAN.md) — complete three-hour sequence
- [`TEACHER_RUNBOOK.md`](TEACHER_RUNBOOK.md) — setup, station keys, hints, demo beats
- [`LESSON12_CHEATSHEET.md`](LESSON12_CHEATSHEET.md) — projector/desk reference
- [`POSTMORTEM_TEMPLATE.md`](POSTMORTEM_TEMPLATE.md) — evidence-first deliverable
- [`STUDENT_HANDOUT.md`](STUDENT_HANDOUT.md) — symptom-only station cards and rubric
- [`REFERENCES.md`](REFERENCES.md) — current framework/protocol references
- [`../slides/lesson-12.html`](../slides/lesson-12.html) — 23-slide deck with speaker notes

## Static validation

These checks require no Docker daemon or API key:

```bash
docker compose --profile scenarios config --quiet
uv run ruff check app agent evals mcp_server processor scenarios scripts tests
uv run python -m compileall -q app agent evals mcp_server processor scenarios scripts
uv run pytest -q
python -m json.tool scenarios/manifest.json
python -m json.tool grafana/dashboards/lesson12-pipeline.json
```

The architecture and safety invariants for future changes are in
[`AGENTS.md`](AGENTS.md).
