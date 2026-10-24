# Troubleshooting

**`docker: command not found` / Docker socket permission denied**: install and start Docker Engine on Linux; confirm `docker ps` works with your chosen privileges. If only `sudo docker` works, run `sudo .venv/bin/campus-net demo` with environment considerations or configure Docker group access carefully (Docker group effectively gives host-root privileges).

**`containerlab: command not found`**: install Containerlab from official instructions; check `containerlab version`.

**No OSPF Full neighbors**: verify all containers are running, check `docker logs clab-campus-net-resilience-r1`, and `docker exec ... vtysh -c 'show ip ospf neighbor'`. Check the FRR config mounts and eth1/eth2 addresses.

**Unexpected route**: inspect `show ip route 10.20.30.0/24` and `show ip ospf interface`. OSPF must have converged. Do not adjust costs without updating the tests.

**Ping fails though the route exists**: check the return path on r3, host IP settings, Linux forwarding and interfaces. Both directions must converge after a failure.

**Interrupted during fault injection**: restore the fixed lab link with `docker exec clab-campus-net-resilience-r1 ip link set dev eth2 up`. Restart the demo only after confirming normal connectivity.

**Mac/Windows**: use an Ubuntu Linux VM with Docker Engine; do not assume Docker Desktop supports the same privileged network links and interface behavior.

**Lab image download fails**: check network access to quay.io and Docker Hub, then retry. Do not commit private registry credentials.
