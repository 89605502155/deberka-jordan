"""Quick tour of deberka_jordan without any hardware.

Run: ``uv run python examples/01_quickstart.py``
"""

import random

from deberka_jordan import (
    RateLimitedSim,
    choose_deadband,
    deadband_sweep,
    execute_simultaneous,
    execute_two_phase,
    jordan_plan,
    min_pool,
    netting_report,
    recipients_first,
    two_phase,
)

current = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}  # MiB

# 1. Plan and its order -------------------------------------------------------
target = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
plan = jordan_plan(current, target, pool_free=100.0, deadband=64.0)
print("donors", plan.donors, "recipients", plan.recipients, "skipped", plan.skipped)
print(
    "volume",
    plan.volume,
    "min pool: two-phase",
    min_pool(two_phase(plan), 100.0),
    "recipients-first",
    min_pool(recipients_first(plan), 100.0),
)

# 2. Netting of pairwise proposals ---------------------------------------------
proposals = [("vm1", "vm2", 300.0), ("vm2", "vm3", 300.0), ("vm3", "vm1", 100.0)]
r = netting_report(proposals)
print(
    f"netting: sequential {r.sequential_volume:.0f}, Jordan {r.jordan_volume:.0f}, "
    f"gain {r.gain:.0%}"
)

# 3. Execution with a slow balloon --------------------------------------------
plan = jordan_plan(current, {"vm1": 2800.0, "vm2": 2200.0}, pool_free=0.0)
for name, run in [("two-phase", execute_two_phase), ("simultaneous", execute_simultaneous)]:
    sim = RateLimitedSim(current, 0.0, take_rate=200.0, give_rate=800.0)
    rep = run(sim, plan, current, timeout_s=10.0)
    print(f"{name:13s} duration {rep.duration_s:.1f} s, pool min {rep.pool_min:.0f} MiB")

# 4. Dead band on a noisy demand trace ------------------------------------------
rng = random.Random(1)
demand: dict[str, list[float]] = {}
for vm in current:
    x, xs = 1500.0, []
    for _ in range(3600):
        x = max(200.0, x + rng.gauss(0.0, 30.0))
        xs.append(x)
    demand[vm] = xs
res = deadband_sweep(demand, 1.0, [0, 32, 64, 128, 256], reserve=256.0, interval=2.0)
for row in res:
    print(
        f"h={row.h:5.0f} cycles={row.cycles:5d} volume={row.volume / 1024:7.1f} GiB "
        f"kappa={row.kappa_median:.2f} deficit={row.deficit_integral / 1024:.2f} GiB*s"
    )
print("chosen h:", choose_deadband(res, kappa_target=0.5))
