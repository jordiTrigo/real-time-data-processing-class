# Agent takeover guide — Lesson 12

Read this file completely before changing `src-lesson12`. Then read `README.md`,
`LESSON_PLAN.md`, and `TEACHER_RUNBOOK.md` before changing behavior or pedagogy.

## Mission

Lesson 12 is a self-contained incident-response capstone. It contains its own copy
of the healthy Lesson 11 pipeline and adds six bounded failure scenarios, an
evidence-first incident agent, approval-gated remediation, and deterministic
evaluations. Nothing in this directory should require `src-lesson11` at runtime.

The lesson teaches one thesis:

> An AI agent is also a stateful data system. Its messages and tool calls are
> events, its context is state, its checkpoints enable recovery, and unsupported
> conclusions are data-quality failures.

## Healthy reference pipeline

```text
Postgres -> Debezium -> Kafka + Schema Registry -> Spark -> ClickHouse -> FastAPI
                                                               |
                                           Prometheus <---------+
                                               |
                                            Grafana
```

Lesson 12 host ports intentionally differ from Lesson 11:

| Component | Host port |
|---|---:|
| Postgres | 16432 |
| Kafka | 39092 |
| Schema Registry | 28081 |
| Kafka Connect | 28083 |
| ClickHouse HTTP / native / metrics | 28123 / 29000 / 29363 |
| API | 28000 |
| Spark UI / metrics | 24040 / 29108 |
| Prometheus | 29090 |
| Grafana | 23000 |

Compose resources and containers use the `lesson12` / `l12-` namespace.

## Non-negotiable invariants

1. `src-lesson12` is self-contained. Do not import files from another lesson or
   require another lesson's Compose project to be running.
2. The default path is healthy. Failure injection happens only through the
   scenario controller and must be explicit, bounded, observable, and reversible.
3. Never fill a student's disk to teach disk exhaustion. Demonstrate risk with a
   small quota, bounded fixture, or capacity calculation and an early tripwire.
4. Never grow WAL without a configured upper bound and an automatic reset path.
5. Never give the incident agent arbitrary shell or unrestricted SQL. Diagnostic
   tools are allow-listed and read-only. Mutations require a separate remediation
   action plus human approval.
6. Every diagnosis must retain an evidence ledger: source, observation, timestamp,
   and the hypothesis it supports or contradicts.
7. Scenario tests and agent tests run offline with fakes. They must not require
   Docker, an API key, or network access.
8. A green dashboard is not proof of recovery. Recovery means the scenario's
   explicit steady-state assertions pass and the end-to-end verifier passes.
9. Keep the stack within the existing laptop-sized resource model. Do not add a
   second broker, Spark cluster, vector database, or hosted dependency to the
   default classroom path.
10. Preserve Lesson 11's correctness invariants: per-record Avro schema IDs,
    whole-row Debezium images, source LSN versioning, persistent Spark checkpoints,
    bounded offsets per trigger, and `ReplacingMergeTree` current-state semantics.

## Scenario contract

Each scenario must define:

- a student-visible symptom;
- one bounded activation path;
- status probes and expected evidence;
- an immediate fix and structural prevention strategy;
- an idempotent reset;
- a deterministic evaluation case;
- a maximum blast radius and safety rationale.

Only one scenario is active in a student environment at a time. Activating a new
one must fail unless the current scenario has been reset or an explicit instructor
override is used.

## Agent contract

The teaching workflow is:

```text
observe -> hypothesize -> choose probe -> collect evidence -> revise
        -> propose action -> human approval -> remediate -> verify -> post-mortem
```

Agentic judgment belongs in hypothesis formation and probe selection. Health
collection, authorization, remediation execution, and recovery verification remain
deterministic. Multi-agent delegation is an optional comparison, not the default.

No API credential is required for the scripted investigator or evaluation suite.
Real-model adapters must be opt-in through environment variables, have no
hard-coded secret, and preserve the same typed state and tool boundary.

## Validation

Use the smallest relevant checks while iterating, then finish with:

```bash
docker compose config --quiet
uv run ruff check app agent evals mcp_server processor scenarios scripts tests
uv run python -m compileall -q app agent evals mcp_server processor scenarios scripts
uv run pytest -q
uv run python scripts/preflight.py
uv run python scripts/verify.py --timeout 180
```

Run a live scenario rehearsal only after the healthy contract passes. Do not run
`docker compose down -v` without explicit user approval; it destroys this lesson's
Postgres, Kafka, ClickHouse, checkpoint, Prometheus, and Grafana volumes.

## Worktree safety

The parent repository may contain unrelated untracked work. Do not delete, reset,
stage, or reformat files outside the Lesson 12 task. Never modify `src-lesson11` to
make Lesson 12 pass.

