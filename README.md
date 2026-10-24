# Campus Network Reliability Lab

## The Problem

A campus network has one path between students and a server. When that link fails, the service is down until someone manually reroutes traffic. There is no way to test whether a backup path actually works, or whether the preferred path recovers after repair.

## The Solution

This lab builds a three-router OSPF network using Containerlab and FRRouting. OSPF automatically prefers the direct `r1 → r3` link. When that link is disabled, traffic reroutes through `r1 → r2 → r3`. A Python CLI verifies every stage: neighbor adjacency, route convergence, end-to-end connectivity, safe fault injection, backup verification, link restoration, and recovery confirmation. Every result is saved as a JSON evidence file.

```
Student PC ── r1 ──primary── r3 ── Campus server
               │              │
               └──── r2 ──────┘
                   (backup)
```

No repair runs without verification. No link stays down after the test, even if a step fails.

## Tech Stack

- **FRRouting** — OSPF routing on each router container
- **Containerlab** — reproducible network topology as YAML
- **Python** — CLI for validation, fault injection, and evidence collection
- **Docker** — isolates each router and host as a container

## Quick Start

Requires Linux with Docker, [Containerlab](https://containerlab.dev/install/), Python 3.10+.

```bash
cd campus-network-reliability-lab
python3 -m venv .venv && source .venv/bin/activate
pip install -e '.[dev]'

# Static validation (no Docker needed)
campus-net validate

# Deploy lab and run failover test
sudo containerlab deploy -t campus.clab.yml
campus-net demo

# Clean up
sudo containerlab destroy -t campus.clab.yml --cleanup
```

## Tests

```bash
pytest -v
```

33 tests cover route parsing, OSPF neighbor detection, failover sequencing, recovery-after-failure, timeout handling, input validation, Docker command safety, CLI error paths, and JSON evidence serialization. No Docker required for tests.

## Project Structure

```
campus_net/    Route parsing, failover scenario, config validator, CLI
configs/       FRR router configurations (r1, r2, r3)
tests/         33 automated tests
docs/          Architecture, demo walkthrough, troubleshooting
```

## Key Design Decisions

- **Always restore.** The test restores the disabled link even when earlier steps fail. If the process crashes, a manual recovery command is documented.
- **Validate before running.** The CLI checks topology, IP addressing, subnet consistency, OSPF advertisements, and router IDs before any Docker command.
- **No shell=True.** Docker commands are built as argument lists. Only the five known lab containers are reachable.
- **Fake runner for tests.** A protocol-based Runner lets all scenario logic run against a deterministic fake, with no Docker dependency.

## Verified Results

- **33 unit tests pass** — route parsing, OSPF neighbor detection, failover sequencing, recovery-after-failure, timeout handling, input validation, Docker command safety, CLI error paths, JSON evidence serialization
- **Static validation pass** — `campus-net validate` checks topology YAML, IP addressing, subnet consistency, OSPF advertisements, router IDs, and passive interfaces against the FRR configs

### Limitations

- **Requires Linux host.** Containerlab uses Linux network namespaces (`ip netns`) and cannot run on macOS Docker Desktop or Windows WSL2 Docker. Integration testing (live OSPF failover) requires a Linux VM or bare-metal Linux with Docker and Containerlab installed.
- **No live failover test included in CI.** GitHub Actions runs unit tests and static validation only. The full OSPF failover demo (`campus-net demo`) requires a Containerlab-capable host.

## Docs

[Architecture](docs/ARCHITECTURE.md) · [Demo Guide](docs/DEMO.md) · [Test Report](docs/TEST_REPORT.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)

## License

[MIT](LICENSE)
