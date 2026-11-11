"""The volume factor: units per byte moved between two consumers (default 1: bytes).

Factor 2 gives the balloon operations: a byte moved between consumers is one
deflation and one inflation.
"""

import json

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from deberka_jordan import (
    POOL,
    jordan_plan,
    net_transfers,
    netting_by_cycle,
    netting_report,
    plan_volume,
    sequential_volume,
)
from deberka_jordan.cli import main

names = st.sampled_from(["a", "b", "c", "d", "e"])
amounts = st.floats(0.0, 1e4, allow_nan=False)
transfers = st.lists(st.tuples(names, names, amounts), max_size=10)
shares = st.dictionaries(names, st.floats(0.0, 1e5, allow_nan=False), min_size=1)

RING = [("vm1", "vm2", 300.0), ("vm2", "vm3", 300.0), ("vm3", "vm1", 100.0)]


# Default reproduces the numbers of the previous version ----------------------


def test_default_sequential_volume_is_the_bytes_transferred():
    ts = [("a", "b", 100.0), ("b", "c", 50.0)]
    assert sequential_volume(ts) == 150.0
    assert sequential_volume(ts) == sequential_volume(ts, factor=1.0)


def test_factor_two_is_the_balloon_operations():
    ts = [("a", "b", 100.0), ("b", "c", 50.0)]
    assert sequential_volume(ts, factor=2.0) == 2.0 * 150.0


def test_default_netting_is_in_bytes():
    report = netting_report(RING)
    assert report.sequential_volume == 700.0
    assert report.jordan_volume == 200.0
    assert report.ratio == pytest.approx(200.0 / 700.0)
    assert netting_report(RING, factor=2.0).sequential_volume == 1400.0
    assert netting_report(RING, factor=2.0).jordan_volume == 400.0


def test_plan_volume_default_is_plan_volume_property():
    cur = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}
    new = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
    p = jordan_plan(cur, new, pool_free=100.0)
    assert plan_volume(p) == p.volume
    assert plan_volume(p, factor=1.0) == p.volume
    assert plan_volume(p, factor=2.0) == p.operations


# Factor 1 counts each transferred byte once ---------------------------------


def test_factor_one_counts_each_byte_once():
    assert sequential_volume(RING, factor=1.0) == 700.0
    assert netting_report(RING, factor=1.0).sequential_volume == 700.0
    assert netting_report(RING, factor=1.0).jordan_volume == 200.0


def test_plan_volume_is_linear_in_the_factor():
    cur = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}
    new = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
    p = jordan_plan(cur, new, pool_free=100.0)
    assert plan_volume(p, factor=2.0) == pytest.approx(p.operations)
    assert plan_volume(p, factor=3.0) == pytest.approx(1.5 * p.operations)


@given(transfers, st.floats(0.1, 10.0))
def test_jordan_volume_is_factor_times_bytes_moved(ts, factor):
    # the net plan of a closed set of transfers moves sum of its positive parts
    nu = net_transfers(ts)
    moved = sum(x for c, x in nu.items() if c != POOL and x > 0.0)
    report = netting_report(ts, factor=factor)
    assert report.jordan_volume == pytest.approx(factor * moved, abs=1e-6)
    assert report.sequential_volume == pytest.approx(factor * sum(a for _, _, a in ts))


@given(transfers, st.floats(0.1, 10.0))
def test_gain_does_not_depend_on_the_factor(ts, factor):
    # amounts so small that factor * amount underflows make the sequential volume 0,
    # where the ratio is defined as 1; that is float underflow, not the gain
    assume(sum(a for _, _, a in ts) > 1e-200)
    base = netting_report(ts)
    scaled = netting_report(ts, factor=factor)
    assert scaled.ratio == pytest.approx(base.ratio, abs=1e-9)
    assert scaled.gain == pytest.approx(base.gain, abs=1e-9)


@given(transfers)
def test_factor_one_is_never_above_factor_two_for_jordan(ts):
    assert netting_report(ts).jordan_volume <= netting_report(ts, factor=2.0).jordan_volume + 1e-9


@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.floats(0.1, 10.0))
def test_plan_volume_scales_with_factor(cur, pool, factor):
    new = {c: max(0.0, a * 0.7 + 300.0) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool)
    assert plan_volume(p, factor=factor) == pytest.approx(factor / 2.0 * p.operations)


# Netting by cycle -----------------------------------------------------------


def test_netting_by_cycle_takes_the_factor():
    log = [(1, "a", "b", 100.0), (1, "b", "c", 100.0), (2, "a", "b", 50.0), (2, "b", "a", 50.0)]
    rows = {r.cycle: r for r in netting_by_cycle(log)}
    assert rows[1].sequential_volume == 200.0
    assert rows[1].jordan_volume == 100.0
    assert rows[2].jordan_volume == 0.0
    balloon = {r.cycle: r for r in netting_by_cycle(log, factor=2.0)}
    assert balloon[1].sequential_volume == 400.0
    assert balloon[1].ratio == rows[1].ratio


# Validation -----------------------------------------------------------------


@pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
def test_factor_must_be_finite_and_positive(bad):
    with pytest.raises(ValueError):
        sequential_volume(RING, factor=bad)
    with pytest.raises(ValueError):
        netting_report(RING, factor=bad)
    with pytest.raises(ValueError):
        netting_by_cycle([(1, "a", "b", 1.0)], factor=bad)
    p = jordan_plan({"a": 1.0, "b": 1.0}, {"a": 2.0, "b": 0.0}, 0.0)
    with pytest.raises(ValueError):
        plan_volume(p, factor=bad)


@pytest.mark.parametrize("bad", [True, "2", None, [2.0]])
def test_factor_must_be_a_number(bad):
    with pytest.raises(TypeError):
        sequential_volume(RING, factor=bad)
    with pytest.raises(TypeError):
        netting_report(RING, factor=bad)
    p = jordan_plan({"a": 1.0, "b": 1.0}, {"a": 2.0, "b": 0.0}, 0.0)
    with pytest.raises(TypeError):
        plan_volume(p, factor=bad)


# Command line ---------------------------------------------------------------


def test_cli_plan_factor(tmp_path, capsys):
    f = tmp_path / "state.csv"
    f.write_text("consumer,current,target\nvm1,2000,2600\nvm2,3000,2500\nvm3,1500,1530\n")
    assert main(["plan", str(f), "--pool", "100"]) == 0
    default = json.loads(capsys.readouterr().out)
    assert main(["plan", str(f), "--pool", "100", "--factor", "2"]) == 0
    balloon = json.loads(capsys.readouterr().out)
    assert balloon["volume"] == pytest.approx(2 * default["volume"])
    assert default["volume_factor"] == 1.0
    assert balloon["volume_factor"] == 2.0


def test_cli_net_factor(tmp_path, capsys):
    f = tmp_path / "log.csv"
    f.write_text("cycle,donor,recipient,amount_mib\n1,a,b,100\n1,b,c,100\n2,a,c,64\n")
    assert main(["net", str(f)]) == 0
    default = json.loads(capsys.readouterr().out)
    assert default["sequential_volume"] == 264.0
    assert default["volume_factor"] == 1.0
    assert main(["net", str(f), "--factor", "2"]) == 0
    balloon = json.loads(capsys.readouterr().out)
    assert balloon["sequential_volume"] == 2 * 264.0
    assert balloon["overall_gain"] == pytest.approx(default["overall_gain"])


@pytest.mark.parametrize("value", ["0", "-2", "nan", "inf", "two"])
def test_cli_rejects_bad_factor(tmp_path, value):
    f = tmp_path / "log.csv"
    f.write_text("cycle,donor,recipient,amount_mib\n1,a,b,100\n")
    with pytest.raises(SystemExit) as exc:
        main(["net", str(f), "--factor", value])
    assert exc.value.code == 2
