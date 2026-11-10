# jordanplan

Reallocation plans for a shared resource by the Hahn–Jordan decomposition.

`jordanplan` treats one reallocation cycle among consumers of a common pool
(host memory shared by virtual machines, CPU quota, bandwidth, budget) as a
**signed measure**. From that measure it builds:

1. **The least-volume plan.** Netting all proposals of a cycle by the Jordan
   decomposition gives the minimum possible volume of operations
   `W = Σ|a'ᵢ − aᵢ|`.
2. **A safe order.** Donors first, recipients second. The pool never goes
   negative, even with slow actuators or donors that cannot give everything.
3. **An oscillation index and a dead band.** The jump measure of each
   consumer on the time axis gives `κ = 1 − |ξ(W)| / |ξ|(W)`, and a sweep picks
   the smallest dead band `h` that keeps `κ` below a target. The number of
   operations is then provably bounded by `V/h`.

The core is pure Python with no dependencies. A libvirt backend for KVM memory
ballooning is an optional extra.

[Русская версия](README.ru.md)

## Install

```bash
pip install jordanplan-deberka            # core
pip install "jordanplan-deberka[kvm]"     # + libvirt backend
```

Python 3.11–3.14. The import name is `jordanplan`.

## Quick start

```python
from jordanplan import jordan_plan, two_phase, recipients_first, min_pool

current = {"vm1": 2000, "vm2": 3000, "vm3": 1500, "vm4": 2500}   # MiB
target  = {"vm1": 2600, "vm2": 2500, "vm3": 1530, "vm4": 2100}

plan = jordan_plan(current, target, pool_free=100, deadband=64)
plan.donors        # {'vm2': 500.0, 'vm4': 400.0}
plan.recipients    # {'vm1': 600.0}
plan.skipped       # {'vm3': 30.0}  below the dead band
plan.volume        # 1500.0  = Σ|ν({i})|, the lower bound

min_pool(two_phase(plan), 100)          # 100.0  never negative
min_pool(recipients_first(plan), 100)   # -500.0 overdraws the pool
```

### Netting a controller's proposals

```python
from jordanplan import netting_report

proposals = [("vm1", "vm2", 300), ("vm2", "vm3", 300), ("vm3", "vm1", 100)]
r = netting_report(proposals)
r.sequential_volume, r.jordan_volume, r.gain     # (1400.0, 400.0, 0.714...)
```

### Executing on actuators with finite speed

```python
from jordanplan import RateLimitedSim, execute_two_phase, jordan_plan

plan = jordan_plan(current, {"vm1": 2800, "vm2": 2200}, pool_free=0)
sim = RateLimitedSim(current, pool_free=0, take_rate=200, give_rate=800,
                     reclaimable={"vm2": 500})          # vm2 can give only 500
rep = execute_two_phase(sim, plan, current, timeout_s=10)
rep.freed, rep.given, rep.pool_min, rep.rationed
# ({'vm2': 500.0}, {'vm1': 500.0}, 0.0, True)
```

The same call drives real VMs:

```python
from jordanplan.kvm import LibvirtBackend

be = LibvirtBackend.connect("qemu:///system", ["vm1", "vm2", "vm3"])
cur = be.snapshot()                                   # balloon `actual`, MiB
plan = jordan_plan(cur, new_targets, be.pool_free(), deadband=64)
execute_two_phase(be, plan, cur, timeout_s=60)
```

Any object with `now()`, `get_actual()`, `set_target()` and `sleep()` is a
backend: cgroups, cloud quotas, a test double.

### Choosing a dead band

```python
from jordanplan import deadband_sweep, choose_deadband

# demand: {"vm1": [...], "vm2": [...]} sampled every dt seconds
res = deadband_sweep(demand, dt=0.1, deadbands=[0, 16, 32, 64, 128, 256],
                     reserve=256, interval=2.0)
for r in res:
    print(r.h, r.cycles, r.volume, r.kappa_median, r.deficit_integral, r.bound)
choose_deadband(res, kappa_target=0.5)
```

## Command line

```bash
jordanplan plan state.csv --pool 100 --deadband 64     # consumer,current,target
jordanplan net proposals.csv --out netting.csv         # cycle,source,recipient,amount
jordanplan deadband trace.csv --interval 2 --reserve 256 --h 0,32,64,128 --out sweep.csv
```

`trace.csv` has a `t_s` column on a uniform grid and one column per consumer.

## Theory in short

Let `X = {pool, 1, …, N}`. A cycle `a → a'` is the signed measure
`ν({i}) = a'ᵢ − aᵢ`, `ν({pool}) = −Σν({i})`, so `ν(X) = 0`
(Halmos, *Measure Theory*, §28–29).

| Claim | Statement | Where |
|---|---|---|
| 1. Lower bound | Any sequence of operations moving `a` to `a'` has volume `≥ W = Σ|ν({i})|`. The Jordan plan attains it. Netting gain is `1 − W/W_seq`. | `jordan_plan`, `netting_report` |
| 2. Safe order | If the pool is non-negative before and after the cycle, donors-then-recipients keeps it non-negative at every moment. | `two_phase`, `execute_two_phase` |
| 3. Dead band | With target `d + s`, threshold `h` and `s ≥ h`, the number of jumps is `≤ V/h` and their volume is `≤ V`, where `V` is the variation of observed demand. | `replay_reserve`, `cycles_bound` |

All three are checked by property-based tests (`tests/`).

## When it helps most

| Situation | What you get |
|---|---|
| The controller emits pairwise transfers (diffusion, gossip, market-like matching), and one consumer can be both source and recipient in a cycle | Netting removes the transit volume: only the net change of every consumer is executed. |
| The free pool is small and the actuator is slow (balloon inflation is slower than deflation) | The two-phase executor never overdraws the pool and grants only what was actually freed. |
| The controller "breathes": allocations swing back and forth | `κ` measures it, and the dead band sweep trades operations for deficit with a proven bound. |

When it does **not** help: if the controller already outputs final targets and
the pool is large, the plan has nothing to net and any order is safe. Claim 1
then only justifies executing the net change.

## Development

```bash
uv sync
uv run pytest
uv run ruff check src tests examples
uv run mypy
```

## Citing

If you use the library in research, please cite the accompanying paper
(reference will be added after publication).

## License

MIT, see [LICENSE](LICENSE).
