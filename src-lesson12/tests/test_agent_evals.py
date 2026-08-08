from __future__ import annotations

import unittest

from evals.runner import run_all
from evals.scenarios import SCENARIOS


class IncidentEvaluationTests(unittest.TestCase):
    def test_all_six_scenarios_score_perfectly_with_the_scripted_reference(
        self,
    ) -> None:
        results = run_all()
        self.assertEqual(len(results), 6)
        self.assertTrue(all(result.total == 1.0 for result in results))
        self.assertTrue(all("No remediation command" in result.notes[-1] for result in results))

    def test_evals_follow_the_bounded_scenario_catalogue(self) -> None:
        expected_tools = {
            "poison-deserialization": "poison_probe_logs",
            "partition-hotspot": "kafka_partition_offsets",
            "silent-data-contract": "source_business_outliers",
            "kafka-retention-risk": "retention_topic_config",
        }
        scenarios = {scenario.id: scenario for scenario in SCENARIOS}
        for scenario_id, tool_name in expected_tools.items():
            self.assertIn(tool_name, scenarios[scenario_id].required_tools)
