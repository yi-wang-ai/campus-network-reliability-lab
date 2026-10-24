from campus_net.routes import full_neighbor_count, next_hops


def test_next_hops_frr():
    text = "O>* 10.20.30.0/24 [110/15] via 10.0.13.2, eth2, weight 1, 00:00:06"
    assert next_hops(text) == {"10.0.13.2"}


def test_multipath():
    assert next_hops("via 10.0.12.2 and via 10.0.13.2") == {"10.0.12.2", "10.0.13.2"}


def test_reject_invalid_address():
    assert next_hops("via 999.0.0.1 via 10.0.13.2") == {"10.0.13.2"}


def test_no_via():
    assert not next_hops("C>* 10.20.30.0/24 is directly connected, eth3")


def test_full_neighbors():
    neighbors = "Neighbor ID   Pri State\n2.2.2.2 1 Full/- 00:00:03\n3.3.3.3 1 Full/- 00:00:03"
    assert full_neighbor_count(neighbors) == 2


def test_partial_neighbors():
    assert full_neighbor_count("2.2.2.2 1 Init 00:00:03\n3.3.3.3 1 2-Way/DROther") == 0


def test_full_case_insensitive():
    assert full_neighbor_count("1.1.1.1 1 FULL/DR") == 1
