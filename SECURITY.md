# Security and scope

This is an isolated educational lab. Never run its fault-injection command on production routers or workstations. The `demo` command only addresses Docker containers under the fixed `clab-campus-net-resilience-*` prefix and toggles r1:eth2.

Containerlab and Docker require elevated host privileges. Prefer a disposable Ubuntu VM rather than a company laptop or shared production server. Grant Docker socket access only to trusted users. Review the upstream container images and their licenses before deployment.

The Python recovery cleanup is best effort, and it cannot restore a link following SIGKILL or host crashes. A manual recovery command appears in README. Any reported results must come from a real run: do not fabricate logs, screenshots or performance metrics.

For vulnerability reports, open a private GitHub security advisory rather than a public issue. Do not include secrets or IPs from real networks.
