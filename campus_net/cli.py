"""Command-line entry point. Fault injection requires explicit `demo`."""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from campus_net.runner import DockerRunner
from campus_net.scenario import FailoverScenario, Report
from campus_net.validator import validate


def project_root() -> Path:
    return Path(__file__).resolve().parent.parent


def save_report(report: Report, filename: Path) -> None:
    filename.parent.mkdir(parents=True, exist_ok=True)
    filename.write_text(json.dumps(report.to_dict(), indent=2) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Campus OSPF failure/recovery network lab")
    subs = parser.add_subparsers(dest="command", required=True)
    subs.add_parser("validate", help="Check YAML, routing config and addressing without Docker")
    demo = subs.add_parser("demo", help="Inject one lab link failure; always attempt restoration")
    demo.add_argument("--timeout", type=float, default=75)
    demo.add_argument("--interval", type=float, default=2)
    demo.add_argument("--output", type=Path, default=None)
    args = parser.parse_args(argv)
    errors = validate(project_root())
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 2
    if args.command == "validate":
        print("PASS: topology, interfaces, subnets, FRR configs and router IDs")
        return 0

    if args.timeout <= 0 or args.interval <= 0:
        parser.error("--timeout and --interval must be positive")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    dest = args.output or Path("artifacts") / f"ospf-failover-{stamp}.json"
    runner = DockerRunner()
    try:
        ready = runner.execute("r1", "true")
    except (RuntimeError, OSError) as exc:
        print(f"Cannot access Docker lab: {exc}", file=sys.stderr)
        return 2
    if ready.returncode != 0:
        print("Lab is not running. Deploy it with containerlab first.", file=sys.stderr)
        return 2
    report = FailoverScenario(runner, timeout=args.timeout, interval=args.interval).run()
    save_report(report, dest)
    for step in report.steps:
        mark = "PASS" if step.passed else "FAIL"
        print(f"{mark:4} {step.label}: {step.detail} ({step.seconds:.2f}s)")
    for error in report.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    print(f"{report.status}: evidence saved to {dest}")
    return 0 if report.status == "PASSED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
