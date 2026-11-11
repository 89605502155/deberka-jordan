"""deberka_jordan: reallocation plans for a shared resource by the Jordan decomposition.

A reallocation cycle among consumers of one pool is a signed measure. Its Hahn
decomposition splits consumers into donors and recipients. Its Jordan
decomposition gives the plan with the least volume of operations and a safe
two-phase order that never overdraws the pool. On the time axis the same idea
gives the oscillation index ``kappa`` and a justified choice of a dead band.

Modules: :mod:`~deberka_jordan.measure`, :mod:`~deberka_jordan.plan`,
:mod:`~deberka_jordan.order`, :mod:`~deberka_jordan.execute`, :mod:`~deberka_jordan.churn`,
:mod:`~deberka_jordan.kvm` (optional, libvirt).
"""

from importlib.metadata import PackageNotFoundError, version

from .churn import (
    Jump,
    ReplayResult,
    WindowStats,
    choose_deadband,
    cycles_bound,
    deadband_sweep,
    jumps_of,
    kappa,
    kappa_series,
    replay_reserve,
    sampled_variation,
    window_stats,
)
from .execute import Backend, ExecReport, RateLimitedSim, execute_simultaneous, execute_two_phase
from .measure import POOL, HahnDecomposition, JordanDecomposition, SignedMeasure
from .order import (
    Op,
    is_safe,
    min_pool,
    pairwise,
    pool_trajectory,
    recipients_first,
    shuffled,
    two_phase,
)
from .plan import (
    NettingReport,
    Plan,
    Transfer,
    jordan_plan,
    lower_bound_volume,
    net_transfers,
    netting_by_cycle,
    netting_report,
    plan_volume,
    ration,
    sequential_volume,
)

try:
    __version__ = version("deberka-jordan")
except PackageNotFoundError:  # pragma: no cover - running from a source tree
    __version__ = "0.0.0"

__all__ = [
    "POOL",
    "Backend",
    "ExecReport",
    "HahnDecomposition",
    "JordanDecomposition",
    "Jump",
    "NettingReport",
    "Op",
    "Plan",
    "RateLimitedSim",
    "ReplayResult",
    "SignedMeasure",
    "Transfer",
    "WindowStats",
    "__version__",
    "choose_deadband",
    "cycles_bound",
    "deadband_sweep",
    "execute_simultaneous",
    "execute_two_phase",
    "is_safe",
    "jordan_plan",
    "jumps_of",
    "kappa",
    "kappa_series",
    "lower_bound_volume",
    "min_pool",
    "net_transfers",
    "netting_by_cycle",
    "netting_report",
    "pairwise",
    "plan_volume",
    "pool_trajectory",
    "ration",
    "recipients_first",
    "replay_reserve",
    "sampled_variation",
    "sequential_volume",
    "shuffled",
    "two_phase",
    "window_stats",
]
