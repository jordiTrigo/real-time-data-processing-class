# Incident post-mortem

Copy this template once per incident. Write for an engineer who did not attend
class and needs to reproduce the reasoning—not merely read a confident outcome.

## 1. Incident summary

| Field | Record |
|---|---|
| Title | |
| Scenario / station | |
| Severity (P1–P4) and justification | |
| Start / detected / mitigated (with timezone) | |
| User or business impact | |
| Current status | |
| Author(s) | |

In two sentences: what did an operator or user experience, and what did the
system actually do?

## 2. Steady state and blast radius

What did “healthy” mean before the incident? State measurable expectations:

- expected API/current-state behavior:
- expected lag, throughput, freshness, or query latency:
- affected boundary or component:
- what remained healthy (do not infer this from one green panel):
- what data could be wrong, delayed, duplicated, or unavailable:

## 3. Timeline

| Time | Observation or action | Who / system | Evidence link or exact command |
|---|---|---|---|
| | symptom observed | | |
| | first hypothesis | | |
| | hypothesis rejected / supported | | |
| | mitigation proposed | | |
| | recovery verified | | |

## 4. Evidence ledger

Every material claim needs a source. “Checked logs” is not evidence.

| # | Observation | Source: command, query, metric, trace, or log line | What it supports or rules out |
|---|---|---|---|
| 1 | | | |
| 2 | | | |
| 3 | | | |

Include relevant identifiers: order/canary id, Kafka topic/partition/offset,
source LSN, schema ID/version, ClickHouse table/part count, agent trace id, and
the time window. Redact secrets; never paste credentials.

## 5. Hypotheses and diagnosis

| Hypothesis | Why it was plausible | Test / next observation | Result |
|---|---|---|---|
| | | | |
| | | | |

**Root cause:**

Explain the technical causal chain. Name the triggering condition, the failed
boundary, why automatic recovery did or did not happen, and why the observed
symptom followed. If data was silently wrong, explain why normal health checks did
not reveal it.

## 6. Remediation and approval

**Immediate mitigation:**

What was changed, by whom, and why was it scoped and safe?

**Approval boundary:**

Which action could change state (restart, config edit, replay, SQL write,
retention adjustment)? Who approved it? Why was a stronger action not taken?

**Long-term fix:**

Describe the code/config/design change. Link or paste the relevant minimal diff.
State rollback conditions.

## 7. Verification

| Expected recovery signal | Actual result | Evidence |
|---|---|---|
| | | |
| canary verifier passes end to end | | |
| no regression in correctness/freshness | | |

Use a deterministic verifier where possible. “The dashboard became green” is not
sufficient verification.

## 8. Prevention and follow-up

| Action | Owner | Due date | Detect, prevent, or reduce blast radius? | Success measure |
|---|---|---|---|---|
| | | | | |

Consider monitoring, data-quality assertions, contract tests, capacity limits,
runbooks, least-privilege tools, and drills. State what would have detected the
incident earlier and what would have prevented it.

## 9. Agent-assistance appendix

Complete this section if an AI assistant was used. AI help is encouraged; hidden
or unsupported AI conclusions are not.

| Field | Record |
|---|---|
| Model/tool or framework | |
| Incident input given to it | |
| Allowed read-only tools | |
| Tools/actions denied | |
| Trace/run identifier | |
| Human approval requested / granted | |
| Useful suggestion | |
| Unsupported or unsafe suggestion | |
| Evaluation result | |

Attach or link the structured incident output. It must distinguish **observed
evidence** from **inference** and list uncertainty. A fluent narrative does not
substitute for an evidence trail.

## 10. Reflection

What was the misleading signal? What exact observation broke the tie between
competing explanations? Where would a deterministic workflow have been safer than
model judgment, and where did model judgment actually help?
