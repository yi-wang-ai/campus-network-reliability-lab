"""Fault injection, route verification, safe restoration, and audit evidence."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from time import monotonic, sleep
from typing import Callable

from campus_net.routes import full_neighbor_count, next_hops
from campus_net.runner import Runner

DESTINATION = "10.20.30.0/24"
SERVER_IP = "10.20.30.10"
PRIMARY_NEXTHOP = "10.0.13.2"
BACKUP_NEXTHOP = "10.0.12.2"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Step:
    label: str
    passed: bool
    detail: str
    seconds: float


@dataclass
class Report:
    scenario: str = "ospf-primary-link-failure"
    lab: str = "campus-net-resilience"
    started_at: str = field(default_factory=_utc_now)
    finished_at: str = ""
    status: str = "FAILED"
    live_test: bool = False
    steps: list[Step] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


class ScenarioError(RuntimeError):
    pass


class FailoverScenario:
    def __init__(
        self,
        runner: Runner,
        *,
        timeout: float = 75,
        interval: float = 2,
        clock: Callable[[], float] = monotonic,
        sleeper: Callable[[float], None] = sleep,
    ):
        if timeout <= 0 or interval <= 0:
            raise ValueError("timeout and interval must both be positive")
        self.runner = runner
        self.timeout = timeout
        self.interval = interval
        self.clock = clock
        self.sleeper = sleeper
        self.report = Report(live_test=bool(getattr(runner, "is_live", False)))

    def _record(self, label: str, action: Callable[[], str]) -> None:
        start = self.clock()
        try:
            detail = action()
            self.report.steps.append(Step(label, True, detail, round(self.clock() - start, 3)))
        except Exception as exc:
            self.report.steps.append(Step(label, False, str(exc), round(self.clock() - start, 3)))
            raise

    def _command(self, node: str, *args: str) -> str:
        result = self.runner.execute(node, *args)
        if result.returncode:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown error"
            raise ScenarioError(f"{node}: {args[0]} returned {result.returncode}: {detail}")
        return result.stdout

    def _wait(self, label: str, check: Callable[[], bool]) -> str:
        started = self.clock()
        last_error = "no matching result"
        while self.clock() - started <= self.timeout:
            try:
                if check():
                    return f"{label} confirmed"
            except (ScenarioError, RuntimeError) as exc:
                last_error = str(exc)
            self.sleeper(self.interval)
        raise ScenarioError(f"Timed out waiting for {label}: {last_error}")

    def _neighbors(self) -> str:
        def ready() -> bool:
            output = self._command("r1", "vtysh", "-c", "show ip ospf neighbor")
            return full_neighbor_count(output) >= 2
        return self._wait("2 full OSPF neighbors on r1", ready)

    def _route(self, next_hop: str) -> str:
        def ready() -> bool:
            output = self._command("r1", "vtysh", "-c", f"show ip route {DESTINATION}")
            return next_hop in next_hops(output)
        return self._wait(f"route to {DESTINATION} via {next_hop}", ready)

    def _ping(self) -> str:
        def ready() -> bool:
            result = self.runner.execute("client", "ping", "-c", "1", "-W", "2", SERVER_IP)
            return result.returncode == 0
        return self._wait(f"client reaches {SERVER_IP}", ready)

    def _link(self, state: str) -> str:
        if state not in {"up", "down"}:
            raise ValueError("Unsupported interface state")
        self._command("r1", "ip", "link", "set", "dev", "eth2", state)
        return f"lab-only link r1:eth2 set {state}"

    def run(self) -> Report:
        disabled = False
        try:
            self._record("OSPF adjacency", self._neighbors)
            self._record("Primary route", lambda: self._route(PRIMARY_NEXTHOP))
            self._record("Baseline connectivity", self._ping)
            # Even a failed Docker response may leave the link disabled; always restore.
            disabled = True
            self._record("Inject r1-r3 link failure", lambda: self._link("down"))
            self._record("Backup route", lambda: self._route(BACKUP_NEXTHOP))
            self._record("Connectivity during failover", self._ping)
        except Exception as exc:
            self.report.errors.append(str(exc))
        finally:
            if disabled:
                try:
                    self._record("Restore primary link", lambda: self._link("up"))
                    self._record("Primary route returns", lambda: self._route(PRIMARY_NEXTHOP))
                    self._record("Connectivity after recovery", self._ping)
                except Exception as exc:
                    self.report.errors.append(f"RECOVERY ERROR: {exc}")
        self.report.finished_at = _utc_now()
        if not self.report.errors and len(self.report.steps) == 9 and all(s.passed for s in self.report.steps):
            self.report.status = "PASSED"
        return self.report
