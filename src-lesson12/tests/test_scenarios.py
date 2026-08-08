"""Deterministic tests: all Docker commands are mocked."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from scenarios.catalog import SCENARIOS
from scenarios.controller import ScenarioController


class RecordingRunner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, ...]] = []

    def __call__(self, argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
        self.calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "ok", "")


class ScenarioControllerTests(unittest.TestCase):
    def make_controller(self) -> tuple[ScenarioController, RecordingRunner]:
        tempdir = tempfile.TemporaryDirectory()
        self.addCleanup(tempdir.cleanup)
        runner = RecordingRunner()
        return (
            ScenarioController(
                SCENARIOS,
                Path(tempdir.name) / "state.json",
                Path("/example/src-lesson12/docker-compose.yml"),
                runner,
            ),
            runner,
        )

    def test_catalog_has_six_unique_bounded_scenarios(self) -> None:
        self.assertEqual(len(SCENARIOS), 6)
        self.assertEqual(set(SCENARIOS), {scenario.id for scenario in SCENARIOS.values()})
        self.assertTrue(all(scenario.timebox_seconds <= 120 for scenario in SCENARIOS.values()))
        self.assertTrue(all(scenario.safety_boundary for scenario in SCENARIOS.values()))
        self.assertTrue(
            all(
                scenario.evidence and scenario.fix and scenario.prevention
                for scenario in SCENARIOS.values()
            )
        )

    def test_activate_is_dry_run_by_default(self) -> None:
        controller, runner = self.make_controller()
        commands = controller.activate("partition-hotspot")
        self.assertTrue(commands)
        self.assertEqual(runner.calls, [])
        self.assertEqual(controller.active_ids(), set())
        self.assertIn("docker compose", commands[0])

    def test_apply_activate_then_reset_executes_only_expected_commands(self) -> None:
        controller, runner = self.make_controller()
        controller.activate("paused-connector-slot-risk", apply=True)
        self.assertEqual(len(runner.calls), 2)
        self.assertIn("connect", runner.calls[0])
        self.assertEqual(controller.active_ids(), {"paused-connector-slot-risk"})

        reset_preview = controller.reset("paused-connector-slot-risk")
        self.assertEqual(len(runner.calls), 2, "reset preview must not execute Docker")
        self.assertIn("unpause", reset_preview[0])

        controller.reset("paused-connector-slot-risk", apply=True)
        self.assertEqual(len(runner.calls), 3)
        self.assertEqual(controller.active_ids(), set())

    def test_only_one_scenario_can_be_active(self) -> None:
        controller, _ = self.make_controller()
        controller.activate("partition-hotspot", apply=True)
        with self.assertRaisesRegex(ValueError, "partition-hotspot is already active"):
            controller.activate("kafka-retention-risk", apply=True)

    def test_isolated_topics_are_never_the_orders_topic(self) -> None:
        for scenario_id in ("poison-deserialization", "kafka-retention-risk"):
            scenario = SCENARIOS[scenario_id]
            activation = " ".join(part for command in scenario.activate for part in command.argv)
            self.assertIn("l12.", activation)
            self.assertNotIn("--topic cdc.public.orders", activation)

    def test_poison_fixture_encodes_declared_schema_id_999999(self) -> None:
        activation = " ".join(
            part
            for command in SCENARIOS["poison-deserialization"].activate
            for part in command.argv
        )
        self.assertIn(r"\000\000\017\102\077", activation)

    def test_manifest_contains_agent_evidence_and_commands(self) -> None:
        controller, _ = self.make_controller()
        manifest = controller.manifest("silent-data-contract")["silent-data-contract"]
        self.assertTrue(manifest["evidence"])
        self.assertTrue(manifest["activate_commands"])
        self.assertTrue(manifest["reset_commands"])


if __name__ == "__main__":
    unittest.main()
