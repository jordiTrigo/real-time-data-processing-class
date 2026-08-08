"""Execution and state management for the Lesson 12 scenario catalogue."""

from __future__ import annotations

import json
import shlex
import subprocess
from collections.abc import Callable, Iterable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .catalog import Command, Scenario

CommandRunner = Callable[[tuple[str, ...]], subprocess.CompletedProcess[str]]


def default_runner(argv: tuple[str, ...]) -> subprocess.CompletedProcess[str]:
    """Run one command with a finite timeout and leave its evidence visible."""
    return subprocess.run(argv, check=True, text=True, timeout=180)


def command_text(command: Command, compose_file: Path) -> str:
    """Render a command without executing it, suitable for a projector or agent trace."""
    argv = tuple(str(compose_file) if part == "{compose_file}" else part for part in command.argv)
    return shlex.join(argv)


class ScenarioController:
    """Small state machine: inactive -> active -> inactive.

    The state file records only that the controller completed an activation. It
    never claims that a process recovered; probes remain the evidence source.
    """

    def __init__(
        self,
        scenarios: dict[str, Scenario],
        state_file: Path,
        compose_file: Path,
        runner: CommandRunner = default_runner,
    ) -> None:
        self.scenarios = scenarios
        self.state_file = state_file
        self.compose_file = compose_file
        self.runner = runner

    def _state(self) -> dict[str, dict[str, str]]:
        if not self.state_file.exists():
            return {}
        data = json.loads(self.state_file.read_text())
        if not isinstance(data, dict) or not all(
            isinstance(value, dict) for value in data.values()
        ):
            raise ValueError(f"invalid scenario state file: {self.state_file}")
        return data

    def _write_state(self, state: dict[str, dict[str, str]]) -> None:
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.state_file.with_suffix(self.state_file.suffix + ".tmp")
        temporary.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")
        temporary.replace(self.state_file)

    def scenario(self, scenario_id: str) -> Scenario:
        try:
            return self.scenarios[scenario_id]
        except KeyError as error:
            known = ", ".join(sorted(self.scenarios))
            raise KeyError(f"unknown scenario {scenario_id!r}; choose one of: {known}") from error

    def active_ids(self) -> set[str]:
        return set(self._state())

    def activate(self, scenario_id: str, *, apply: bool = False) -> list[str]:
        scenario = self.scenario(scenario_id)
        state = self._state()
        if scenario_id in state:
            raise ValueError(f"{scenario_id} is already active; reset it before reactivating")
        if state:
            active_id = next(iter(state))
            raise ValueError(
                f"{active_id} is already active; reset it before activating {scenario_id}"
            )
        rendered = [command_text(command, self.compose_file) for command in scenario.activate]
        if not apply:
            return rendered
        self._run(scenario.activate)
        state[scenario_id] = {
            "activated_at": datetime.now(UTC).isoformat(),
            "title": scenario.title,
        }
        self._write_state(state)
        return rendered

    def reset(self, scenario_id: str, *, apply: bool = False) -> list[str]:
        scenario = self.scenario(scenario_id)
        state = self._state()
        if scenario_id not in state:
            raise ValueError(f"{scenario_id} is not active")
        rendered = [command_text(command, self.compose_file) for command in scenario.reset]
        if not apply:
            return rendered
        self._run(scenario.reset)
        del state[scenario_id]
        self._write_state(state)
        return rendered

    def probe(self, scenario_id: str, *, apply: bool = False) -> list[str]:
        scenario = self.scenario(scenario_id)
        rendered = [command_text(command, self.compose_file) for command in scenario.probes]
        if apply:
            self._run(scenario.probes)
        return rendered

    def manifest(self, scenario_id: str | None = None) -> dict[str, Any]:
        selected: Iterable[Scenario]
        if scenario_id is None:
            selected = (self.scenarios[key] for key in sorted(self.scenarios))
        else:
            selected = (self.scenario(scenario_id),)
        return {
            scenario.id: {
                key: value
                for key, value in asdict(scenario).items()
                if key not in {"activate", "reset", "probes"}
            }
            | {
                "activate_commands": [
                    command_text(command, self.compose_file) for command in scenario.activate
                ],
                "reset_commands": [
                    command_text(command, self.compose_file) for command in scenario.reset
                ],
                "probe_commands": [
                    command_text(command, self.compose_file) for command in scenario.probes
                ],
            }
            for scenario in selected
        }

    def _run(self, commands: Iterable[Command]) -> None:
        for command in commands:
            argv = tuple(
                str(self.compose_file) if part == "{compose_file}" else part
                for part in command.argv
            )
            self.runner(argv)
