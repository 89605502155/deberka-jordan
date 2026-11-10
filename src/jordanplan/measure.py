"""Finite atomic signed measures and their Hahn and Jordan decompositions.

A reallocation cycle among consumers that share one pool (memory of a host,
CPU quota, bandwidth, money) is a signed measure on the finite set
``X = {pool, consumer_1, ..., consumer_N}``. Every atom carries the change of
the share of that element, and the pool atom closes the balance so that
``nu(X) = 0``.

Reference for the theory: P. R. Halmos, *Measure Theory*, §28 (signed
measures) and §29 (Hahn and Jordan decompositions).
"""

from __future__ import annotations

from collections.abc import Hashable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Generic, TypeVar

K = TypeVar("K", bound=Hashable)

POOL = "pool"
"""Default name of the pool atom (free capacity of the shared resource)."""


class SignedMeasure(Mapping[K, float], Generic[K]):
    """Signed measure concentrated on finitely many atoms.

    The measure is stored as a mapping ``atom -> nu({atom})``. Atoms whose
    absolute mass does not exceed ``tol`` are dropped. The measure of a set is
    ``nu(A) = sum(nu({a}) for a in A)``.

    >>> nu = SignedMeasure({"a": 3.0, "b": -1.0, "c": -2.0})
    >>> nu.total(), nu.total_variation()
    (0.0, 6.0)
    >>> sorted(nu.hahn().positive), sorted(nu.hahn().negative)
    (['a'], ['b', 'c'])
    """

    __slots__ = ("_atoms",)

    def __init__(self, atoms: Mapping[K, float] | Iterable[tuple[K, float]] = (),
                 *, tol: float = 0.0) -> None:
        items = atoms.items() if isinstance(atoms, Mapping) else atoms
        acc: dict[K, float] = {}
        for key, value in items:
            acc[key] = acc.get(key, 0.0) + float(value)
        self._atoms = {k: v for k, v in acc.items() if abs(v) > tol}

    # Mapping protocol -------------------------------------------------
    def __getitem__(self, key: K) -> float:
        return self._atoms[key]

    def __iter__(self) -> Iterator[K]:
        return iter(self._atoms)

    def __len__(self) -> int:
        return len(self._atoms)

    def __repr__(self) -> str:
        return f"SignedMeasure({self._atoms!r})"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, SignedMeasure):
            return self._atoms == other._atoms
        return NotImplemented

    __hash__ = None  # type: ignore[assignment]

    # Construction ------------------------------------------------------
    @classmethod
    def from_allocations(cls, current: Mapping[K, float], target: Mapping[K, float],
                         *, pool: K | None = None, tol: float = 0.0) -> SignedMeasure[K]:
        """Measure of the cycle ``current -> target``.

        ``nu({i}) = target[i] - current[i]``. Consumers missing from ``target``
        keep their share. If ``pool`` is given, the pool atom
        ``nu({pool}) = -sum(nu({i}))`` is added, so the result has total zero.
        """
        atoms: dict[K, float] = {k: target.get(k, v) - v for k, v in current.items()}
        for k, v in target.items():
            if k not in current:
                atoms[k] = float(v)
        if pool is not None:
            if pool in atoms:
                raise ValueError(f"pool atom {pool!r} clashes with a consumer name")
            atoms[pool] = -sum(atoms.values())
        return cls(atoms, tol=tol)

    @classmethod
    def from_transfers(cls, transfers: Iterable[tuple[K, K, float]],
                       *, tol: float = 1e-9) -> SignedMeasure[K]:
        """Net effect of transfers ``(source, recipient, amount)``.

        This is the *netting* of a cycle: all proposals are summed per atom.
        """
        atoms: dict[K, float] = {}
        for source, recipient, amount in transfers:
            atoms[source] = atoms.get(source, 0.0) - float(amount)
            atoms[recipient] = atoms.get(recipient, 0.0) + float(amount)
        return cls(atoms, tol=tol)

    # Measure of sets ---------------------------------------------------
    def __call__(self, subset: Iterable[K]) -> float:
        """``nu(A)`` for a set of atoms ``A``. Unknown atoms carry zero mass."""
        return sum(self._atoms.get(k, 0.0) for k in set(subset))

    def total(self) -> float:
        """``nu(X)``: mass of the whole space."""
        return sum(self._atoms.values())

    def total_variation(self) -> float:
        """``|nu|(X) = nu+(X) + nu-(X)``."""
        return sum(abs(v) for v in self._atoms.values())

    def restrict(self, subset: Iterable[K]) -> SignedMeasure[K]:
        """Restriction ``nu(. ∩ A)``."""
        keep = set(subset)
        return SignedMeasure({k: v for k, v in self._atoms.items() if k in keep})

    def without(self, *atoms: K) -> SignedMeasure[K]:
        """Restriction to the complement of the given atoms."""
        drop = set(atoms)
        return SignedMeasure({k: v for k, v in self._atoms.items() if k not in drop})

    # Algebra -----------------------------------------------------------
    def __add__(self, other: SignedMeasure[K]) -> SignedMeasure[K]:
        return SignedMeasure([*self._atoms.items(), *other.items()])

    def __neg__(self) -> SignedMeasure[K]:
        return SignedMeasure({k: -v for k, v in self._atoms.items()})

    def __sub__(self, other: SignedMeasure[K]) -> SignedMeasure[K]:
        return self + (-other)

    def __mul__(self, c: float) -> SignedMeasure[K]:
        return SignedMeasure({k: v * c for k, v in self._atoms.items()})

    __rmul__ = __mul__

    # Decompositions ----------------------------------------------------
    def hahn(self) -> HahnDecomposition[K]:
        """Hahn decomposition: ``X = A + B`` (disjoint) with ``nu >= 0`` on A and ``<= 0`` on B.

        For an atomic measure it is unique up to null atoms, which are not
        stored and therefore belong to neither part.
        """
        pos = frozenset(k for k, v in self._atoms.items() if v > 0.0)
        neg = frozenset(k for k, v in self._atoms.items() if v < 0.0)
        return HahnDecomposition(pos, neg)

    def jordan(self) -> JordanDecomposition[K]:
        """Jordan decomposition ``nu = nu+ - nu-`` with mutually singular parts."""
        plus = {k: v for k, v in self._atoms.items() if v > 0.0}
        minus = {k: -v for k, v in self._atoms.items() if v < 0.0}
        return JordanDecomposition(SignedMeasure(plus), SignedMeasure(minus))


@dataclass(frozen=True, slots=True)
class HahnDecomposition(Generic[K]):
    """Positive set (recipients) and negative set (donors)."""

    positive: frozenset[K]
    negative: frozenset[K]


@dataclass(frozen=True, slots=True)
class JordanDecomposition(Generic[K]):
    """Non-negative parts ``plus`` and ``minus`` with ``nu = plus - minus``."""

    plus: SignedMeasure[K]
    minus: SignedMeasure[K]

    @property
    def variation(self) -> SignedMeasure[K]:
        """``|nu| = nu+ + nu-``."""
        return self.plus + self.minus
