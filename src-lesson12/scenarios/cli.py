"""Control self-contained Lesson 12 incident fixtures.

Examples, from the repository root:

  python src-lesson12/scenarios/cli.py status
  python src-lesson12/scenarios/cli.py activate partition-hotspot
  python src-lesson12/scenarios/cli.py activate partition-hotspot --apply
  python src-lesson12/scenarios/cli.py reset partition-hotspot --apply
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in {None, ""}:  # support direct invocation shown above
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from scenarios.catalog import SCENARIOS
    from scenarios.controller import ScenarioController
else:
    from .catalog import SCENARIOS
    from .controller import ScenarioController


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_COMPOSE = ROOT / "src-lesson12" / "docker-compose.yml"
DEFAULT_STATE = ROOT / "src-lesson12" / ".scenario-state.json"


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Safe Lesson 12 incident scenario controller")
    result.add_argument(
        "--compose-file",
        type=Path,
        default=DEFAULT_COMPOSE,
        help="Lesson 12 compose file; no compose file is modified",
    )
    result.add_argument(
        "--state-file",
        type=Path,
        default=DEFAULT_STATE,
        help="local controller state (default: src-lesson12/.scenario-state.json)",
    )
    subcommands = result.add_subparsers(dest="command", required=True)
    subcommands.add_parser("list", help="list scenario IDs and safety boundaries")
    status = subcommands.add_parser(
        "status", help="show controller state and optional read-only probes"
    )
    status.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS))
    status.add_argument("--live", action="store_true", help="run read-only probes")
    for name, help_text in (
        ("activate", "activate one scenario"),
        ("reset", "reset one active scenario"),
    ):
        action = subcommands.add_parser(name, help=help_text)
        action.add_argument("scenario", choices=sorted(SCENARIOS))
        action.add_argument(
            "--apply",
            action="store_true",
            help="execute the displayed bounded commands; omission is dry-run",
        )
    manifest = subcommands.add_parser(
        "manifest", help="emit agent-friendly scenario metadata as JSON"
    )
    manifest.add_argument("scenario", nargs="?", choices=sorted(SCENARIOS))
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    controller = ScenarioController(SCENARIOS, args.state_file, args.compose_file)
    if args.command == "list":
        for scenario in sorted(SCENARIOS.values(), key=lambda item: item.id):
            print(f"{scenario.id}: {scenario.title}\n  safety: {scenario.safety_boundary}")
        return 0
    if args.command == "manifest":
        print(json.dumps(controller.manifest(args.scenario), indent=2, sort_keys=True))
        return 0
    if args.command == "status":
        active = controller.active_ids()
        scenarios = [args.scenario] if args.scenario else sorted(SCENARIOS)
        for scenario_id in scenarios:
            marker = "ACTIVE" if scenario_id in active else "inactive"
            print(f"{marker:8} {scenario_id}")
            if args.live:
                for command in controller.probe(scenario_id, apply=True):
                    print(f"  probed: {command}")
        return 0
    action = controller.activate if args.command == "activate" else controller.reset
    commands = action(args.scenario, apply=args.apply)
    mode = "applied" if args.apply else "dry-run (pass --apply to execute)"
    print(f"{args.command} {args.scenario}: {mode}")
    for command in commands:
        print(f"  {command}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
