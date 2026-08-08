# Lesson 12 teacher runbook

This runbook operates the self-contained Lesson 12 `l12-` stack. Its architecture
carries forward the Lesson 11 reference pipeline, but it does not start, edit, or
inject chaos into `src-lesson11/`. A scenario implementation belongs in a
separate, resettable Lesson 12 profile; this document is the teaching contract for
that implementation.

## Before learners arrive

From `src-lesson12/`, start and prove the healthy reference system:

```bash
docker compose up -d --build
uv sync
uv run python scripts/preflight.py
uv run python scripts/verify.py --timeout 180
```

The expected conclusion is a `PASS` for Postgres → Debezium → Avro/Kafka → Spark
→ ClickHouse → API. Do not call a green container list sufficient proof. Keep
Grafana, the browser order tracer, and one terminal ready:

```bash
open dashboard.html
open http://localhost:23000
docker compose logs -f stream-processor
```

Use the Lesson 12 host-port map: Postgres `16432`, Kafka `39092`, Schema Registry
`28081`, Connect `28083`, ClickHouse HTTP `28123`, API `28000`, Spark UI `24040`,
Prometheus `29090`, and Grafana `23000`. All Compose/container names use the
`l12-` prefix.

## Safety rules

- Do not run `docker compose down -v` during class. It removes the source,
  Kafka log, ClickHouse state, checkpoint, Grafana state, and cached artifacts.
- Do not pause or break the one shared healthy Lesson 12 reference stack for every learner.
  Use per-station resettable profiles or prepared evidence fixtures.
- Do not fill real Postgres or Kafka disks. Simulate an approaching limit with a
  capped quota, synthetic metric, fixture logs, or a deliberately small isolated
  volume. Students must still calculate the actual capacity risk.
- Do not ask learners to drop a replication slot, delete Kafka log segments,
  run `OPTIMIZE ... FINAL`, or perform arbitrary shell repair. Those are
  discussion-only emergency actions unless the station's isolated profile gives a
  tightly scoped, reversible command.
- Do not turn the healthy Avro orders stream into “malformed JSON.” The quarantine
  station publishes one Confluent-framed unknown-schema record to the isolated
  `l12.poison-boundary` topic; only the profile-gated probe consumes it.

## Room setup

The scenario controller is dry-run by default and permits only one active
incident in an environment:

```bash
uv run python -m scenarios.cli list
uv run python -m scenarios.cli activate poison-deserialization
uv run python -m scenarios.cli activate poison-deserialization --apply
uv run python -m scenarios.cli status poison-deserialization --live
uv run python -m scenarios.cli reset poison-deserialization --apply
```

Run the preview before every activation/reset. After reset, run `preflight` and
the full canary verifier before handing the environment to another pair.

Prepare six numbered station cards and give each pair exactly one. Each card has a
symptom only, the acceptance test, and one initial safe command. Keep the root
cause and progressive hints on this page, out of student view. If equipment does
not allow six independent environments, rotate prepared logs/metrics/query-output
fixtures while one instructor machine performs the live verification.

Display the evidence ledger columns before the CTF:

| Time | Observation | Source / exact command | Hypothesis changed | Next least-invasive check |
|---|---|---|---|---|

The first question to a stuck group is never “did you check logs?” Ask: “Which
precise observation would eliminate one of your competing hypotheses?”

## Station briefings and keys

### A — Quarantine: one record blocks progress

**Student symptom:** “The isolated Avro probe restarts and repeats the same
offset. Restarting did not help; the healthy orders pipeline still passes.”

**Instructor setup:** Activate `poison-deserialization`. It publishes one
Confluent-framed payload declaring unknown schema ID `999999` to an isolated topic
and starts the profile-gated probe. Preserve the partition and offset; the normal
Lesson 12 orders processor remains untouched.

**Expected evidence:** probe log naming the unknown schema ID; Schema Registry
returns 404 for that ID; the same partition/offset is retried; the healthy orders
verifier still passes.

**Root cause:** one record references a schema the deserializer cannot resolve, so
the probe exits and its bounded restart policy rereads the same offset.

**Safe remediation:** add explicit validation and a quarantine/dead-letter path;
record event identity, raw payload reference, unknown schema ID, reason, and time.
Verify that the bad event is auditable and the healthy canary still passes.

**Hints:**

1. “A restart has not changed the input position. Which position is that?”
2. “Which external identifier must the deserializer resolve before it can decode?”

### B — Hotspot: aggregate health lies

**Student symptom:** “A bounded update burst advanced one Kafka partition much
faster than the other two.”

**Instructor setup:** Activate `partition-hotspot`. It makes exactly 300 updates
to one existing order, so Debezium emits one stable record key. Keep ordering
requirements explicit: do not claim random keys are safe when per-order ordering matters.

**Expected evidence:** broker end offsets by partition before/after the bounded
burst; one order ID with many versions; Debezium's stable record key.

**Root cause:** one business key maps to one partition and dominates its service
capacity. Adding partitions alone does not split that existing hot key.

**Safe remediation:** choose a key strategy that preserves the ordering actually
needed; often sub-partition by a secondary stable shard. Alert on skew ratio, not
only aggregate lag. Verify balanced distribution and acceptable per-key ordering.

**Hints:**

1. “What hides when you average three partitions?”
2. “Which business property does the partition key preserve?”

### C — Retained WAL: analytics threatens the source

**Student symptom:** “The CDC path is behind, the source's retained-WAL risk is
rising, and an operator calls it ‘only analytics.’”

**Instructor setup:** Use a safe fixture/metric showing slot lag and connector
task down/paused; do not generate uncontrolled WAL. Include current LSN,
confirmed flush LSN, and bounded retained-byte estimate.

**Expected evidence:** connector and task status; `pg_replication_slots` row;
current WAL LSN compared with confirmed flush LSN; source-space warning.

**Root cause:** a logical replication slot holds WAL while Debezium cannot advance.

**Safe remediation:** restore connector/task progress and observe the LSN gap
close. Discuss, do not execute, a slot drop: it trades CDC continuity for source
protection and requires a re-snapshot. Prevention: slot-lag and disk alerts,
`max_slot_wal_keep_size`, explicit recovery runbook.

**Hints:**

1. “Which downstream position can force Postgres to retain old history?”
2. “What difference would quantify its risk before the disk is full?”

### D — Green but wrong: the silent contract break

**Student symptom:** “Health checks, processor progress, and lag are normal;
revenue is implausibly inflated for a bounded set of orders.”

**Instructor setup:** Activate `silent-data-contract`. It snapshots at most 12
amounts and multiplies them by 100, modeling a cents-versus-dollars error. The
records and Avro schema remain valid; reset issues compensating source updates.

**Expected evidence:** 100x source amount outliers, the same values faithfully
propagated downstream, normal event flow, and unchanged registry compatibility.

**Root cause:** the pipeline faithfully transports a well-typed value whose unit
is semantically wrong. Registry compatibility checks shape, not business meaning.

**Safe remediation:** restore the snapshotted source values with compensating CDC
updates and prove source/sink/API amounts agree. Add unit, range, distribution,
and business-reconciliation assertions beside schema compatibility.

**Hints:**

1. “What evidence says the data is wrong rather than late?”
2. “Can a value satisfy its type and still use the wrong unit?”

### E — Too many parts: throughput becomes query pain

**Student symptom:** “Inserts continue but API/query latency rises. CPU/merge work
is high.”

**Instructor setup:** Use a short, isolated tiny-insert profile or fixture with
bounded active-parts and merge metrics. Never damage the shared current-state
table with thousands of classroom parts.

**Expected evidence:** `system.parts` active count for the target table;
`system.merges`; recent insert size/frequency; query latency.

**Root cause:** tiny, frequent writes create MergeTree parts faster than background
merges can consolidate them.

**Safe remediation:** stop the micro-insert behavior and batch by rows/time.
`OPTIMIZE ... FINAL` is a risky, expensive operation, not an automatic agent
action. Prevent with minimum batch policy and early parts-count alerting.

**Hints:**

1. “What does MergeTree physically create per insert?”
2. “Is a one-off manual merge a cure or an emergency symptom treatment?”

### F — Retention risk before disk exhaustion

**Student symptom:** “An isolated topic retains forever by time. The fixture is
byte-capped, so you must diagnose the production risk before a disk fills.”

**Instructor setup:** Activate `kafka-retention-risk`. It creates a separate topic
with `retention.ms=-1`, a 1 MiB byte cap, and only 128 KiB of sample data. Include
a worksheet with event rate, record size, intended recovery window, replication,
and headroom.

**Expected evidence:** explicit topic retention configuration, the fixture's byte
cap and sample size, and a capacity calculation showing the unbounded production risk.

**Root cause:** a forever-by-time policy has no capacity relationship to ingress or
provisioned storage. The classroom byte cap prevents the outage while preserving the mistake.

**Safe remediation:** propose calculated time and byte budgets for the isolated
topic, preserving the required replay window and headroom. Prevent with storage
alerts and recovery-time-aware retention or tiered storage design.

**Hints:**

1. “Which configuration value says when retained history may be deleted?”
2. “Calculate the budget before you change the retention number.”

## Live agent demo

Use an intentionally small graph. It is a teaching artifact, not an autonomous
on-call system.

```bash
# Deterministic projector fallback: full trace, no network or model key.
uv run python -m agent.demo --scenario poison-deserialization

# Real LangGraph + durable SQLite: pauses at interrupt().
uv run python -m agent.demo --scenario poison-deserialization \
  --runtime langgraph --checkpoint .state/class.sqlite --thread-id demo

# Persist the named human decision. This still executes no remediation.
uv run python -m agent.demo --scenario poison-deserialization \
  --runtime langgraph --checkpoint .state/class.sqlite --thread-id demo \
  --decision approve --approved-by instructor --note 'bounded reset approved'
```

```text
intake → baseline → select_readonly_tool → record_evidence ─┐
                      ▲                                     │
                      └──────── insufficient evidence ──────┘
                                        ↓
                                  propose_action
                                        ↓
                              interrupt_for_approval
                                        ↓
                          authorized external action
                                        ↓
                                      verify
```

Give the model only read-only, typed inspectors such as
`get_pipeline_health`, `get_partition_lag`, `get_connector_status`,
`get_slot_status`, `get_parts_stats`, `get_schema_versions`, and
`query_business_metric`. Keep `restart_connector`, `apply_retention_profile`, and
`replay_scoped_window` on a separately approved allow-list. Do not expose
`run_shell`, `drop_replication_slot`, arbitrary SQL write, or arbitrary Kafka
administration.

Demo sequence:

1. Show a symptom and the empty incident state.
2. Let the agent select a read-only tool. Pause and ask learners for their next
   tool choice before running it.
3. Require every conclusion to add an evidence object with source and observation.
4. Let it propose a state-changing action; stop at the approval interrupt.
5. Approve only a reversible, scoped action.
6. Apply the scenario controller's scoped reset outside the agent, run the
   deterministic verifier, and show the trace/evaluation row. Approval changes
   authority; it does not claim that remediation or recovery already happened.
7. Change one vague tool description to a precise one and compare trajectories.

The teacher line to repeat: “The model may suggest the next observation. It may
not manufacture evidence or authorize itself.”

## Timing recovery

If the human CTF runs long, stop active investigation at 1:15 and take only one
finding per station. Preserve the 40-minute agent block; that is the capstone's
new synthesis, not an optional trailer. If the demo model is unavailable, use the
pre-recorded/mock trace from the student vertical-slice schema and let the room
grade it. The lesson still works because the learning target is the evidence and
approval design, not a live model response.

## End-of-class checks

- Every station has named a misleading signal and a decisive observation.
- Every proposed remediation has an expected recovery signal.
- Every student group can say why a generic shell tool is unsafe.
- Every agent vertical slice has a durable incident state, evidence array,
  approval boundary, and at least one evaluation case.
- Restore/reset only the isolated station profiles. Keep the Lesson 12 reference
  pipeline clean and leave its verifier passing for the next class/rehearsal.
