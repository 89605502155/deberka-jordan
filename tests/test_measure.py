import pytest
from hypothesis import given
from hypothesis import strategies as st

from deberka_jordan import POOL, SignedMeasure

atoms = st.dictionaries(
    st.sampled_from("abcdefgh"), st.floats(-1e4, 1e4, allow_nan=False), max_size=8
)


def test_from_allocations_closes_with_pool():
    nu = SignedMeasure.from_allocations({"a": 10.0, "b": 5.0}, {"a": 7.0, "b": 9.0}, pool=POOL)
    assert dict(nu) == {"a": -3.0, "b": 4.0, POOL: -1.0}
    assert nu.total() == 0.0


def test_pool_name_clash():
    with pytest.raises(ValueError):
        SignedMeasure.from_allocations({POOL: 1.0}, {POOL: 2.0}, pool=POOL)


def test_from_transfers_nets():
    nu = SignedMeasure.from_transfers([("a", "b", 5.0), ("b", "a", 5.0), ("a", "c", 2.0)])
    assert dict(nu) == {"a": -2.0, "c": 2.0}


def test_set_function_and_algebra():
    nu = SignedMeasure({"a": 2.0, "b": -3.0})
    assert nu({"a", "b", "z"}) == -1.0
    assert dict(nu - nu) == {}
    assert dict(2 * nu) == {"a": 4.0, "b": -6.0}
    assert dict(nu.restrict({"a"})) == {"a": 2.0}
    assert dict(nu.without("a")) == {"b": -3.0}


@given(atoms)
def test_jordan_and_hahn_properties(d):
    nu = SignedMeasure(d)
    j = nu.jordan()
    h = nu.hahn()
    # nu = nu+ - nu-, both parts non-negative and mutually singular
    assert dict(j.plus - j.minus) == pytest.approx(dict(nu))
    assert all(v > 0 for v in j.plus.values())
    assert all(v > 0 for v in j.minus.values())
    assert not set(j.plus) & set(j.minus)
    # Hahn sets carry the parts
    assert set(j.plus) == h.positive
    assert set(j.minus) == h.negative
    assert nu(h.positive) == pytest.approx(j.plus.total())
    assert nu(h.negative) == pytest.approx(-j.minus.total())
    # |nu|(X) = nu+(X) + nu-(X)
    assert nu.total_variation() == pytest.approx(j.variation.total())
