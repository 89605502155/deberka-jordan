# deberka-jordan

[![PyPI](https://img.shields.io/pypi/v/deberka-jordan.svg)](https://pypi.org/project/deberka-jordan/)
[![Python](https://img.shields.io/pypi/pyversions/deberka-jordan.svg)](https://pypi.org/project/deberka-jordan/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/89605502155/deberka-jordan/blob/main/LICENSE)

**Планы перераспределения общего ресурса на основе разложения Хана–Жордана.**

Цикл перераспределения между потребителями одного пула (память хоста, квота CPU,
полоса) — это знакопеременная мера на множестве «пул и потребители».
deberka-jordan вычисляет:

* разложение Хана цикла: доноры и получатели;
* план Жордана: взаимозачёт всех предложений цикла с наименьшим объёмом операций,
  `W = Σ |ν({i})|`;
* безопасный двухфазный порядок (сначала доноры, затем получатели), который не
  уводит пул в минус, и исполнитель, который ждёт фактически освобождённой памяти;
* индекс колебаний `κ` контроллера на оси времени и порог нечувствительности `h`,
  выбранный проигрыванием трассы потребности.

Первая цель — баллонирование памяти ВМ KVM через libvirt; ядро библиотеки от неё
не зависит.

English version: [README.md](https://github.com/89605502155/deberka-jordan/blob/main/README.md).
Документация: [English](https://github.com/89605502155/deberka-jordan/tree/main/docs/en) ·
[Русский](https://github.com/89605502155/deberka-jordan/tree/main/docs/ru) ·
[Журнал изменений](https://github.com/89605502155/deberka-jordan/blob/main/CHANGELOG.md) ·
[Задачи](https://github.com/89605502155/deberka-jordan/issues)

Библиотека сопровождает статью 2 серии А. Ферубко и О. Д. Казакова, Брянский государственный
инженерно-технологический университет (БГИТУ). Теория:
[docs/ru/theory.md](https://github.com/89605502155/deberka-jordan/blob/main/docs/ru/theory.md).

## Установка

```sh
pip install deberka-jordan                # ядро: без зависимостей
pip install "deberka-jordan[kvm]"         # плюс libvirt-python для живых доменов
```

Нужен Python 3.11 или новее.

## Быстрый старт

```python
from deberka_jordan import SignedMeasure, jordan_plan, min_pool, netting_report
from deberka_jordan import recipients_first, two_phase

nu = SignedMeasure({"a": 3.0, "b": -1.0, "c": -2.0})
print(nu.total(), nu.total_variation())  # 0.0 6.0

current = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}  # МиБ
target = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
plan = jordan_plan(current, target, pool_free=100.0, deadband=64.0)
print(plan.volume)  # 1500.0 МиБ операций
print(min_pool(two_phase(plan), 100.0))  # 100.0: безопасный порядок, пул не ниже старта
print(min_pool(recipients_first(plan), 100.0))  # -500.0: неверный порядок уводит пул в минус

report = netting_report([("vm1", "vm2", 300.0), ("vm2", "vm3", 300.0), ("vm3", "vm1", 100.0)])
print(report.sequential_volume, report.jordan_volume)  # 1400.0 400.0
```

Командная строка, на файле состояния с колонками `consumer,current,target`:

    deberka-jordan plan state.csv --pool 100 --deadband 64
    deberka-jordan net proposals.csv --out netting.csv
    deberka-jordan deadband trace.csv --h 0,64,128 --reserve 256

## Отличия от существующих пакетов

Разложения Хана и Жордана — классическая теория меры (Халмош, §28–29). На PyPI есть
пакеты с такими же названиями для матриц и топологического анализа данных, и ни один
из них не делает того, что делает эта библиотека:

* `jordan-form` вычисляет жорданову форму матрицы, это другой объект;
* `multipers` работает с персистентными модулями в топологическом анализе данных.

Пакеты распределения ресурсов (планировщики квот, размещение задач) выбирают цели,
но не сворачивают цикл предложений к наименьшему объёму операций и не дают безопасного
порядка операций для пула.

| Возможность | deberka-jordan | `jordan-form`, `multipers`, планировщики распределения |
|---|---|---|
| Разложения Хана и Жордана конечной знакопеременной меры на потребителях и пуле | да | нет |
| Взаимозачёт цикла с наименьшим объёмом `W = Σ |ν({i})|` и базой «поочерёдно» | да | нет |
| Безопасный двухфазный порядок без уходящего в минус пула, исполнитель ждёт освобождения памяти | да | нет |
| Индекс колебаний `κ` и порог нечувствительности `h`, выбранный на трассе потребности | да | нет |
| Бэкенд баллона libvirt (необязательный) | да | нет |

## Модули

| Модуль | Содержимое |
|---|---|
| `measure` | `SignedMeasure`, `HahnDecomposition`, `JordanDecomposition` |
| `plan` | `jordan_plan`, `Plan`, `ration`, взаимозачёт: `netting_report`, `netting_by_cycle` |
| `order` | `two_phase`, `recipients_first`, `shuffled`, `pairwise`, `min_pool`, `is_safe` |
| `execute` | `execute_two_phase`, `execute_simultaneous`, `RateLimitedSim` |
| `churn` | `kappa`, `replay_reserve`, `deadband_sweep`, `choose_deadband`, `cycles_bound` |
| `kvm` | `LibvirtBackend`, `host_mem_available` (необязательный, нужен libvirt-python) |

## Когда это помогает

Числа статьи получены на стенде и в этот пакет не входят. Примеры показывают механизмы
на небольших входах: `examples/02_netting_log.py` (кольцо предложений даёт взаимозачёт
74 % объёма, веер предложений не сворачивается совсем) и `examples/03_two_phase_fake.py`
(исполнитель переносит память в безопасном порядке).

## Разработка

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
bash scripts/install_hooks.sh   # один раз в клоне: ограничения сообщений коммитов
```

Сообщения коммитов в этом репозитории: тема не длиннее 8 символов, тела нет. Хук ставит
`scripts/install_hooks.sh` и запускает `scripts/check_commit_msg.py`.

## Цитирование

См. [CITATION.cff](https://github.com/89605502155/deberka-jordan/blob/main/CITATION.cff)
или кнопку «Cite this repository» на GitHub.

## Авторы

- Ферубко Андрей, [ORCID 0009-0006-5625-137X](https://orcid.org/0009-0006-5625-137X)
- Казаков Олег Дмитриевич, [ORCID 0000-0001-9665-8138](https://orcid.org/0000-0001-9665-8138)

Брянский государственный инженерно-технологический университет (БГИТУ).

## Лицензия

MIT. Copyright (c) 2026 Andrey Ferubko, Oleg Kazakov. См. [LICENSE](https://github.com/89605502155/deberka-jordan/blob/main/LICENSE).
