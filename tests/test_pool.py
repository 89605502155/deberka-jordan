"""Pool modes of the plan volume: ``pool="max"`` (default) and ``pool="weighted"``.

``max`` counts a byte moved into or out of the pool as one byte, the same as a
byte between consumers: ``factor * max(take, give)``. ``weighted`` counts it
``pool_weight`` times: ``factor * (min(take, give) + pool_weight * |pool change|)``.
With ``pool_weight = 0.5`` this is the earlier volume ``factor / 2 * operations``;
with ``pool_weight = 1`` it coincides with ``max``.
"""

import json
import math

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

from deberka_jordan import POOL, jordan_plan, plan_volume
from deberka_jordan.cli import main
from deberka_jordan.plan import POOL_MODES

CUR = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}
NEW = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}  # changes the pool

names = st.sampled_from(["a", "b", "c", "d", "e", "f"])
amounts = st.floats(0.0, 1e5, allow_nan=False, allow_infinity=False)
shares = st.dictionaries(names, amounts, min_size=2, max_size=6)
weights = st.floats(0.0, 10.0, allow_nan=False, allow_infinity=False)


def _pool_free_plan(cur: dict[str, float], deltas: list[float]):
    """Plan of a cycle that moves shares between consumers only (sum unchanged)."""
    keys = sorted(cur)
    d = [deltas[i % len(deltas)] for i in range(len(keys))]
    mean = sum(d) / len(d)
    target = {k: max(0.0, cur[k] + (x - mean)) for k, x in zip(keys, d, strict=True)}
    # project back so the total is unchanged after clipping at zero
    gap = sum(cur.values()) - sum(target.values())
    if gap != 0.0 and target:
        big = max(target, key=target.get)
        target[big] += gap
    return jordan_plan(cur, target, pool_free=0.0)


# Default mode -----------------------------------------------------------------


def test_default_mode_is_max():
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    assert p.pool_change != 0.0
    assert plan_volume(p) == max(p.take, p.give)
    assert p.volume == plan_volume(p, pool="max")


def test_max_counts_pool_bytes_fully():
    # take 0, give 150: the pool gives 150 bytes to the recipients
    p = jordan_plan({"a": 10.0, "b": 10.0}, {"a": 40.0, "b": 10.0}, pool_free=100.0)
    assert (p.take, p.give) == (0.0, 30.0)
    assert plan_volume(p) == 30.0
    assert plan_volume(p, pool="weighted") == 15.0  # half, the balloon-operation count
    assert plan_volume(p, pool="weighted", pool_weight=1.0) == 30.0


def test_max_is_bytes_moved_on_the_closed_measure():
    # netting counts the pool atom with weight one per byte: (1/2) sum |nu| over all
    # atoms of the closed measure (consumers and pool) equals the max mode
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    closed = p.measure(POOL)
    assert plan_volume(p) == pytest.approx(0.5 * sum(abs(x) for x in closed.values()))


# Weighted mode reproduces the earlier numbers ----------------------------------


def test_weighted_half_is_the_balloon_operations_over_two():
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    assert plan_volume(p, pool="weighted") == pytest.approx(p.operations / 2)
    assert plan_volume(p, pool="weighted", factor=2.0) == pytest.approx(p.operations)
    assert plan_volume(p, pool="weighted", pool_weight=0.5) == plan_volume(p, pool="weighted")


@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.integers(0, 10**6))
def test_weighted_default_weight_is_operations_over_two(cur, pool_free, seed):
    new = {c: max(0.0, a * (0.6 + (seed % 7) * 0.1) + 200.0) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool_free)
    assert plan_volume(p, pool="weighted") == pytest.approx(p.operations / 2, abs=1e-6)


# Modes coincide for pool-free plans --------------------------------------------


@pytest.mark.parametrize(
    ("cur", "new"),
    [
        ({"a": 100.0, "b": 50.0, "c": 20.0}, {"a": 80.0, "b": 90.0, "c": 0.0}),
        ({"a": 10.0, "b": 10.0}, {"a": 20.0, "b": 0.0}),
        ({"x": 1.0, "y": 2.0, "z": 3.0, "w": 4.0}, {"x": 4.0, "y": 3.0, "z": 2.0, "w": 1.0}),
    ],
)
def test_all_modes_coincide_without_pool_change(cur, new):
    p = jordan_plan(cur, new, pool_free=0.0)
    assert p.pool_change == pytest.approx(0.0, abs=1e-9)
    values = [
        plan_volume(p),
        plan_volume(p, pool="weighted"),
        plan_volume(p, pool="weighted", pool_weight=1.0),
        plan_volume(p, pool="weighted", pool_weight=0.0),
        plan_volume(p, pool="weighted", pool_weight=7.3),
    ]
    for v in values:
        assert v == pytest.approx(values[0], abs=1e-9)
    assert values[0] == pytest.approx(p.operations / 2)


@given(shares, st.lists(st.floats(-1e3, 1e3, allow_nan=False), min_size=1, max_size=6), weights)
def test_all_modes_coincide_for_random_pool_free_cycles(cur, deltas, w):
    p = _pool_free_plan(cur, deltas)
    assume(abs(p.pool_change) <= 1e-6)  # clipping at zero may leave a gap
    base = plan_volume(p)
    assert plan_volume(p, pool="weighted", pool_weight=w) == pytest.approx(base, abs=1e-6)
    assert plan_volume(p, pool="weighted") == pytest.approx(base, abs=1e-6)


# Relations between the modes ---------------------------------------------------


@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.integers(0, 10**6))
def test_weight_one_is_max(cur, pool_free, seed):
    new = {c: max(0.0, a * (0.5 + (seed % 9) * 0.1) + 150.0) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool_free)
    assert plan_volume(p, pool="weighted", pool_weight=1.0) == pytest.approx(plan_volume(p))


@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.integers(0, 10**6), weights, weights)
def test_volume_is_nondecreasing_in_pool_weight(cur, pool_free, seed, w1, w2):
    new = {c: max(0.0, a * (0.5 + (seed % 9) * 0.1) + 150.0) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool_free)
    lo, hi = sorted((w1, w2))
    assert (
        plan_volume(p, pool="weighted", pool_weight=lo)
        <= plan_volume(p, pool="weighted", pool_weight=hi) + 1e-9
    )


@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.integers(0, 10**6))
def test_max_dominates_the_balloon_half(cur, pool_free, seed):
    new = {c: max(0.0, a * (0.5 + (seed % 9) * 0.1) + 150.0) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool_free)
    assert plan_volume(p) >= p.operations / 2 - 1e-9
    assert plan_volume(p) >= abs(p.pool_change) - 1e-9
    assert plan_volume(p) >= min(p.take, p.give) - 1e-9


@given(shares, st.floats(0.0, 1e4, allow_nan=False), st.integers(0, 10**6))
def test_factor_scales_every_mode(cur, pool_free, seed):
    new = {c: max(0.0, a * (0.5 + (seed % 9) * 0.1) + 150.0) for c, a in cur.items()}
    p = jordan_plan(cur, new, pool_free)
    for mode in POOL_MODES:
        one = plan_volume(p, pool=mode)
        assert plan_volume(p, factor=2.0, pool=mode) == pytest.approx(2.0 * one)


# Validation ----------------------------------------------------------------------


@pytest.mark.parametrize("bad", [True, "0.5", None, [0.5]])
def test_pool_weight_must_be_a_number(bad):
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    with pytest.raises(TypeError):
        plan_volume(p, pool="weighted", pool_weight=bad)


@pytest.mark.parametrize("bad", [-0.1, -1.0, math.nan, math.inf, -math.inf])
def test_pool_weight_must_be_finite_and_non_negative(bad):
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    with pytest.raises(ValueError):
        plan_volume(p, pool="weighted", pool_weight=bad)
    # validated also in the mode that does not use it
    with pytest.raises(ValueError):
        plan_volume(p, pool="max", pool_weight=bad)


@pytest.mark.parametrize("zero", [0.0, 1e-12])
def test_pool_weight_zero_is_allowed(zero):
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    assert plan_volume(p, pool="weighted", pool_weight=zero) == pytest.approx(
        min(p.take, p.give), abs=1e-6
    )


@pytest.mark.parametrize("bad", [None, 1, 0.5, ["max"]])
def test_pool_must_be_a_string(bad):
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    with pytest.raises(TypeError):
        plan_volume(p, pool=bad)


@pytest.mark.parametrize("bad", ["sum", "MAX", "", "weight"])
def test_pool_must_be_a_known_mode(bad):
    p = jordan_plan(CUR, NEW, pool_free=100.0)
    with pytest.raises(ValueError):
        plan_volume(p, pool=bad)


def test_pool_modes_are_documented_values():
    assert POOL_MODES == ("max", "weighted")
    assert POOL == "pool"


# Command line ----------------------------------------------------------------------


@pytest.fixture
def state_file(tmp_path):
    f = tmp_path / "state.csv"
    f.write_text("consumer,current,target\nvm1,2000,2600\nvm2,3000,2500\nvm3,1500,1530\n")
    return f


def test_cli_default_is_max(state_file, capsys):
    p = jordan_plan(
        {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0},
        {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0},
        100.0,
    )
    assert main(["plan", str(state_file), "--pool", "100"]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out["volume_pool_mode"] == "max"
    assert out["volume_pool_weight"] is None
    assert out["volume"] == pytest.approx(max(p.take, p.give))


def test_cli_weighted_half_matches_operations(state_file, capsys):
    assert main(["plan", str(state_file), "--pool", "100", "--pool-mode", "weighted"]) == 0
    weighted = json.loads(capsys.readouterr().out)
    assert weighted["volume_pool_weight"] == 0.5
    assert main(["plan", str(state_file), "--pool", "100"]) == 0
    default = json.loads(capsys.readouterr().out)
    assert weighted["volume"] <= default["volume"]
    assert weighted["volume"] == pytest.approx(
        plan_volume(
            jordan_plan(
                {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0},
                {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0},
                100.0,
            ),
            pool="weighted",
        )
    )


def test_cli_pool_weight_one_equals_max(state_file, capsys):
    assert (
        main(
            [
                "plan",
                str(state_file),
                "--pool",
                "100",
                "--pool-mode",
                "weighted",
                "--pool-weight",
                "1",
            ]
        )
        == 0
    )
    w1 = json.loads(capsys.readouterr().out)
    assert main(["plan", str(state_file), "--pool", "100"]) == 0
    default = json.loads(capsys.readouterr().out)
    assert w1["volume"] == pytest.approx(default["volume"])


@pytest.mark.parametrize("value", ["-1", "nan", "inf", "heavy"])
def test_cli_rejects_bad_pool_weight(state_file, value):
    with pytest.raises(SystemExit) as exc:
        main(["plan", str(state_file), "--pool", "100", "--pool-weight", value])
    assert exc.value.code == 2


def test_cli_rejects_unknown_pool_mode(state_file):
    with pytest.raises(SystemExit) as exc:
        main(["plan", str(state_file), "--pool", "100", "--pool-mode", "sum"])
    assert exc.value.code == 2
