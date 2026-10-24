# Five-minute interview demo (after lab deployment)

1. **Problem (30 seconds):** a campus server must remain reachable if one router link goes down.
2. **Architecture (30 seconds):** show the triangle diagram, FRR configs, and OSPF costs in `configs/`.
3. **Baseline (1 minute):** run `campus-net validate`, then show `show ip route 10.20.30.0/24` and `ping`.
4. **Failure (1 minute):** run `campus-net demo`, explain why route changes from 10.0.13.2 to 10.0.12.2.
5. **Evidence (1 minute):** open the generated `artifacts/ospf-failover-*.json` and discuss route/ping checks, recovery and limitations.
6. **Engineering (1 minute):** show unit tests and GitHub Actions CI; explain the `finally` safety cleanup and manual recovery command.

Do not show invented performance numbers. If the live test fails, preserve the failing JSON, use `docs/TROUBLESHOOTING.md`, and explain the diagnosis.

## Suggested screenshots to capture

- Containerlab `inspect` output showing all five containers.
- OSPF neighbors and primary routing table on r1.
- Terminal output of the real failover demo.
- Generated evidence JSON and green GitHub Actions run.

No screenshots are included until they are captured from a real lab.
