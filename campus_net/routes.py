"""Parse a small, documented subset of FRR CLI output."""

import ipaddress
import re

_VIA_RE = re.compile(r"\bvia\s+((?:\d{1,3}\.){3}\d{1,3})\b")
_FULL_RE = re.compile(r"\bFull(?:/[-A-Za-z]+)?\b", re.IGNORECASE)


def next_hops(route_output: str) -> set[str]:
    """Extract valid IPv4 next hops from `show ip route PREFIX` output."""
    candidates = _VIA_RE.findall(route_output)
    results = set()
    for value in candidates:
        try:
            results.add(str(ipaddress.IPv4Address(value)))
        except ipaddress.AddressValueError:
            continue
    return results


def full_neighbor_count(output: str) -> int:
    """Count full OSPF neighbors in FRR's text neighbor table."""
    return sum(bool(_FULL_RE.search(line)) for line in output.splitlines())
