# Программный интерфейс

Все имена экспортируются из пакета `deberka_jordan`. Единицы свободны, но должны быть
согласованы; примеры используют МиБ.

## Мера (`deberka_jordan.measure`)

`SignedMeasure(atoms, *, tol=0.0)` — отображение `атом -> ν({атом})`.

| Элемент | Смысл |
|---|---|
| `from_allocations(current, target, *, pool=None)` | Мера цикла; с `pool` атом пула замыкает её |
| `from_transfers(transfers)` | Взаимозачёт: сумма `(source, recipient, amount)` по атомам |
| `nu(subset)` | `ν(A)` для множества атомов |
| `total()`, `total_variation()` | `ν(X)` и `|ν|(X)` |
| `restrict(subset)`, `without(*atoms)` | Сужения |
| `hahn()` | `HahnDecomposition(positive, negative)` |
| `jordan()` | `JordanDecomposition(plus, minus)`; `.variation` — это `|ν|` |

`POOL` — имя атома пула по умолчанию.

## План (`deberka_jordan.plan`)

`jordan_plan(current, target, pool_free, *, deadband=0, force=(), floor=None,
ceiling=None, priority=None) -> Plan`

План содержит `donors`, `recipients`, `skipped`, `rationed`, `pool_before` и свойства
`take`, `give`, `pool_change`, `pool_after`, `volume` (байты, `pool="max"`), `operations` (балонные операции), `peak`, `is_empty`, а также методы
`measure(pool)` и `targets(current)`.

| Функция | Смысл |
|---|---|
| `ration(demand, budget, priority=None)` | Делит недостаточный бюджет пропорционально или по приоритету |
| `net_transfers(transfers)` | Свёрнутая мера по потребителям |
| `sequential_volume(transfers, *, factor=1.0)` | `factor · Σ amount`; по умолчанию `factor=1` дает перенесённые байты, `factor=2` — балонные операции |
| `lower_bound_volume(nu, pool=POOL)` | `W = Σ |ν({i})|` по потребителям: балонные операции; в байтах `W / 2` |
| `netting_report(transfers, cycle=None, *, factor=1.0)` | `NettingReport` с `ratio` и `gain`; жорданов объём равен `(factor / 2) Σ |чистое|`, выигрыш от `factor` не зависит |
| `plan_volume(plan, *, factor=1.0, pool="max", pool_weight=0.5)` | `factor · (min(take, give) + w · |изменение пула|)`; `w = 1` для `pool="max"` (по умолчанию, перенесённые байты; `plan.volume`), `w = pool_weight` для `pool="weighted"`; `pool="weighted", pool_weight=0.5, factor=2` равно `plan.operations` |
| `netting_by_cycle(rows, *, factor=1.0)` | Отчёт по каждому циклу строк `(cycle, source, recipient, amount)` |

## Порядки (`deberka_jordan.order`)

`Op(consumer, delta)`. `two_phase(plan)` (сначала доноры, безопасный порядок),
`recipients_first(plan)`, `shuffled(plan, rng=None)`, `pairwise(transfers)`,
`pool_trajectory(ops, pool_free)`, `min_pool(ops, pool_free)`,
`is_safe(ops, pool_free, tol=1e-9)`.

## Исполнители (`deberka_jordan.execute`)

Бэкенд имеет методы `now()`, `get_actual(consumer)`, `set_target(consumer, target)` и
`sleep(dt)`.

* `execute_two_phase(backend, plan, current, *, priority=None, timeout_s=30,
  poll_s=0.1, tol=1.0) -> ExecReport`
* `execute_simultaneous(backend, plan, current, ...)`: база сравнения, не безопасна.
* `RateLimitedSim(actual, pool_free, take_rate=200, give_rate=800, reclaimable=None,
  step=0.01)`: моделируемый исполнитель с конечной скоростью; ведёт `pool_min`.

`ExecReport` содержит `freed`, `given`, `duration_s`, `pool_min`, `unfinished` и `rationed`.

## Колебания и порог (`deberka_jordan.churn`)

| Функция | Смысл |
|---|---|
| `kappa(deltas)`, `WindowStats(variation, net).kappa` | Индекс колебаний |
| `window_stats(times, deltas, t_now, window)`, `kappa_series(...)` | Скользящее окно |
| `sampled_variation(samples)` | `V = Σ |d_k − d_{k−1}|` |
| `cycles_bound(samples, h)` | `V / h`, граница утверждения 2.3 |
| `replay_reserve(demand, dt, *, reserve, deadband=64, interval=None, theta=64, ...)` | `ReplayResult` |
| `deadband_sweep(demand, dt, deadbands, **kwargs)` | Проигрывание для каждого `h` |
| `choose_deadband(results, kappa_target=0.5)` | Наименьший `h` с медианой `κ` не выше цели |

## Живой бэкенд (`deberka_jordan.kvm`)

`LibvirtBackend(domains, pool=None)`: `domains` — отображение имён в объекты с методами
`memoryStats()` и `setMemoryFlags()`; `connect(uri, names=None)` открывает libvirt (нужен
`libvirt-python`). `snapshot()` возвращает размеры баллонов в МиБ, `pool_free()` — свободную
память хоста. `host_mem_available(path)` читает `MemAvailable` из `/proc/meminfo`.
