import json

import pytest

from campus_net.cli import main, save_report
from campus_net.runner import DockerRunner, Result
from campus_net.scenario import FailoverScenario


class FakeRunner:
    def __init__(self, fail_ping_after_outage=False, fail_restore=False, no_neighbor=False):
        self.state = "up"
        self.calls = []
        self.fail_ping_after_outage = fail_ping_after_outage
        self.fail_restore = fail_restore
        self.no_neighbor = no_neighbor

    def execute(self, node, *args):
        self.calls.append((node, args))
        if args == ("true",):
            return Result(0)
        if args[:3] == ("ip", "link", "set"):
            state = args[-1]
            if state == "up" and self.fail_restore:
                return Result(1, stderr="simulated interface failure")
            self.state = state
            return Result(0)
        if args[:2] == ("vtysh", "-c"):
            if "neighbor" in args[-1]:
                if self.no_neighbor:
                    return Result(0, "1.1.1.1 Init")
                return Result(0, "2.2.2.2 1 Full/- 00:00:03\n3.3.3.3 1 Full/- 00:00:03")
            hop = "10.0.13.2" if self.state == "up" else "10.0.12.2"
            return Result(0, f"O>* 10.20.30.0/24 via {hop}, eth2")
        if args[0] == "ping":
            if self.state == "down" and self.fail_ping_after_outage:
                return Result(1, "0 received")
            return Result(0, "1 packets transmitted, 1 received, 0% packet loss")
        raise ValueError(f"Unknown fake command: {args}")


class TickClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        self.t += 0.1
        return self.t

    def sleep(self, seconds):
        self.t += seconds


def make_scenario(runner, timeout=2):
    clock = TickClock()
    return FailoverScenario(runner, timeout=timeout, interval=0.3, clock=clock, sleeper=clock.sleep)


def test_happy_path_passes_and_restores():
    runner = FakeRunner()
    report = make_scenario(runner).run()
    assert report.status == "PASSED"
    assert not report.live_test  # fake runner is only a unit-test simulation
    assert len(report.steps) == 9
    assert runner.state == "up"
    assert ("r1", ("ip", "link", "set", "dev", "eth2", "down")) in runner.calls
    assert ("r1", ("ip", "link", "set", "dev", "eth2", "up")) in runner.calls


def test_failure_still_restores():
    runner = FakeRunner(fail_ping_after_outage=True)
    report = make_scenario(runner).run()
    assert report.status == "FAILED"
    assert runner.state == "up"
    assert any(step.label == "Restore primary link" and step.passed for step in report.steps)


def test_restore_failure_reported():
    runner = FakeRunner(fail_restore=True)
    report = make_scenario(runner).run()
    assert report.status == "FAILED"
    assert any("RECOVERY ERROR" in x for x in report.errors)


def test_neighbor_timeout_has_no_fault_injection():
    runner = FakeRunner(no_neighbor=True)
    report = make_scenario(runner, timeout=1).run()
    assert report.status == "FAILED"
    assert not any(args[-1:] == ("down",) for _, args in runner.calls)


def test_timeout_validation():
    with pytest.raises(ValueError):
        FailoverScenario(FakeRunner(), timeout=-1)


def test_result_serialized(tmp_path):
    report = make_scenario(FakeRunner()).run()
    file = tmp_path / "nested/evidence.json"
    save_report(report, file)
    data = json.loads(file.read_text())
    assert data["status"] == "PASSED"
    assert data["lab"] == "campus-net-resilience"
    assert len(data["steps"]) == 9


def test_cli_validate(capsys):
    assert main(["validate"]) == 0
    assert "PASS" in capsys.readouterr().out


def test_docker_rejects_unknown_container():
    with pytest.raises(ValueError, match="Unknown lab node"):
        DockerRunner().execute("production", "true")


def test_docker_rejects_empty_command():
    with pytest.raises(ValueError, match="command"):
        DockerRunner().execute("r1")


def test_docker_invocation_safe(monkeypatch):
    recorded = {}
    class Finished:
        returncode = 0
        stdout = "ok"
        stderr = ""
    def fake_run(command, **kwargs):
        recorded["command"] = command
        recorded["kwargs"] = kwargs
        return Finished()
    monkeypatch.setattr("campus_net.runner.subprocess.run", fake_run)
    result = DockerRunner().execute("r1", "vtysh", "-c", "show ip route")
    assert result.stdout == "ok"
    assert recorded["command"][:3] == ("docker", "exec", "clab-campus-net-resilience-r1")
    assert not recorded["kwargs"].get("shell", False)


def test_failed_disable_response_still_attempts_restore():
    class PartialFailure(FakeRunner):
        def execute(self, node, *args):
            result = super().execute(node, *args)
            if args[-1:] == ("down",):
                return Result(1, stderr="reported failure after changing interface")
            return result

    runner = PartialFailure()
    report = make_scenario(runner).run()
    assert report.status == "FAILED"
    assert runner.state == "up"
    assert any(s.label == "Restore primary link" and s.passed for s in report.steps)


def test_cli_preflight_failure(monkeypatch, capsys):
    class MissingLab:
        def execute(self, node, *args):
            return Result(1, stderr="not found")

    monkeypatch.setattr("campus_net.cli.DockerRunner", MissingLab)
    assert main(["demo"]) == 2
    assert "not running" in capsys.readouterr().err


def test_cli_demo_creates_evidence_with_fake_runner(monkeypatch, tmp_path):
    monkeypatch.setattr("campus_net.cli.DockerRunner", FakeRunner)
    dest = tmp_path / "evidence.json"
    assert main(["demo", "--output", str(dest)]) == 0
    evidence = json.loads(dest.read_text())
    assert evidence["status"] == "PASSED"
    assert evidence["live_test"] is False
