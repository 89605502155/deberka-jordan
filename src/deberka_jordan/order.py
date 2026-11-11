"""Order of operations and the pool invariant.

Claim 2 (safe order). Let the pool be non-negative before and after the cycle.
If all donors are executed first and all recipients after them, the pool stays
non-negative at every moment: it first only grows and then decreases
monotonically to its final value. Other orders may overdraw the pool.

Operations here are instantaneous. Finite actuator speed is handled by the
executors in :mod:`deberka_jordan.execute`.
"""

from __future__ import annotations

import random
from collections.abc import Hashable, Iterable, Sequence
from typing import Any, NamedTuple

from .plan import Plan


class Op(NamedTuple):
    """Change of the share of one consumer: ``delta > 0`` gives, ``< 0`` takes."""

    consumer: Hashable
    delta: float


def two_phase(plan: Plan[Any]) -> list[Op]:
    """Donors first, then recipients (the safe order)."""
    return [Op(c, -x) for c, x in plan.donors.items()] + [
        Op(c, x) for c, x in plan.recipients.items()
    ]


def recipients_first(plan: Plan[Any]) -> list[Op]:
    """Recipients first, then donors. Baseline that may overdraw the pool."""
    return [Op(c, x) for c, x in plan.recipients.items()] + [
        Op(c, -x) for c, x in plan.donors.items()
    ]


def shuffled(plan: Plan[Any], rng: random.Random | None = None) -> list[Op]:
    """Random order of the plan's operations. Baseline."""
    ops = two_phase(plan)
    (rng or random.Random()).shuffle(ops)  # noqa: S311 - a baseline, not a secret
    return ops


def pairwise(transfers: Iterable[tuple[Hashable, Hashable, float]]) -> list[Op]:
    """Proposals one by one: take from the source, then give to the recipient."""
    out: list[Op] = []
    for source, recipient, amount in transfers:
        out += [Op(source, -float(amount)), Op(recipient, float(amount))]
    return out


def pool_trajectory(ops: Sequence[tuple[Hashable, float]], pool_free: float) -> list[float]:
    """Pool level before the first and after every operation."""
    level = float(pool_free)
    out = [level]
    for _, delta in ops:
        level -= delta
        out.append(level)
    return out


def min_pool(ops: Sequence[tuple[Hashable, float]], pool_free: float) -> float:
    """Lowest pool level over the whole trajectory."""
    return min(pool_trajectory(ops, pool_free))


def is_safe(ops: Sequence[tuple[Hashable, float]], pool_free: float, tol: float = 1e-9) -> bool:
    """Return True if the pool never goes below zero."""
    return min_pool(ops, pool_free) >= -tol
