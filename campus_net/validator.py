"""Fail fast on unsafe or inconsistent topology and FRR addressing."""

import re
from ipaddress import IPv4Interface
from pathlib import Path

import yaml

EXPECTED_NODES = {"r1", "r2", "r3", "client", "server"}
EXPECTED_LINKS = {
    frozenset(("r1:eth1", "r2:eth1")),
    frozenset(("r2:eth2", "r3:eth1")),
    frozenset(("r1:eth2", "r3:eth2")),
    frozenset(("client:eth1", "r1:eth3")),
    frozenset(("server:eth1", "r3:eth3")),
}


def _router_interfaces(text: str) -> dict[str, IPv4Interface]:
    addresses: dict[str, IPv4Interface] = {}
    current: str | None = None
    for raw in text.splitlines():
        line = raw.strip()
        if raw.startswith("interface "):
            current = line.split(maxsplit=1)[1]
        elif line == "!":
            current = None
        elif current and line.startswith("ip address "):
            if current in addresses:
                raise ValueError(f"Repeated IP configuration on {current}")
            addresses[current] = IPv4Interface(line.split()[-1])
    return addresses


def _host_interfaces(commands: list[str]) -> dict[str, IPv4Interface]:
    addresses = {}
    for command in commands:
        m = re.fullmatch(r"ip addr add (\S+) dev (eth\d+)", command)
        if m:
            addresses[m.group(2)] = IPv4Interface(m.group(1))
    return addresses


def validate(root: Path) -> list[str]:
    """Return issues instead of silently accepting miswired network configurations."""
    errors: list[str] = []
    try:
        topology = yaml.safe_load((root / "campus.clab.yml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        return [f"Cannot parse campus.clab.yml: {exc}"]
    if not isinstance(topology, dict):
        return ["Topology must be a YAML mapping"]
    if topology.get("name") != "campus-net-resilience":
        errors.append("Unexpected lab name")
    topo = topology.get("topology") or {}
    if not isinstance(topo, dict):
        return ["Missing topology mapping"]
    nodes = topo.get("nodes") or {}
    groups = topo.get("groups") or {}
    if not isinstance(nodes, dict):
        return ["Missing node mapping"]
    if set(nodes) != EXPECTED_NODES:
        errors.append(f"Expected nodes {sorted(EXPECTED_NODES)}; got {sorted(nodes)}")
    if (groups.get("routers") or {}).get("kind") != "frr":
        errors.append("Routers must use native FRR kind")
    if (groups.get("routers") or {}).get("daemons") != ["ospfd"]:
        errors.append("This lab should enable only ospfd in the router group")
    links = topo.get("links") or []
    actual_links: set[frozenset[str]] = set()
    seen_endpoints: set[str] = set()
    for index, link in enumerate(links):
        endpoints = link.get("endpoints") if isinstance(link, dict) else None
        if not isinstance(endpoints, list) or len(endpoints) != 2:
            errors.append(f"Invalid endpoints at link {index}")
            continue
        for endpoint in endpoints:
            if endpoint in seen_endpoints:
                errors.append(f"Repeated endpoint {endpoint}")
            seen_endpoints.add(endpoint)
            if ":eth0" in endpoint:
                errors.append("eth0 is reserved for management")
        actual_links.add(frozenset(endpoints))
    if actual_links != EXPECTED_LINKS:
        errors.append("Unexpected or missing network links")

    interfaces: dict[str, dict[str, IPv4Interface]] = {}
    router_ids: set[str] = set()
    for node in EXPECTED_NODES.intersection(nodes):
        definition = nodes[node]
        if node in {"r1", "r2", "r3"}:
            expected_cfg = f"configs/{node}.frr.conf"
            if definition.get("startup-config") != expected_cfg:
                errors.append(f"{node} must use {expected_cfg}")
            try:
                conf = (root / expected_cfg).read_text(encoding="utf-8")
                interfaces[node] = _router_interfaces(conf)
            except (OSError, ValueError) as exc:
                errors.append(f"Invalid FRR config for {node}: {exc}")
                continue
            match = re.search(r"^ ospf router-id (\S+)$", conf, flags=re.MULTILINE)
            if not match or match.group(1) in router_ids:
                errors.append(f"Missing or repeated OSPF router-id for {node}")
            else:
                router_ids.add(match.group(1))
            advertised = set(re.findall(r"^ network (\S+) area 0\.0\.0\.0$", conf, re.MULTILINE))
            for ip in interfaces[node].values():
                if str(ip.network) not in advertised:
                    errors.append(f"{node}: {ip.network} is not advertised in OSPF")
            if node in {"r1", "r3"} and " passive-interface eth3" not in conf:
                errors.append(f"{node}: host-facing port must be OSPF passive")
        else:
            interfaces[node] = _host_interfaces(definition.get("exec", []))
    for link in EXPECTED_LINKS:
        a, b = sorted(link)
        a_node, a_if = a.split(":")
        b_node, b_if = b.split(":")
        try:
            first = interfaces[a_node][a_if]
            second = interfaces[b_node][b_if]
            if first.network != second.network:
                errors.append(f"Subnet mismatch: {a} and {b}")
            if first.ip == second.ip:
                errors.append(f"Duplicate IPv4 address: {a} and {b}")
        except KeyError:
            errors.append(f"Missing IP assignment for link {a} <-> {b}")
    expected = {
        "r1": {"eth1": "10.0.12.1/30", "eth2": "10.0.13.1/30", "eth3": "10.20.10.1/24"},
        "r2": {"eth1": "10.0.12.2/30", "eth2": "10.0.23.1/30"},
        "r3": {"eth1": "10.0.23.2/30", "eth2": "10.0.13.2/30", "eth3": "10.20.30.1/24"},
        "client": {"eth1": "10.20.10.10/24"},
        "server": {"eth1": "10.20.30.10/24"},
    }
    for node, expected_ips in expected.items():
        if node in interfaces:
            actual_ips = {key: str(value) for key, value in interfaces[node].items()}
            if actual_ips != expected_ips:
                errors.append(f"Unexpected interface addresses on {node}")
    if len(router_ids) != 3:
        errors.append("Three unique OSPF router IDs are required")
    return errors
