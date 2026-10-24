from pathlib import Path
from shutil import copytree

import pytest

from campus_net.validator import _host_interfaces, _router_interfaces, validate


def test_valid_repository(root):
    assert validate(root) == []


def test_router_parser():
    text = "interface eth1\n ip address 10.0.0.1/30\n!\ninterface eth2\n ip address 10.0.0.5/30\n!\n"
    assert set(_router_interfaces(text)) == {"eth1", "eth2"}


def test_router_duplicate_interface():
    with pytest.raises(ValueError, match="Repeated"):
        _router_interfaces("interface eth1\n ip address 10.0.0.1/30\n ip address 10.0.0.2/30\n!")


def test_host_parser():
    assert set(_host_interfaces(["ip addr add 10.20.10.10/24 dev eth1"])) == {"eth1"}


def copy_config(root: Path, tmp_path: Path) -> Path:
    copytree(root / "configs", tmp_path / "configs")
    (tmp_path / "campus.clab.yml").write_text((root / "campus.clab.yml").read_text())
    return tmp_path


def test_bad_yaml(root, tmp_path):
    (tmp_path / "campus.clab.yml").write_text("topology: [not, valid, :")
    assert "Cannot parse" in validate(tmp_path)[0]


def test_duplicate_ip_detected(root, tmp_path):
    target = copy_config(root, tmp_path) / "configs/r2.frr.conf"
    target.write_text(target.read_text().replace("10.0.12.2/30", "10.0.12.1/30"))
    assert any("Duplicate IPv4" in x or "Unexpected interface" in x for x in validate(tmp_path))


def test_wrong_subnet_detected(root, tmp_path):
    target = copy_config(root, tmp_path) / "configs/r2.frr.conf"
    target.write_text(target.read_text().replace("10.0.12.2/30", "10.0.99.2/30"))
    assert any("Subnet mismatch" in x for x in validate(tmp_path))


def test_ospf_missing_advertisement(root, tmp_path):
    target = copy_config(root, tmp_path) / "configs/r3.frr.conf"
    target.write_text(target.read_text().replace(" network 10.20.30.0/24 area 0.0.0.0", ""))
    assert any("is not advertised" in x for x in validate(tmp_path))


def test_passive_access_port(root, tmp_path):
    target = copy_config(root, tmp_path) / "configs/r1.frr.conf"
    target.write_text(target.read_text().replace(" passive-interface eth3", ""))
    assert any("host-facing" in x for x in validate(tmp_path))


def test_router_id_uniqueness(root, tmp_path):
    target = copy_config(root, tmp_path) / "configs/r2.frr.conf"
    target.write_text(target.read_text().replace("2.2.2.2", "1.1.1.1"))
    assert any("router-id" in x for x in validate(tmp_path))


def test_missing_config(root, tmp_path):
    copy_config(root, tmp_path)
    (tmp_path / "configs/r1.frr.conf").unlink()
    assert any("Invalid FRR config" in x for x in validate(tmp_path))


def test_duplicate_endpoint(root, tmp_path):
    copy_config(root, tmp_path)
    topo = tmp_path / "campus.clab.yml"
    topo.write_text(topo.read_text().replace('"r3:eth2"', '"r2:eth1"'))
    assert any("Repeated endpoint" in x for x in validate(tmp_path))


def test_bad_lab_name(root, tmp_path):
    copy_config(root, tmp_path)
    topo = tmp_path / "campus.clab.yml"
    topo.write_text(topo.read_text().replace("name: campus-net-resilience", "name: other"))
    assert "Unexpected lab name" in validate(tmp_path)
