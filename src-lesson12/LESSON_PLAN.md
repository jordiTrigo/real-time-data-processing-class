# Lesson 12 teaching plan — break everything, build the agent who gets paged

Lesson 12 is a self-contained capstone stack that carries forward the healthy
reference architecture from Lesson 11:

```text
Postgres → Debezium → Kafka + Schema Registry → Spark → ClickHouse → FastAPI
                                                               │
                                           Prometheus ←─────────┘
                                               │
                                            Grafana
```

Students do two related jobs. First, they investigate a production-style incident
as people with logs, metrics, queries, and judgment. Then they make the beginning
of a safe incident-investigation agent which can collect the same evidence, keep
an auditable incident state, and ask a human before it changes anything.

The Lesson 12 implementation has its own `l12-` Compose/container prefix and does
not require students to start or modify `src-lesson11/`. Framework vocabulary earns its place
only when it clarifies a system students have already operated: durable state,
typed tool boundaries, replay, evidence, permissions, and evaluation.

## Outcomes

By the end, students can:

1. Work from an ambiguous symptom to a root cause without confusing a green
   dependency check with correct or fresh data.
2. Use the Lesson 11 pipeline's observable boundaries to collect evidence for a
   diagnosis and verify recovery with the canary verifier.
3. Classify an automated step as deterministic workflow, model judgment, or a
   dangerous action requiring human approval.
4. Define typed, least-privilege diagnostic tools instead of giving a model an
   unrestricted shell.
5. Model an incident as durable state: symptom, evidence, hypotheses, proposed
   action, approval, and verification.
6. Evaluate an agent on evidence, safety, recovery, latency, and cost—not on a
   plausible final paragraph.

## The central visual

```text
alert / symptom
      │
      ▼
observe → hypothesize → inspect → evidence → propose action → HUMAN APPROVAL
                 ▲                         │                        │
                 └──────── not enough ────┘                        ▼
                                                              fix → verify
                                                                    │
                                                                    ▼
                                                             post-mortem
```

The right-hand half is deliberately constrained. Read-only observation can be
automatic. A restart, configuration change, SQL write, slot drop, topic retention
change, or data backfill must be proposed with expected recovery evidence and then
approved by a human. The agent never receives arbitrary shell access in class.

## Three-hour run of show

### 0:00–0:15 — Cold open and incident contract

Start from the healthy Lesson 12 stack. Run `preflight` and one canary verifier
step; show the API response and the Grafana dashboard. Then show a broken surface:
lag rises, a business value looks wrong, or a write path has stopped. Ask only:

> What is the next observation that would reduce uncertainty?

Frame the discipline before the activity:

- A dashboard is evidence, not a verdict.
- Diagnose from the symptom; do not start by editing.
- A fix is incomplete until a steady-state signal returns and the canary passes.
- AI is welcome, but every conclusion needs the command, query, log line, or
  metric that supports it.

### 0:15–0:35 — Failure thinking, fast

Keep theory tight and anchored in the pipeline.

| Idea | Question to ask | Pipeline example |
|---|---|---|
| Failure taxonomy | Which boundary could create this symptom? | Kafka disk pressure becomes stale API data. |
| Steady state | What measurable claim did we expect? | lag below threshold, current canary visible, known freshness. |
| Chaos loop | hypothesis → inject → observe → harden | pause CDC only in a bounded classroom profile. |
| Failure choice | recover, degrade, or stop safely? | quarantine an undecodable record instead of serving corrupted data. |
| Capacity napkin math | Where does retained work accumulate? | WAL, Kafka segments, ClickHouse parts, Spark backlog. |

The key line: **the most dangerous incident is plausible, green, and wrong.**

### 0:35–1:15 — Human CTF, six distributed pair stations

Do not give every pair all six incidents. Make six stations, one scenario each;
assign pairs evenly and rotate only if a station finishes early. This fits the
hour, keeps local machine risk bounded, and makes the collective debrief useful.

| Station | Symptom handed to students | Failure boundary | Required evidence |
|---|---|---|---|
| A — quarantine | isolated Avro probe repeats one offset | schema resolution | probe error plus unknown schema-ID lookup |
| B — hotspot | one partition advances much faster | Kafka key distribution | broker offsets by partition and stable hot key |
| C — retained WAL | analytics is behind; source storage risk rises | Postgres / Debezium | slot LSN gap and connector/task status |
| D — green but wrong | revenue inflates while health and lag are normal | semantic data contract | source outliers and unchanged schema compatibility |
| E — too many parts | active parts jump after tiny writes | ClickHouse | active parts and insert pattern |
| F — retention risk | forever-by-time policy on a capped fixture | Kafka capacity | topic config, byte cap, and capacity calculation |

Station profiles must be individually activatable and resettable in the local
Lesson 12 stack. They are not six
simultaneous destructive faults. In particular, WAL and Kafka disk incidents use
a visible bounded simulation/threshold or fixture; never fill a learner's actual
disk. The poison-pill station uses one Confluent-framed record with an unknown
schema ID on an isolated topic. Its profile-gated Avro probe crash-loops without
touching the healthy orders topic or Spark checkpoint.

Each pair records the first three sections of the post-mortem template while they
work: symptom/impact, timeline, and evidence ledger. Give one progressive hint
after ten stuck minutes, then a second only if the pair cannot name a next
observation after another five.

### 1:15–1:30 — Collective incident review

One spokesperson per station gets two minutes:

1. symptom and misleading signal;
2. decisive evidence;
3. root cause and safe remediation;
4. verification signal; and
5. prevention.

The instructor connects each station to an invariant from Lesson 11. Do not turn
this into a list of solutions. Keep asking, “What evidence ruled out the tempting
alternative?”

### 1:30–1:40 — Break

Leave the healthy architecture slide up. Reset the instructor demo profile; do not
ask students to reset volumes or operate destructive recovery commands.

### 1:40–2:05 — Agentic incident-response kaleidoscope

Introduce a single vertical slice—not a “framework zoo.” LangGraph is the visible
state-machine implementation because durable, inspectable graph state mirrors the
course's checkpoints and replay lessons. A small model adapter keeps the graph
independent of model provider.

| Topic | The point to teach | Concrete class move |
|---|---|---|
| Agent or workflow? | deterministic paths are cheaper and more reliable | make baseline/verify fixed nodes; use model judgment only to choose the next read-only tool |
| Typed tools | tool contracts are part of the application | compare `run_shell(command)` with `get_partition_lag()` |
| MCP | reusable boundary for tools, resources, prompts | map inspector actions to tools; topology/runbooks to resources |
| Durable state | incidents outlive one completion | show checkpointed state and resume after an approval pause |
| RAG | documents provide context, not proof | distinguish a runbook suggestion from live system evidence |
| Structured evidence | claims need source and observation | require a JSON incident object with evidence array |
| HITL / least privilege | authorization is separate from correctness | interrupt at a restart/config/write proposal |
| Traces | agent systems are observable systems | follow model → tool → evidence → action as a causal graph |
| Evals | known failures are test cases | score tool trajectory, evidence, safety, recovery, time, tokens |
| Multi-agent skepticism | decomposition has a cost | ask whether one agent plus four tools beats four agents with handoffs |

Teacher demo beat: change one weak tool description to a precise one and re-run the
same incident. The visible difference makes “tool design is prompt engineering”
concrete without requiring a long framework lecture.

### 2:05–2:35 — Student vertical slice

Pairs implement/design one thin, safe graph path:

```text
incident intake → baseline health → choose read-only inspection → evidence record
    → propose remediation → interrupt for approval → verification plan
```

Minimum submission is a typed tool contract, structured incident schema, graph
diagram/pseudocode, one trace (real or mocked), and a test case from the station.
They do not need a production agent or autonomous repairer. The quality bar is
that an observer can identify what the agent knew, what it inferred, and which
human approved a state-changing action.

### 2:35–2:50 — Human versus agent: seventh, unseen incident

Run a new bounded scenario not used as a student station, such as the API is
healthy but `source_ts` is old because the connector task stopped. Students and
the demo agent both receive only the symptom. Pause after each agent tool call and
ask the room whether they would make that call next.

Score both trails with the same rubric. The point is not that the agent wins; it
is to make unsupported confidence, wasted calls, and unsafe remediation visible.

### 2:50–3:00 — Eval close

Show the final incident object, trace, approval boundary, and evaluation row.
Close on the connection to the course:

> An agent is a distributed system whose events are messages and tool calls,
> whose state is context, whose checkpoints are memory, and whose data-quality
> failures are unsupported claims.

## Deliverables

Each pair submits one post-mortem for its human station and one agent vertical
slice. Individual reflection: “Where was model judgment useful, and where was a
deterministic workflow safer?”

The post-mortem must name evidence precisely and include a safe recovery test. The
agent slice must list its allowed tools, denied tools, approval boundary, and
evaluation case. A stylish chatbot response without evidence receives no credit.

## Instructor positioning

The instructor's value is made visible in judgment calls:

- diagnose ambiguous telemetry live;
- distinguish an attractive explanation from one supported by evidence;
- stop a dangerous but technically plausible remediation;
- turn a failed trace into an evaluation; and
- connect today's agent checkpoint to yesterday's streaming checkpoint.

That is the throughline: systems thinking survives changes in framework names.
