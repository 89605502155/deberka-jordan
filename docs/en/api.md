# API

All names are re-exported from the package `deberka_jordan`. Units are free but
must be consistent; the examples use MiB.

## Measure (`deberka_jordan.measure`)

`SignedMeasure(atoms, *, tol=0.0)` is a mapping `atom -> ν({atom})`.

| Member | Meaning |
|---|---|
| `from_allocations(current, target, *, pool=None)` | Measure of the cycle; with `pool` the pool atom closes it |
| `from_transfers(transfers)` | Netting: sum of `(source, recipient, amount)` per atom |
| `nu(subset)` | `ν(A)` for a set of atoms |
| `total()`, `total_variation()` | `ν(X)` and `|ν|(X)` |
| `restrict(subset)`, `without(*atoms)` | Restrictions |
| `hahn()` | `HahnDecomposition(positive, negative)` |
| `jordan()` | `JordanDecomposition(plus, minus)`; `.variation` is `|ν|` |

`POOL` is the default name of the pool atom.

## Plan (`deberka_jordan.plan`)

`jordan_plan(current, target, pool_free, *, deadband=0, force=(), floor=None,
ceiling=None, priority=None) -> Plan`

The plan has `donors`, `recipients`, `skipped`, `rationed`, `pool_before` and the
properties `take`, `give`, `pool_change`, `pool_after`, `volume`, `peak`,
`is_empty`, and the methods `measure(pool)` and `targets(current)`.

| Function | Meaning |
|---|---|
| `ration(demand, budget, priority=None)` | Split an insufficient budget, in proportion or by priority |
| `net_transfers(transfers)` | Netted measure over consumers |
| `sequential_volume(transfers)` | `2 Σ amount` |
| `lower_bound_volume(nu, pool=POOL)` | `W = Σ |ν({i})|` over consumers |
| `netting_report(transfers, cycle=None)` | `NettingReport` with `ratio` and `gain` |
| `netting_by_cycle(rows)` | One report per cycle of `(cycle, source, recipient, amount)` rows |

## Orders (`deberka_jordan.order`)

`Op(consumer, delta)`. `two_phase(plan)` (donors first, the safe order),
`recipients_first(plan)`, `shuffled(plan, rng=None)`, `pairwise(transfers)`,
`pool_trajectory(ops, pool_free)`, `min_pool(ops, pool_free)`,
`is_safe(ops, pool_free, tol=1e-9)`.

## Executors (`deberka_jordan.execute`)

A backend has `now()`, `get_actual(consumer)`, `set_target(consumer, target)` and
`sleep(dt)`.

* `execute_two_phase(backend, plan, current, *, priority=None, timeout_s=30,
  poll_s=0.1, tol=1.0) -> ExecReport`
* `execute_simultaneous(backend, plan, current, ...)`: a baseline, not safe.
* `RateLimitedSim(actual, pool_free, take_rate=200, give_rate=800, reclaimable=None,
  step=0.01)`: a simulated actuator with finite speed; it tracks `pool_min`.

`ExecReport` has `freed`, `given`, `duration_s`, `pool_min`, `unfinished` and
`rationed`.

## Churn and dead band (`deberka_jordan.churn`)

| Function | Meaning |
|---|---|
| `kappa(deltas)`, `WindowStats(variation, net).kappa` | Oscillation index |
| `window_stats(times, deltas, t_now, window)`, `kappa_series(...)` | Sliding window |
| `sampled_variation(samples)` | `V = Σ |d_k − d_{k−1}|` |
| `cycles_bound(samples, h)` | `V / h`, the bound of claim 2.3 |
| `replay_reserve(demand, dt, *, reserve, deadband, interval=None, theta=64, ...)` | `ReplayResult` |
| `deadband_sweep(demand, dt, deadbands, **kwargs)` | Replay for each `h` |
| `choose_deadband(results, kappa_target=0.5)` | Smallest `h` with median `κ` at most the target |

## Live backend (`deberka_jordan.kvm`)

`LibvirtBackend(domains, pool=None)`: `domains` maps names to objects with
`memoryStats()` and `setMemoryFlags()`; `connect(uri, names=None)` opens libvirt
(needs `libvirt-python`). `snapshot()` returns the balloon sizes in MiB,
`pool_free()` the free host memory. `host_mem_available(path)` reads
`MemAvailable` from `/proc/meminfo`.
