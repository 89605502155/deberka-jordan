# Быстрый старт

## 1. Знакопеременная мера и её разложения

```python
from deberka_jordan import SignedMeasure

nu = SignedMeasure({"a": 3.0, "b": -1.0, "c": -2.0})
print(nu.total(), nu.total_variation())  # 0.0 6.0
hahn = nu.hahn()
print(sorted(hahn.positive), sorted(hahn.negative))  # ['a'] ['b', 'c']
jordan = nu.jordan()
print(jordan.plus, jordan.minus)  # части nu+ и nu- в равенстве nu = nu+ - nu-
```

## 2. План цикла перераспределения

```python
from deberka_jordan import jordan_plan, min_pool, recipients_first, two_phase

current = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}  # МиБ
target = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
plan = jordan_plan(current, target, pool_free=100.0, deadband=64.0)
print(plan.donors, plan.recipients)  # кто отдаёт и кто получает, МиБ
print(plan.skipped)  # изменения меньше порога нечувствительности
print(plan.volume)  # 900.0: байты, перенесённые планом (600 между потребителями, 300 в пул)
print(min_pool(two_phase(plan), 100.0))  # 100.0: безопасный порядок
print(min_pool(recipients_first(plan), 100.0))  # -500.0: небезопасный порядок
```

## 3. Взаимозачёт предложений

```python
from deberka_jordan import netting_report

proposals = [("vm1", "vm2", 300.0), ("vm2", "vm3", 300.0), ("vm3", "vm1", 100.0)]
report = netting_report(proposals)
print(report.sequential_volume, report.jordan_volume)  # 700.0 200.0: байты
print(f"выигрыш {report.gain:.0%}")  # выигрыш 71%
```

## 4. Безопасное исполнение на поддельном баллоне

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

## 5. Командная строка

    deberka-jordan plan state.csv --pool 100 --deadband 64

Форматы входных файлов описаны в [cli.md](cli.md).
