import random

import pytest
from hypothesis import given
from hypothesis import strategies as st

from jordanplan import (
    POOL,
    is_safe,
    jordan_plan,
    lower_bound_volume,
    min_pool,
    net_transfers,
    netting_by_cycle,
    pairwise,
    pool_trajectory,
    ration,
    recipients_first,
    sequential_volume,
    shuffled,
    two_phase,
)

CUR = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}
NEW = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}

names = st.sampled_from(["a", "b", "c", "d", "e", "f"])
amounts = st.floats(0.0, 1e4, allow_nan=False)
transfers = st.lists(st.tuples(names, names, amounts), max_size=12)
shares = st.dictionaries(names, st.floats(0.0, 1e5, allow_nan=False), min_size=1)


def test_plan_matches_measure():
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    assert set(p.donors) == {"vm2", "vm4"}
    assert set(p.recipients) == {"vm1", "vm3"}
    nu = p.measure()
    assert nu.total() == pytest.approx(0.0)
    assert nu[POOL] == pytest.approx(p.pool_change)
    assert p.volume == pytest.approx(lower_bound_volume(nu))
    assert p.targets(CUR) == pytest.approx(NEW)


def test_deadband_force_and_bounds():
    p = jordan_plan(CUR, NEW, 100.0, deadband=64.0)
    assert "vm3" not in p.recipients and p.skipped == {"vm3": 30.0}
    p = jordan_plan(CUR, NEW, 100.0, deadband=64.0, force={"vm3"})
    assert p.recipients["vm3"] == pytest.approx(30.0)
    p = jordan_plan(CUR, NEW, 100.0, floor={"vm2": 2900.0}, ceiling={"vm1": 2100.0})
    assert p.donors["vm2"] == pytest.approx(100.0)
    assert p.recipients["vm1"] == pytest.approx(100.0)


def test_invalid_arguments():
    with pytest.raises(ValueError):
        jordan_plan(CUR, NEW, -1.0)
    with pytest.raises(ValueError):
        jordan_plan(CUR, NEW, 0.0, deadband=-1.0)


def test_rationing():
    got = ration({"a": 300.0, "b": 300.0, "c": 300.0}, 500.0,
                 priority={"a": 50, "b": -10, "c": 5})
    assert got == {"b": 300.0, "c": 200.0}
    prop = ration({"a": 300.0, "b": 100.0}, 200.0)
    assert prop == pytest.approx({"a": 150.0, "b": 50.0})
    assert ration({"a": 1.0}, 0.0) == {}


def test_plan_rations_when_pool_is_short():
    p = jordan_plan({"a": 100.0, "b": 100.0}, {"a": 300.0, "b": 50.0}, pool_free=10.0)
    assert p.rationed
    assert p.give == pytest.approx(60.0)
    assert p.pool_after == pytest.approx(0.0)


# Claim 1 --------------------------------------------------------------------

@given(transfers)
def test_claim1_netting_never_exceeds_sequential(ts):
    assert lower_bound_volume(net_transfers(ts)) <= sequential_volume(ts) + 1e-6


@given(transfers)
def test_claim1_any_execution_is_at_least_the_bound(ts):
    # executing the proposals one by one is one particular sequence of operations;
    # its per-consumer volume is never below |net change|
    ops = pairwise(ts)
    per: dict[str, float] = {}
    for c, d in ops:
        per[c] = per.get(c, 0.0) + abs(d)
    nu = net_transfers(ts)
    for c, x in nu.items():
        assert per[c] >= abs(x) - 1e-6


def test_netting_by_cycle():
    log = [(1, "a", "b", 100.0), (1, "b", "c", 100.0),   # b is a transit node
           (2, "a", "b", 50.0), (2, "b", "a", 50.0),     # opposite proposals
           (3, "a", "c", 64.0)]
    rows = {r.cycle: r for r in netting_by_cycle(log)}
    assert rows[1].sequential_volume == 400.0 and rows[1].jordan_volume == 200.0
    assert rows[1].gain == pytest.approx(0.5)
    assert rows[2].jordan_volume == 0.0 and rows[2].ratio == 0.0
    assert rows[3].ratio == 1.0


# Claim 2 --------------------------------------------------------------------

@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.randoms(use_true_random=False),
       st.floats(0.0, 500.0))
def test_claim2_two_phase_never_overdraws(cur, pool, rnd, h):
    new = {c: max(0.0, a + rnd.uniform(-5e3, 5e3)) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool, deadband=h)
    traj = pool_trajectory(two_phase(p), pool)
    assert min(traj) >= -1e-6
    assert max(traj) == pytest.approx(p.peak, abs=1e-6)
    assert traj[-1] == pytest.approx(p.pool_after, abs=1e-6)


def test_other_orders_can_overdraw():
    p = jordan_plan(CUR, {"vm1": 2800.0, "vm2": 2200.0}, pool_free=100.0)
    assert not is_safe(recipients_first(p), 100.0)
    assert is_safe(two_phase(p), 100.0)
    bad = sum(min_pool(shuffled(p, random.Random(s)), 100.0) < 0 for s in range(50))
    assert 0 < bad < 50
    assert is_safe(pairwise([("vm2", "vm1", 800.0)]), 0.0)
