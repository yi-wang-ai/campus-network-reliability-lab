# Test report — v1.0.0

## Local results (2026-10-24)

- `campus-net validate`: **PASS**.
- `pytest -q --cov=campus_net --cov-report=term-missing --cov-fail-under=80`: **33 passed**, **91.93% statement coverage** (rounded to 92%).
- `python -m compileall -q campus_net tests`: **PASS**.
- `pip install -e . --no-build-isolation --no-deps --no-index`: **PASS** with dependencies preinstalled in the test environment.
- `ruff check .`: **not run locally** (Ruff is not installed in this offline environment). Configured in GitHub Actions.

## Verification types

- Local validation tests: PyYAML config integrity and expected lab addressing.
- Unit tests: next-hop parsing, OSPF neighbor parsing, failure/restore paths, safe Docker scoping, JSON output.
- GitHub Actions: same tests with Python 3.12 and lint checks. CI configuration included; hosted CI status is not claimed until GitHub runs it.
- **Not executed here:** actual Docker images, Containerlab deployment, FRRouting startup, OSPF convergence and live end-to-end ping. The authoring environment does not provide Docker/Containerlab.

Run locally:

```bash
pip install -e '.[dev]'
ruff check .
campus-net validate
pytest -q --cov=campus_net --cov-report=term-missing
```

The README is intentionally limited to verified statements. After a successful Linux lab run, record the actual results and timestamp here, then attach your `artifacts/ospf-failover-*.json` evidence and screenshots. Avoid uploading sensitive host settings.
