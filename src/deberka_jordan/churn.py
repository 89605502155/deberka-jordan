"""Controller oscillations on the time axis and the choice of a dead band.

The share ``a_i(t)`` of a consumer is a step function. Its jumps define the
atomic signed measure ``xi_i`` on the time axis. In a window ``W``:

* ``|xi_i|(W)``: total variation, the volume of operations;
* ``xi_i(W)``: net change;
* ``kappa_i(W) = 1 - |xi_i(W)| / |xi_i|(W)``: oscillation index in ``[0, 1]``.
  It is 0 when the share moves in one direction and tends to 1 when it swings
  back and forth.

Claim 3 (dead band). Let the controller keep the target ``d + s``, execute a
change only when ``|target - a| > h`` (or the consumer is short), and let
``s >= h``. Then the number of jumps is at most ``V / h`` and their volume is
at most ``V``, where ``V`` is the variation of observed demand (the sum of
absolute differences of consecutive samples).
"""

from __future__ import annotations

import itertools
import math
import statistics
from collections.abc import Hashable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NamedTuple


class Jump(NamedTuple):
    """Jump of the share of one consumer at time ``t``."""

    t: float
    consumer: Hashable
    delta: float


@dataclass(frozen=True, slots=True)
class WindowStats:
    """Jumps of one consumer in a window: total variation and net change."""

    variation: float
    """``|xi|(W)``: volume of operations in the window."""
    net: float
    """``xi(W)``: net change in the window."""

    @property
    def kappa(self) -> float:
        """Oscillation index ``1 - |net| / variation`` (0 for an empty window)."""
        if self.variation <= 0.0:
            return 0.0
        return max(0.0, 1.0 - abs(self.net) / self.variation)


def kappa(deltas: Iterable[float]) -> float:
    """Oscillation index of a sequence of jumps."""
    ds = list(deltas)
    return WindowStats(sum(abs(x) for x in ds), sum(ds)).kappa


def jumps_of(
    jumps: Iterable[tuple[float, Hashable, float]], consumer: Hashable
) -> tuple[list[float], list[float]]:
    """Return the times and sizes of the jumps of one consumer."""
    sel = [(t, x) for t, c, x in jumps if c == consumer]
    return [t for t, _ in sel], [x for _, x in sel]


def window_stats(
    times: Sequence[float], deltas: Sequence[float], t_now: float, window: float
) -> WindowStats:
    """Statistics of jumps in ``(t_now - window, t_now]``."""
    lo = t_now - window
    xs = [x for t, x in zip(times, deltas, strict=True) if lo < t <= t_now]
    return WindowStats(sum(abs(x) for x in xs), sum(xs))


def kappa_series(
    times: Sequence[float], deltas: Sequence[float], at: Iterable[float], window: float
) -> list[float]:
    """Oscillation index in a sliding window evaluated at the moments ``at``."""
    return [window_stats(times, deltas, t, window).kappa for t in at]


def sampled_variation(samples: Sequence[float]) -> float:
    """``V = sum |d_k - d_(k-1)|``."""
    return sum(abs(b - a) for a, b in itertools.pairwise(samples))


def cycles_bound(samples: Sequence[float], h: float) -> float:
    """Upper bound ``V / h`` on the number of jumps (Claim 3)."""
    return sampled_variation(samples) / h if h > 0.0 else math.inf


# Replay of a reserve controller with a dead band ---------------------------


@dataclass(frozen=True, slots=True)
class ReplayResult:
    """Replay of the reserve controller on a demand trace."""

    h: float
    jumps: list[Jump]
    cycles: int
    """Monitoring moments with at least one jump."""
    volume: float
    """Total volume of operations ``sum |delta|``."""
    bound: float
    """Sum over consumers of ``V_i / h`` (Claim 3); ``inf`` for ``h = 0``."""
    observed_variation: float
    """Sum over consumers of ``V_i``."""
    deficit_integral: float
    """``integral of max(d - a, 0) dt`` summed over consumers, unit·s."""
    deficit_share: float
    """Share of consumer-time with deficit above ``theta``."""
    kappa_median: float
    """Median of the oscillation index over consumers and window positions."""


DEFAULT_DEADBAND = 64.0
"""Default dead band ``h``, MiB: the value of the article (trace A, reserve 256 MiB, interval 2 s)."""


def replay_reserve(
    demand: Mapping[Any, Sequence[float]],
    dt: float,
    *,
    reserve: float,
    deadband: float = DEFAULT_DEADBAND,
    interval: float | None = None,
    theta: float = 64.0,
    kappa_window: float = 60.0,
    kappa_step: float = 10.0,
) -> ReplayResult:
    """Replay the controller "demand + reserve" with a dead band on a trace.

    ``demand`` maps every consumer to samples on a uniform grid with step
    ``dt`` seconds. The controller observes demand every ``interval`` seconds
    (default ``dt``), sets the target ``d + reserve`` and executes it when
    ``|target - a| > deadband`` or the consumer is short (``a < d``). The share
    is held between observations and the actuator is instantaneous.
    """
    if dt <= 0.0:
        msg = "dt must be positive"
        raise ValueError(msg)
    names = list(demand)
    if not names:
        msg = "empty trace"
        raise ValueError(msg)
    n = len(demand[names[0]])
    if any(len(demand[c]) != n for c in names):
        msg = "all consumers must have the same number of samples"
        raise ValueError(msg)
    stride = max(1, round((interval or dt) / dt))
    a = {c: float(demand[c][0]) + reserve for c in names}
    jumps: list[Jump] = []
    cycles = 0
    deficit_sum = 0.0
    above = 0
    observed: dict[Hashable, list[float]] = {c: [] for c in names}
    for k in range(n):
        t = k * dt
        if k % stride == 0:
            moved = False
            for c in names:
                d = float(demand[c][k])
                observed[c].append(d)
                tgt = d + reserve
                if (a[c] < d or abs(tgt - a[c]) > deadband) and tgt != a[c]:
                    jumps.append(Jump(t, c, tgt - a[c]))
                    a[c] = tgt
                    moved = True
            cycles += moved
        for c in names:
            f = float(demand[c][k]) - a[c]
            if f > 0.0:
                deficit_sum += f * dt
                above += f > theta
    var = sum(sampled_variation(observed[c]) for c in names)
    bound = sum(cycles_bound(observed[c], deadband) for c in names) if deadband > 0 else math.inf
    t_end = n * dt
    at = [
        kappa_window + i * kappa_step
        for i in range(max(0, math.ceil((t_end - kappa_window) / kappa_step)))
    ]
    kap: list[float] = []
    for c in names:
        ts, xs = jumps_of(jumps, c)
        kap += kappa_series(ts, xs, at, kappa_window)
    return ReplayResult(
        h=float(deadband),
        jumps=jumps,
        cycles=cycles,
        volume=sum(abs(j.delta) for j in jumps),
        bound=bound,
        observed_variation=var,
        deficit_integral=deficit_sum,
        deficit_share=above / (n * len(names)),
        kappa_median=statistics.median(kap) if kap else 0.0,
    )


def deadband_sweep(
    demand: Mapping[Any, Sequence[float]], dt: float, deadbands: Iterable[float], **kwargs: float
) -> list[ReplayResult]:
    """:func:`replay_reserve` for every dead band in ``deadbands``."""
    return [replay_reserve(demand, dt, deadband=h, **kwargs) for h in deadbands]


def choose_deadband(
    results: Iterable[ReplayResult | Mapping[str, float]], kappa_target: float = 0.5
) -> float | None:
    """Smallest dead band whose median oscillation index does not exceed the target."""
    ok = []
    for r in results:
        h, k = (r.h, r.kappa_median) if isinstance(r, ReplayResult) else (r["h"], r["kappa_median"])
        if k <= kappa_target:
            ok.append(h)
    return min(ok) if ok else None
