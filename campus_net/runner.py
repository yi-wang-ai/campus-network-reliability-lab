"""Run fixed commands only inside the five known lab containers."""

import subprocess
from dataclasses import dataclass
from typing import Protocol, Sequence

LAB_NAME = "campus-net-resilience"
NODES = frozenset({"r1", "r2", "r3", "client", "server"})


@dataclass(frozen=True)
class Result:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class Runner(Protocol):
    def execute(self, node: str, *args: str) -> Result:
        ...


class DockerRunner:
    """No shell=True, external commands or arbitrary container names."""

    is_live = True

    def __init__(self, timeout: int = 15):
        self.timeout = timeout

    def execute(self, node: str, *args: str) -> Result:
        if node not in NODES:
            raise ValueError(f"Unknown lab node: {node}")
        if not args:
            raise ValueError("A command is required")
        command: Sequence[str] = ("docker", "exec", f"clab-{LAB_NAME}-{node}", *args)
        try:
            completed = subprocess.run(
                command, text=True, capture_output=True, timeout=self.timeout, check=False
            )
        except FileNotFoundError as exc:
            raise RuntimeError("Docker was not found; see the setup instructions") from exc
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError(f"Docker command timed out on {node}: {args[0]}") from exc
        return Result(completed.returncode, completed.stdout, completed.stderr)
