"""Executors for plans on actuators with finite speed.

The two-phase executor reclaims from donors, waits until the capacity is
actually freed (with a timeout), and then grants recipients no more than was
actually freed plus the free pool. So the pool stays non-negative even when an
actuator is slow or a donor cannot give everything.

Any object that implements :class:`Backend` can be driven: a simulator
(:class:`RateLimitedSim`), libvirt domains (:mod:`jordanplan.kvm`), cgroups,
cloud quotas.
"""

from __future__ import annotations

from collections.abc import Hashable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

from .plan import Plan, ration


@runtime_checkable
class Backend(Protocol):
    """Actuator interface used by the executors."""

    def now(self) -> float:
        """Monotonic time, seconds."""

    def get_actual(self, consumer: Hashable) -> float:
        """Current actual share of the consumer."""

    def set_target(self, consumer: Hashable, target: float) -> None:
        """Request a new share. The actuator moves towards it at its own pace."""

    def sleep(self, dt: float) -> None:
        """Wait ``dt`` seconds (a simulator advances its clock)."""


class RateLimitedSim:
    """Simulated actuator with finite speed and a shared pool.

    Reclaiming (``target < actual``) runs at ``take_rate`` units/s and never
    goes below ``actual - reclaimable[c]``. Granting runs at ``give_rate``
    units/s and is taken from the pool even if the pool is empty, so a bad
    order of operations shows up as a negative ``pool_min``.

    For KVM memory ballooning: ``take_rate`` is the inflate speed and
    ``give_rate`` is the deflate speed, in MiB/s.
    """

    def __init__(self, actual: Mapping[Hashable, float], pool_free: float,
                 take_rate: float = 200.0, give_rate: float = 800.0,
                 reclaimable: Mapping[Hashable, float] | None = None,
                 step: float = 0.01) -> None:
        if take_rate <= 0.0 or give_rate <= 0.0 or step <= 0.0:
            raise ValueError("rates and step must be positive")
        self.actual = {c: float(a) for c, a in actual.items()}
        self.target = dict(self.actual)
        self.pool = float(pool_free)
        self.pool_min = self.pool
        self.take_rate, self.give_rate, self.step = take_rate, give_rate, step
        reclaimable = reclaimable or {}
        self.floor = {c: a - reclaimable.get(c, float("inf")) for c, a in self.actual.items()}
        self.t = 0.0

    def now(self) -> float:
        return self.t

    def get_actual(self, consumer: Hashable) -> float:
        return self.actual[consumer]

    def set_target(self, consumer: Hashable, target: float) -> None:
        self.target[consumer] = float(target)

    def pool_free(self) -> float:
        return self.pool

    def sleep(self, dt: float) -> None:
        steps = max(1, round(dt / self.step))
        h = dt / steps
        for _ in range(steps):
            for c, a in self.actual.items():
                tgt = self.target[c]
                if tgt < a:
                    move = min(self.take_rate * h, a - max(tgt, self.floor[c]))
                    if move > 0.0:
                        self.actual[c] = a - move
                        self.pool += move
                elif tgt > a:
                    move = min(self.give_rate * h, tgt - a)
                    self.actual[c] = a + move
                    self.pool -= move
            self.pool_min = min(self.pool_min, self.pool)
            self.t += h


@dataclass
class ExecReport:
    """Outcome of executing one cycle."""

    freed: dict[Hashable, float]
    given: dict[Hashable, float]
    duration_s: float
    pool_min: float | None = None
    """Lowest pool level if the backend tracks it (``RateLimitedSim`` does)."""
    unfinished: list[Hashable] = field(default_factory=list)
    """Consumers that did not reach their target before the timeout."""
    rationed: bool = False
    """True if recipients got less than planned because donors fell short."""


def _wait(backend: Backend, targets: Mapping[Hashable, float], timeout_s: float,
          poll_s: float, tol: float) -> list[Hashable]:
    start = backend.now()
    while True:
        left = [c for c, t in targets.items() if abs(backend.get_actual(c) - t) > tol]
        if not left or backend.now() - start >= timeout_s:
            return left
        backend.sleep(poll_s)


def execute_two_phase(backend: Backend, plan: Plan[Any], current: Mapping[Hashable, float],
                      *, priority: Mapping[Hashable, float] | None = None,
                      timeout_s: float = 30.0, poll_s: float = 0.1,
                      tol: float = 1.0) -> ExecReport:
    """Execute ``plan`` safely.

    1. Set reduced targets for all donors.
    2. Wait until donors reach them or ``timeout_s`` passes.
    3. Freeze donors that fell short at their actual share.
    4. Budget = ``plan.pool_before`` + actually freed.
    5. If recipients need more than the budget, ration them.
    6. Set increased targets for recipients and wait for them.
    """
    t0 = backend.now()
    donor_targets = {c: current[c] - x for c, x in plan.donors.items()}
    for c, t in donor_targets.items():
        backend.set_target(c, t)
    stuck = _wait(backend, donor_targets, timeout_s, poll_s, tol)
    for c in stuck:
        backend.set_target(c, backend.get_actual(c))
    freed = {c: max(current[c] - backend.get_actual(c), 0.0) for c in plan.donors}
    budget = plan.pool_before + sum(freed.values())
    give = dict(plan.recipients)
    rationed = False
    if sum(give.values()) > budget + tol:
        give = ration(give, budget, priority)
        rationed = True
    recip_targets = {c: current[c] + g for c, g in give.items()}
    for c, t in recip_targets.items():
        backend.set_target(c, t)
    left = _wait(backend, recip_targets, timeout_s, poll_s, tol)
    given = {c: backend.get_actual(c) - current[c] for c in give}
    return ExecReport(freed, given, backend.now() - t0, getattr(backend, "pool_min", None),
                      stuck + left, rationed)


def execute_simultaneous(backend: Backend, plan: Plan[Any], current: Mapping[Hashable, float],
                         *, timeout_s: float = 30.0, poll_s: float = 0.1,
                         tol: float = 1.0) -> ExecReport:
    """Set all targets at once. Baseline for comparison, not safe."""
    t0 = backend.now()
    targets = plan.targets(current)
    for c, t in targets.items():
        backend.set_target(c, t)
    left = _wait(backend, targets, timeout_s, poll_s, tol)
    freed = {c: max(current[c] - backend.get_actual(c), 0.0) for c in plan.donors}
    given = {c: backend.get_actual(c) - current[c] for c in plan.recipients}
    return ExecReport(freed, given, backend.now() - t0, getattr(backend, "pool_min", None),
                      left)
