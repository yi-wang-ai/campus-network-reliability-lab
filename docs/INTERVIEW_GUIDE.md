# Interview questions

**Why OSPF?** It calculates paths from link-state data and updates routes after a topology change, which makes it suitable for demonstrating automatic failover.

**Why does the direct link win?** Its configured cost (5) is below the two-hop backup (10 + 10), before the final attached network cost.

**What happens during a failure?** r1 loses its adjacency with r3 on the direct connection, calculates the backup next hop through r2, and traffic resumes when both directions converge.

**How is failure verified?** The CLI checks OSPF neighbors, the actual chosen next hop, and end-to-end ping, before and after the injected failure.

**Is this production-ready?** No. It is a disposable lab. Production networks need device backups, approvals, monitoring, staged rollouts, security controls and testing under real traffic.

**What is original work?** The topology, routing configuration, safety-scoped Python automation, validator, tests and docs, not the FRR or Containerlab projects themselves.
