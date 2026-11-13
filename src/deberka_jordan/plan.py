"""The Jordan plan of a reallocation cycle and netting of transfer proposals.

Claim 1 (lower bound on volume). Any sequence of operations that moves the
shares from ``a`` to ``a'`` has volume at least ``W = sum |a'_i - a_i|`` over
consumers. The bound is attained when every consumer only gives or only
receives. The Jordan plan does exactly that: it nets all proposals of a cycle
per consumer and executes only the net change.
"""

from __future__ import annotations

import math
import numbers
from collections.abc import Hashable, Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Generic, NamedTuple, TypeVar

from .measure import POOL, SignedMeasure

K = TypeVar("K", bound=Hashable)


class Transfer(NamedTuple):
    """Proposal to move ``amount`` units from ``source`` to ``recipient``."""

    source: Hashable
    recipient: Hashable
    amount: float


@dataclass(frozen=True)
class Plan(Generic[K]):
    """Plan of one reallocation cycle.

    ``donors`` and ``recipients`` hold non-negative amounts: how much to take
    from and how much to give to each consumer (the parts ``nu-`` and ``nu+``
    of the Jordan decomposition restricted to consumers).
    """

    donors: dict[K, float]
    recipients: dict[K, float]
    pool_before: float
    rationed: bool = False
    skipped: dict[K, float] = field(default_factory=dict)
    """Changes suppressed by the dead band, ``consumer -> requested change``."""

    @property
    def take(self) -> float:
        """Total amount reclaimed from donors."""
        return sum(self.donors.values())

    @property
    def give(self) -> float:
        """Total amount granted to recipients."""
        return sum(self.recipients.values())

    @property
    def pool_change(self) -> float:
        """``nu({pool})``: change of free capacity after the cycle."""
        return self.take - self.give

    @property
    def pool_after(self) -> float:
        """Pool level after the cycle, MiB."""
        return self.pool_before + self.pool_change

    @property
    def operations(self) -> float:
        """Balloon operations ``sum |nu({i})|`` over consumers (Claim 1, factor 2).

        Each byte moved between two consumers is one inflation and one deflation,
        so this is ``plan_volume(plan, factor=2, pool="weighted", pool_weight=0.5)``.
        """
        return self.take + self.give

    @property
    def volume(self) -> float:
        """Bytes moved by the plan: ``plan_volume(plan)`` with the default pool mode.

        The default is ``pool="max"`` (article choice): ``max(take, give)``, that is
        the bytes moved between consumers plus the bytes moved into or out of the
        pool, each counted once. For a plan that leaves the pool unchanged this is
        ``operations / 2``. For a plan that changes the pool it is larger than
        ``operations / 2``; see :func:`plan_volume` for the other mode.
        """
        return plan_volume(self)

    @property
    def peak(self) -> float:
        """Highest pool level during two-phase execution (after phase 1)."""
        return self.pool_before + self.take

    @property
    def is_empty(self) -> bool:
        """True if the plan moves nothing."""
        return not self.donors and not self.recipients

    def measure(self, pool: Hashable | None = POOL) -> SignedMeasure[Hashable]:
        """Return the signed measure of the cycle, closed by the pool atom if given."""
        atoms: dict[Hashable, float] = dict(self.recipients.items())
        for k, v in self.donors.items():
            atoms[k] = atoms.get(k, 0.0) - v
        if pool is not None:
            atoms[pool] = -sum(atoms.values())
        return SignedMeasure(atoms)

    def targets(self, current: Mapping[K, float]) -> dict[K, float]:
        """Return the new shares of the consumers touched by the plan."""
        out = {k: current[k] - x for k, x in self.donors.items()}
        out.update({k: current[k] + x for k, x in self.recipients.items()})
        return out


def ration(
    demand: Mapping[K, float], budget: float, priority: Mapping[K, float] | None = None
) -> dict[K, float]:
    """Split an insufficient ``budget`` among recipients.

    Without ``priority`` the budget is split in proportion to demand. With
    ``priority`` (smaller value means more urgent, for example the current
    headroom of a consumer) the recipients are served in that order.
    """
    budget = max(float(budget), 0.0)
    if priority is None:
        total = sum(demand.values())
        k = min(budget / total, 1.0) if total > 0.0 else 0.0
        return {c: x * k for c, x in demand.items() if x * k > 0.0}
    out: dict[K, float] = {}
    for c in sorted(demand, key=lambda name: priority.get(name, 0.0)):
        give = min(demand[c], budget)
        if give > 0.0:
            out[c] = give
        budget -= give
    return out


def jordan_plan(
    current: Mapping[K, float],
    target: Mapping[K, float],
    pool_free: float,
    *,
    deadband: float = 0.0,
    force: Iterable[K] = (),
    floor: Mapping[K, float] | None = None,
    ceiling: Mapping[K, float] | None = None,
    priority: Mapping[K, float] | None = None,
) -> Plan[K]:
    """Build the plan of the cycle ``current -> target``.

    Steps: clip targets to ``[floor, ceiling]``, drop changes with
    ``|change| < deadband`` (unless the consumer is in ``force``), split the
    consumers by the Hahn decomposition, and ration recipients if donors plus
    the free pool cannot cover them.

    The returned plan never needs more than ``pool_free + take``, so its
    two-phase execution keeps the pool non-negative (Claim 2).
    """
    if pool_free < 0.0:
        msg = "pool_free must be non-negative"
        raise ValueError(msg)
    if deadband < 0.0:
        msg = "deadband must be non-negative"
        raise ValueError(msg)
    forced = set(force)
    floor = floor or {}
    ceiling = ceiling or {}
    nu: dict[K, float] = {}
    skipped: dict[K, float] = {}
    for c, a in current.items():
        t = target.get(c, a)
        t = max(t, floor.get(c, float("-inf")))
        t = min(t, ceiling.get(c, float("inf")))
        x = float(t - a)
        if x == 0.0:
            continue
        if abs(x) >= deadband or c in forced:
            nu[c] = x
        else:
            skipped[c] = x
    hahn = SignedMeasure(nu).jordan()
    plus, minus = dict(hahn.plus), dict(hahn.minus)
    budget = pool_free + sum(minus.values())
    rationed = False
    if sum(plus.values()) > budget:
        plus = ration(plus, budget, priority)
        rationed = True
    return Plan(minus, plus, float(pool_free), rationed, skipped)


# Netting -----------------------------------------------------------------


def net_transfers(transfers: Iterable[tuple[K, K, float]]) -> SignedMeasure[K]:
    """Net all transfer proposals of a cycle into one measure over consumers."""
    return SignedMeasure.from_transfers(transfers)


def _check_factor(factor: object) -> float:
    """Return the volume factor as a float, or raise.

    The factor is the number of units per byte moved between two consumers:
    1 for bytes (default), 2 for balloon operations. It must be a real number,
    finite and positive: a bool, a string
    or ``None`` raises ``TypeError``; zero, a negative or non-finite value
    raises ``ValueError``.
    """
    if isinstance(factor, bool) or not isinstance(factor, numbers.Real):
        msg = f"factor must be a real number, got {type(factor).__name__} {factor!r}"
        raise TypeError(msg)
    value = float(factor)
    if not math.isfinite(value) or value <= 0.0:
        msg = f"factor must be finite and positive, got {value!r}"
        raise ValueError(msg)
    return value


# Ways to count the bytes that a plan moves into or out of the pool.
POOL_MODES = ("max", "weighted")


def _check_pool_mode(pool: object) -> str:
    """Return the pool mode, or raise: a string from :data:`POOL_MODES`."""
    if not isinstance(pool, str):
        msg = f"pool must be a string, got {type(pool).__name__} {pool!r}"
        raise TypeError(msg)
    if pool not in POOL_MODES:
        msg = f"pool must be one of {POOL_MODES}, got {pool!r}"
        raise ValueError(msg)
    return pool


def _check_pool_weight(weight: object) -> float:
    """Return the pool weight as a float, or raise.

    The weight is the units counted per byte moved into or out of the pool,
    relative to one unit per byte moved between consumers. It must be a real
    number, finite and non-negative: a bool, a string or ``None`` raises
    ``TypeError``; a negative or non-finite value raises ``ValueError``.
    """
    if isinstance(weight, bool) or not isinstance(weight, numbers.Real):
        msg = f"pool_weight must be a real number, got {type(weight).__name__} {weight!r}"
        raise TypeError(msg)
    value = float(weight)
    if not math.isfinite(value) or value < 0.0:
        msg = f"pool_weight must be finite and non-negative, got {value!r}"
        raise ValueError(msg)
    return value


def plan_volume(
    plan: Plan[Any],
    *,
    factor: float = 1.0,
    pool: str = "max",
    pool_weight: float = 0.5,
) -> float:
    """Volume of a plan in units of ``factor`` per byte moved between consumers.

    With ``take = Σ donors``, ``give = Σ recipients`` and ``m = min(take, give)``
    (bytes moved between consumers) the volume is::

        factor * (m + w * |take - give|)

    where ``|take - give| = |pool_change|`` is the pool movement and ``w`` depends
    on ``pool``:

    * ``pool="max"`` (default, article choice): ``w = 1``. The volume is
      ``factor * max(take, give)``: every byte moved into or out of the pool counts
      as a byte, the same as a byte moved between consumers.
    * ``pool="weighted"``: ``w = pool_weight`` (default 0.5). With ``w = 0.5`` the
      volume is ``factor / 2 * plan.operations``, the value of earlier versions:
      a pool byte is one balloon operation, half a byte.

    A plan that leaves the pool unchanged (``take == give``) has the same volume in
    every mode: ``factor * take``. With ``factor=1`` the default is the bytes moved;
    ``factor=2`` gives balloon operations only in the ``"weighted"`` mode with
    ``pool_weight=0.5``. In the ``"max"`` mode a pool byte counts two balloon
    operations at ``factor=2`` (it is one operation physically), so use that
    combination knowingly. ``pool_weight`` is validated also when it is not used.

    Raises ``TypeError`` for a non-numeric ``factor`` or ``pool_weight``, a
    non-string ``pool``, and ``ValueError`` for a non-finite or non-positive
    ``factor``, a ``pool`` not in :data:`POOL_MODES`, or a negative or non-finite
    ``pool_weight``.
    """
    f = _check_factor(factor)
    mode = _check_pool_mode(pool)
    w = _check_pool_weight(pool_weight)
    weight = 1.0 if mode == "max" else w
    return f * (min(plan.take, plan.give) + weight * abs(plan.pool_change))


def sequential_volume(transfers: Iterable[tuple[K, K, float]], *, factor: float = 1.0) -> float:
    """Volume when every proposal is executed on its own: ``factor * sum amount``.

    The default ``factor=1`` gives the bytes transferred. Each transfer is also
    one balloon inflation at the donor and one deflation at the recipient, two
    balloon operations per byte: ``factor=2`` gives those operations.
    """
    value = _check_factor(factor)
    return value * sum(float(amount) for _, _, amount in transfers)


def lower_bound_volume(nu: Mapping[Any, float], pool: Hashable | None = POOL) -> float:
    """``W = sum |nu({i})|`` over consumers: balloon operations (factor 2).

    The pool atom is excluded. In bytes (the default unit) the bound is ``W / 2``.
    """
    return sum(abs(x) for c, x in nu.items() if c != pool)


@dataclass(frozen=True, slots=True)
class NettingReport:
    """Gain of netting for one cycle."""

    cycle: Hashable
    n_transfers: int
    sequential_volume: float
    jordan_volume: float

    @property
    def ratio(self) -> float:
        """``W / W_seq``; less than one means netting saves operations."""
        return self.jordan_volume / self.sequential_volume if self.sequential_volume else 1.0

    @property
    def gain(self) -> float:
        """``1 - W / W_seq``."""
        return 1.0 - self.ratio


def netting_report(
    transfers: Iterable[tuple[K, K, float]], cycle: Hashable = None, *, factor: float = 1.0
) -> NettingReport:
    """Netting gain for the transfers of one cycle.

    Both volumes are in units of ``factor`` per byte moved between consumers
    (default 1: bytes; 2: balloon operations, see :func:`sequential_volume`).
    The Jordan volume is ``(factor / 2) * sum |net change|``. The gain does not
    depend on ``factor``.
    """
    value = _check_factor(factor)
    ts = list(transfers)
    net = lower_bound_volume(net_transfers(ts), pool=None)
    return NettingReport(
        cycle,
        len(ts),
        sequential_volume(ts, factor=value),
        value / 2.0 * net,
    )


def netting_by_cycle(
    rows: Iterable[tuple[Hashable, K, K, float]], *, factor: float = 1.0
) -> list[NettingReport]:
    """Netting gain per cycle for a proposal log ``(cycle, source, recipient, amount)``."""
    value = _check_factor(factor)
    cycles: dict[Hashable, list[tuple[K, K, float]]] = {}
    for cycle, source, recipient, amount in rows:
        cycles.setdefault(cycle, []).append((source, recipient, float(amount)))
    return [netting_report(ts, cycle, factor=value) for cycle, ts in cycles.items()]
