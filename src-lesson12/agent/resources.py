"""Local, deterministic runbook retrieval for Lesson 12.

Retrieved text is guidance, never a substitute for an observation from the running
stack. The workflow carries that distinction into every evidence ledger entry.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class RunbookResource:
    id: str
    title: str
    text: str


RESOURCES: tuple[RunbookResource, ...] = (
    RunbookResource(
        "evidence-policy",
        "Evidence policy",
        "Live metrics, logs, and database queries establish what happened. Runbooks suggest "
        "what to inspect next; they never prove a root cause by themselves.",
    ),
    RunbookResource(
        "poison-deserialization",
        "Poison-deserialization runbook",
        "Repeated failures at one Kafka offset call for identifying the bad record, preserving it "
        "as evidence, and using a bounded dead-letter path. Do not skip arbitrary ranges.",
    ),
    RunbookResource(
        "partition-hotspot",
        "Partition-hotspot runbook",
        "Compare maximum and median partition lag. A key change can sacrifice per-key ordering, "
        "so establish that business constraint before changing partitioning.",
    ),
    RunbookResource(
        "replication-slot",
        "Replication-slot runbook",
        "An inactive logical replication slot can retain WAL. "
        "Restoring a connector preserves data; "
        "dropping a slot can discard CDC history and always needs an approved recovery plan.",
    ),
    RunbookResource(
        "schema-contract",
        "Semantic-schema runbook",
        "Compatibility checks syntax, not business meaning. Field renames need expand/contract, "
        "known-value contract tests, and a deliberate backfill plan.",
    ),
    RunbookResource(
        "clickhouse-parts",
        "ClickHouse parts runbook",
        "Too many small active parts create merge pressure. Correlate system.parts with batch size "
        "and sink latency before changing write batching.",
    ),
    RunbookResource(
        "kafka-storage",
        "Kafka storage runbook",
        "Retention is a storage budget. Verify free space and recovery requirements "
        "before reducing "
        "retention; never make a retention change without an explicit approval boundary.",
    ),
)


class LexicalRunbookRetriever:
    """Small transparent retrieval: token overlap, deterministic tie breaking, no vector DB."""

    def __init__(self, resources: tuple[RunbookResource, ...] = RESOURCES) -> None:
        self.resources = resources

    def search(self, query: str, limit: int = 2) -> tuple[RunbookResource, ...]:
        tokens = set(re.findall(r"[a-z0-9]+", query.lower()))
        ranked = sorted(
            self.resources,
            key=lambda item: (
                -len(tokens & set(re.findall(r"[a-z0-9]+", f"{item.title} {item.text}".lower()))),
                item.id,
            ),
        )
        return tuple(ranked[:limit])

    def render(self, query: str, limit: int = 2) -> str:
        matches = self.search(query, limit)
        return "\n".join(
            f"[retrieved guidance: {item.id}] {item.title}: {item.text}" for item in matches
        )
