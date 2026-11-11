import math
import random

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from deberka_jordan import (
    choose_deadband,
    cycles_bound,
    deadband_sweep,
    jumps_of,
    kappa,
    replay_reserve,
    sampled_variation,
    window_stats,
)


def test_kappa_properties():
    assert kappa([100.0, 50.0]) == 0.0
    assert kappa([100.0, -100.0]) == pytest.approx(1.0)
    assert kappa([]) == 0.0
    w = window_stats([1, 2, 3, 4], [100, -100, 50, -50], 4.0, 10.0)
    assert (w.variation, w.net, w.kappa) == (300.0, 0.0, 1.0)
    assert window_stats([1, 2], [5.0, 5.0], 2.0, 0.5).variation == 5.0


@given(st.lists(st.floats(-1e3, 1e3, allow_nan=False), max_size=30))
def test_kappa_in_unit_interval(xs):
    assert 0.0 <= kappa(xs) <= 1.0 + 1e-12


def _random_walk(n: int, seed: int) -> list[float]:
    rng = random.Random(seed)
    x, out = 2000.0, []
    for _ in range(n):
        x = max(100.0, x + rng.gauss(0.0, 40.0) + (300.0 if rng.random() < 0.01 else 0.0))
        out.append(x)
    return out


@settings(max_examples=40, deadline=None)
@given(st.integers(0, 10_000), st.floats(1.0, 300.0), st.integers(1, 5))
def test_claim3_bounds(seed, h, stride):
    demand = {f"vm{i}": _random_walk(400, seed + i) for i in range(3)}
    r = replay_reserve(demand, 1.0, reserve=max(h, 256.0), deadband=h, interval=stride)
    for c in demand:
        ts, xs = jumps_of(r.jumps, c)
        obs = demand[c][::stride]
        assert len(ts) <= cycles_bound(obs, h) + 1e-9
        assert sum(abs(x) for x in xs) <= sampled_variation(obs) + 1e-6
    assert len(r.jumps) <= r.bound + 1e-9
    assert r.volume <= r.observed_variation + 1e-6


def test_sweep_monotone_and_choice():
    demand = {f"vm{i}": _random_walk(2000, 7 + i) for i in range(4)}
    res = deadband_sweep(demand, 1.0, [0, 16, 64, 256], reserve=256.0, interval=2.0)
    assert math.isinf(res[0].bound)
    assert [r.cycles for r in res] == sorted((r.cycles for r in res), reverse=True)
    assert res[-1].volume < res[0].volume
    assert res[0].kappa_median > res[-1].kappa_median
    h = choose_deadband(res, 0.5)
    assert h is not None
    assert h > 0
    assert choose_deadband([{"h": 0, "kappa_median": 0.9}], 0.5) is None


def test_replay_validation():
    with pytest.raises(ValueError):
        replay_reserve({"a": [1.0], "b": [1.0, 2.0]}, 1.0, reserve=1.0, deadband=0.0)
    with pytest.raises(ValueError):
        replay_reserve({}, 1.0, reserve=1.0, deadband=0.0)
    with pytest.raises(ValueError):
        replay_reserve({"a": [1.0]}, 0.0, reserve=1.0, deadband=0.0)
