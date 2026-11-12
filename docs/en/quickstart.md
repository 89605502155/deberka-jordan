# Quick start

## 1. A signed measure and its decompositions

```python
from deberka_jordan import SignedMeasure

nu = SignedMeasure({"a": 3.0, "b": -1.0, "c": -2.0})
print(nu.total(), nu.total_variation())  # 0.0 6.0
hahn = nu.hahn()
print(sorted(hahn.positive), sorted(hahn.negative))  # ['a'] ['b', 'c']
jordan = nu.jordan()
print(jordan.plus, jordan.minus)  # the parts nu+ and nu- of nu = nu+ - nu-
```

## 2. The plan of a reallocation cycle

```python
from deberka_jordan import jordan_plan, min_pool, recipients_first, two_phase

current = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}  # MiB
target = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
plan = jordan_plan(current, target, pool_free=100.0, deadband=64.0)
print(plan.donors, plan.recipients)  # who gives and who receives, MiB
print(plan.skipped)  # changes below the dead band
print(plan.volume)  # 900.0: bytes moved (600 between consumers, 300 into the pool)
print(min_pool(two_phase(plan), 100.0))  # 100.0: the safe order
print(min_pool(recipients_first(plan), 100.0))  # -500.0: the unsafe order
```

## 3. Netting of proposals

```python
from deberka_jordan import netting_report

proposals = [("vm1", "vm2", 300.0), ("vm2", "vm3", 300.0), ("vm3", "vm1", 100.0)]
report = netting_report(proposals)
print(report.sequential_volume, report.jordan_volume)  # 700.0 200.0: bytes
print(f"gain {report.gain:.0%}")  # gain 71%
```

## 4. Safe execution on a fake balloon

```python
from deberka_jordan import execute_two_phase, jordan_plan
from deberka_jordan.kvm import LibvirtBackend


class FakeDomain:
    def __init__(self, mib: float) -> None:
        self.kib = round(mib * 1024)

    def memoryStats(self) -> dict[str, int]:
        return {"actual": self.kib}

    def setMemoryFlags(self, kib: int, flags: int) -> None:
        self.kib = kib


domains = {"vm1": FakeDomain(2048.0), "vm2": FakeDomain(1024.0)}
backend = LibvirtBackend(domains, pool=lambda: 128.0)
current_shares = backend.snapshot()
plan = jordan_plan(current_shares, {"vm1": 1536.0, "vm2": 1536.0}, backend.pool_free())
report = execute_two_phase(backend, plan, current_shares, timeout_s=1.0)
print(report.rationed, round(domains["vm2"].kib / 1024))  # False 1536
```

## 5. Command line

    deberka-jordan plan state.csv --pool 100 --deadband 64

See [cli.md](cli.md) for the input formats.
