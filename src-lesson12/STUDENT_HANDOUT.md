# Lesson 12 incident stations — student handout

Your pair receives one station. You are given a symptom, not a root cause. AI
assistance is allowed, but every material conclusion must cite an exact command,
query, metric, log line, or trace.

## Finish condition

Your incident is complete only when you have:

1. recorded at least two plausible hypotheses;
2. identified the smallest read-only observation that distinguishes them;
3. supported a root cause with an evidence ledger;
4. proposed a scoped fix with risk, rollback, and expected recovery signal;
5. named the action requiring human approval;
6. reset the bounded scenario with the instructor; and
7. passed both `preflight` and the end-to-end canary verifier.

Do not run arbitrary repair commands, delete topics or slots, change retention,
execute unrestricted SQL writes, or reset Docker volumes. Ask the instructor to
approve the scenario controller's known reset.

## Evidence ledger

| Time | Observation | Exact source | Hypothesis supported or rejected | Next check |
|---|---|---|---|---|
| | | | | |
| | | | | |
| | | | | |

## Station A — the record that will not decode

**Symptom:** The isolated Avro probe restarts repeatedly and encounters the same
record. The normal orders canary still succeeds.

**Initial safe command:**

```bash
uv run python -m scenarios.cli status poison-deserialization --live
```

**Acceptance test:** Explain why a restart repeats the failure, preserve the
record's identity, and propose a quarantine behavior that does not silently skip
an arbitrary range.

## Station B — one partition runs away

**Symptom:** One Kafka partition advanced much faster than the other two during a
bounded source burst. Aggregate throughput alone does not explain the distribution.

**Initial safe command:**

```bash
uv run python -m scenarios.cli status partition-hotspot --live
```

**Acceptance test:** Identify the skew, explain which ordering property the
current key preserves, and propose a strategy that states its ordering tradeoff.

## Station C — “only analytics” threatens the source

**Symptom:** Postgres accepts changes, but CDC does not advance. The source now
retains history for a downstream reader.

**Initial safe command:**

```bash
uv run python -m scenarios.cli status paused-connector-slot-risk --live
```

**Acceptance test:** Quantify the retained-history risk and state the recovery
signal. Do not drop the replication slot.

## Station D — green, current, and wrong

**Symptom:** Services are healthy, records decode, lag is normal, and revenue is
implausibly high for a bounded set of orders.

**Initial safe command:**

```bash
uv run python -m scenarios.cli status silent-data-contract --live
```

**Acceptance test:** Show why schema compatibility did not protect the business
meaning and define a value-level assertion that would catch the problem.

## Station E — parts multiply

**Symptom:** A bounded write profile created many more active ClickHouse parts than
its row count appears to justify. This is an early-warning exercise, not a request
to overwhelm the database.

**Initial safe command:**

```bash
uv run python -m scenarios.cli status clickhouse-tiny-parts --live
```

**Acceptance test:** Connect the insert pattern to physical parts and merge work;
propose a batching policy and an early alert.

## Station F — the disk incident before the disk fills

**Symptom:** An isolated Kafka topic has a configuration that would retain data
forever by time. The fixture is intentionally byte-capped, so diagnosis requires
capacity reasoning rather than waiting for a real outage.

**Initial safe command:**

```bash
uv run python -m scenarios.cli status kafka-retention-risk --live
```

**Acceptance test:** Calculate storage from measured ingress, retention, and
replication assumptions; propose explicit time and byte budgets plus alert levels.

## Agent vertical slice

After the collective debrief, implement or annotate one path:

```text
incident intake -> baseline -> choose read-only tool -> record evidence
                -> propose remediation -> approval interrupt -> verification plan
```

Submit:

- one typed tool contract;
- structured incident/evidence state;
- one trace, real or mocked;
- allowed and denied capabilities;
- approval payload;
- one evaluation case with explicit pass conditions.

Retrieved guidance may suggest what to inspect. Only observations from the running
system count as live evidence.

