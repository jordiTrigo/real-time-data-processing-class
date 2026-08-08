# Lesson 12, Break everything—and build the agent who gets paged

Lesson 12 is the operational and agentic capstone. It contains its own complete
copy of the course pipeline:

```text
Postgres -> Debezium -> Kafka + Schema Registry -> Spark -> ClickHouse -> FastAPI
                                                               |
                                           Prometheus <---------+
                                               |
                                            Grafana
```

Students first investigate failures as human operators. They then build and
evaluate one evidence-first incident-agent path over the same system. The point is
not autonomous repair. The point is to make diagnosis, uncertainty, authority,
and recovery observable.

The executable source is in [`src-lesson12/`](../../src-lesson12/), the detailed
run of show is [`LESSON_PLAN.md`](../../src-lesson12/LESSON_PLAN.md), and the deck
is [`slides/lesson-12.html`](../../slides/lesson-12.html).

## Learning outcomes

By the end, students can:

1. Move from an ambiguous symptom to a supported root cause using the least
   invasive next observation.
2. Distinguish dependency health, progress, freshness, correctness, and capacity.
3. Classify an automation step as deterministic workflow, bounded model judgment,
   or a state-changing action requiring human approval.
4. Design typed, least-privilege diagnostic tools instead of exposing arbitrary
   shell or SQL.
5. Represent an incident as durable state: symptom, hypotheses, evidence,
   proposal, approval, and recovery verification.
6. Evaluate an agent's diagnosis, evidence trail, tool trajectory, safety, and
   recovery plan instead of grading fluent prose.

## Three-hour structure

| Time | Activity |
|---|---|
| 0:00–0:15 | Cold open: prove steady state, then reveal one ambiguous symptom |
| 0:15–0:35 | Failure taxonomy, chaos discipline, degradation, capacity math |
| 0:35–1:15 | Human CTF: six bounded incident stations distributed across pairs |
| 1:15–1:30 | Collective debrief: misleading signal, decisive evidence, safe fix |
| 1:30–1:40 | Break and reset of the isolated instructor profile |
| 1:40–2:05 | Agentic kaleidoscope: tools, MCP, durable state, RAG, HITL, traces, evals |
| 2:05–2:35 | Student vertical slice: one safe evidence-first graph path |
| 2:35–2:50 | Human versus agent on a seventh unseen incident |
| 2:50–3:00 | Evaluation review and course close |

## Six human incident stations

The scenarios are independently activatable and resettable. Only one may be
active in an environment at once, and the CLI defaults to dry-run.

| Station | Failure | Decisive evidence |
|---|---|---|
| A | Unknown Avro schema ID in an isolated poison-probe topic | repeated offset, probe error, registry miss |
| B | Kafka partition hotspot | broker end offsets by partition and stable hot key |
| C | Paused Debezium connector retaining WAL | connector state and replication-slot LSN gap |
| D | Validly typed but semantically wrong amounts | source outliers and downstream business totals |
| E | ClickHouse tiny-parts pressure | `system.parts`, merges, and insert pattern |
| F | Kafka retention/storage risk | capped topic configuration, bytes written, capacity calculation |

Disk and WAL incidents are bounded demonstrations. They must never fill a
student's real disk. The healthy orders topic and checkpoint remain intact for the
isolated poison scenario.

For each station, students record:

- symptom and impact;
- at least two plausible hypotheses;
- exact commands, queries, metrics, or log lines in an evidence ledger;
- root cause and causal chain;
- scoped remediation, risk, rollback, and approver;
- deterministic recovery signal; and
- prevention or earlier detection.

## Agentic kaleidoscope

The implementation uses a real LangGraph state machine because the graph makes
durable state, loops, checkpoints, and interrupts visible. A deterministic
investigator keeps the classroom and tests offline; a real-model adapter is
optional and environment-configured.

```text
observe -> hypothesize -> choose read-only tool -> collect evidence -> revise
        -> propose action -> INTERRUPT FOR HUMAN APPROVAL -> verify -> report
```

The concepts are introduced through this one vertical slice:

- **Agents versus workflows:** health collection and recovery assertions remain
  deterministic; model judgment is limited to ambiguous probe selection.
- **Typed tools:** diagnostics expose fixed observations, never arbitrary shell.
- **MCP:** tools expose live inspections; resources expose topology and runbooks.
- **Durable state:** SQLite checkpoints survive process restarts and retain the
  evidence/hypothesis ledger.
- **RAG:** lexical retrieval supplies local guidance but is labeled separately
  from live evidence.
- **Structured output:** every diagnosis cites evidence IDs and an expected
  recovery signal.
- **Human-in-the-loop:** remediation proposals pause for a named approve/reject
  decision; the graph has no autonomous repair tool.
- **Observability:** the class compares the pipeline's event trace with the
  agent's model/tool/evidence trace.
- **Evaluation:** the six incidents form an offline regression dataset.
- **Multi-agent skepticism:** specialists are added only if evaluation shows a
  benefit that justifies extra handoffs and failure modes.

## Deliverable

Each pair submits one completed
[`POSTMORTEM_TEMPLATE.md`](../../src-lesson12/POSTMORTEM_TEMPLATE.md) and one agent
vertical slice containing:

- a typed diagnostic tool contract;
- structured incident state;
- graph or executable path;
- evidence/tool trace;
- approval boundary and denied capabilities;
- deterministic recovery plan; and
- one evaluation case derived from the incident.

AI assistance is encouraged, but retrieved guidance and model claims do not count
as incident evidence. The final assessment occurs after Lesson 12 and uses unseen
cases rather than copying these six stations.
