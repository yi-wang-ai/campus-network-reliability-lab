# Architecture

## Why this design

Three OSPF routers form a triangle. The direct r1-r3 link is preferred by cost, but r1-r2-r3 remains available during a primary-link outage. Two end hosts represent a student network and a campus application network. No real campus equipment is affected.

| Link | r1/r2/r3 interface | Address network | OSPF cost |
|---|---|---|---|
| r1–r2 | r1 eth1, r2 eth1 | 10.0.12.0/30 | 10 |
| r2–r3 | r2 eth2, r3 eth1 | 10.0.23.0/30 | 10 |
| r1–r3 | r1 eth2, r3 eth2 | 10.0.13.0/30 | 5 |
| client–r1 | client eth1, r1 eth3 | 10.20.10.0/24 | access / passive |
| server–r3 | server eth1, r3 eth3 | 10.20.30.0/24 | access / passive |

OSPF area is `0.0.0.0`. Router IDs are `1.1.1.1`, `2.2.2.2`, `3.3.3.3`. The clients use scoped static routes for the remote `/24`, leaving their Docker management networks unchanged.

Each transit port uses point-to-point OSPF, hello 1 s and dead 4 s **for a fast lab demonstration**. In a real network, these timers need careful operational review. The health checker polls, rather than assuming convergence is immediate.

`campus-net validate` checks the fixed topology, unique endpoints, IP subnet pairs, router IDs, passive access interfaces and OSPF advertised networks. `campus-net demo` runs only inside `clab-campus-net-resilience-*` containers. It never changes the host's network interfaces.

## Failure-to-recovery test

1. Confirm two OSPF Full neighbors on r1.
2. Confirm route to 10.20.30.0/24 uses 10.0.13.2, then ping server.
3. Disable r1:eth2 (the primary link) via Docker exec.
4. Wait until r1 selects 10.0.12.2 via r2, then ping server again.
5. In a `finally` cleanup block, re-enable r1:eth2.
6. Wait for primary route and connectivity, write a JSON audit report.

The runner restores the interface after normal Python exceptions. It cannot guarantee cleanup after a machine crash, SIGKILL, or power loss. A manual recovery command is provided in README.
