# deberka-jordan

[![PyPI](https://img.shields.io/pypi/v/deberka-jordan.svg)](https://pypi.org/project/deberka-jordan/)
[![Python](https://img.shields.io/pypi/pyversions/deberka-jordan.svg)](https://pypi.org/project/deberka-jordan/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](https://github.com/89605502155/deberka-jordan/blob/main/LICENSE)

**Reallocation plans for a shared resource from the Hahn–Jordan decomposition.**

A reallocation cycle among consumers of one pool (memory of a host, CPU quota,
bandwidth) is a signed measure on the set "pool and consumers". deberka-jordan
computes:

* the Hahn decomposition of the cycle: donors and recipients;
* the Jordan plan, the netting of all proposals of a cycle with the least
  volume of operations, `W = Σ |ν({i})|`;
* a safe two-phase order (donors first, then recipients) that never overdraws
  the pool, and an executor that waits for the memory actually freed;
* the oscillation index `κ` of a controller on the time axis and a dead band `h`
  chosen by the replay of a demand trace.

The first target is KVM memory ballooning through libvirt; nothing in the core
is specific to it.

Русская версия: [README.ru.md](https://github.com/89605502155/deberka-jordan/blob/main/README.ru.md).
Documentation: [English](https://github.com/89605502155/deberka-jordan/tree/main/docs/en) ·
[Русский](https://github.com/89605502155/deberka-jordan/tree/main/docs/ru) ·
[Changelog](https://github.com/89605502155/deberka-jordan/blob/main/CHANGELOG.md) ·
[Issues](https://github.com/89605502155/deberka-jordan/issues)

The library accompanies article 2 of the series by Andrey Ferubko, Bryansk State
Engineering-Technological University (BGITU). Theory:
[docs/en/theory.md](https://github.com/89605502155/deberka-jordan/blob/main/docs/en/theory.md).

## Installation

```sh
pip install deberka-jordan                # core: no dependencies
pip install "deberka-jordan[kvm]"         # plus libvirt-python for live domains
```

Requires Python 3.11 or newer.

## Quick start

```python
from deberka_jordan import SignedMeasure, jordan_plan, min_pool, netting_report
from deberka_jordan import recipients_first, two_phase

nu = SignedMeasure({"a": 3.0, "b": -1.0, "c": -2.0})
print(nu.total(), nu.total_variation())  # 0.0 6.0

current = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}  # MiB
target = {"vm1": 2600.0, "vm2": 2500.0, "vm3": 1530.0, "vm4": 2100.0}
plan = jordan_plan(current, target, pool_free=100.0, deadband=64.0)
print(plan.volume)  # 1500.0 MiB of operations
print(min_pool(two_phase(plan), 100.0))  # 100.0: the pool never goes below its start
print(min_pool(recipients_first(plan), 100.0))  # -500.0: the wrong order overdraws it

report = netting_report([("vm1", "vm2", 300.0), ("vm2", "vm3", 300.0), ("vm3", "vm1", 100.0)])
print(report.sequential_volume, report.jordan_volume)  # 1400.0 400.0
```

Command line, on a state file with the columns `consumer,current,target`:

    deberka-jordan plan state.csv --pool 100 --deadband 64
    deberka-jordan net proposals.csv --out netting.csv
    deberka-jordan deadband trace.csv --h 0,64,128 --reserve 256

## How it differs from existing packages

The Hahn and Jordan decompositions are classical measure theory (Halmos, §28–29).
PyPI has packages for matrices and for topological data analysis that carry the
same names, and none of them does what this library does:

* `jordan-form` computes the Jordan normal form of a matrix, a different object;
* `multipers` works with persistence modules in topological data analysis.

Packages for resource allocation (quota schedulers, job placement) pick targets,
they do not net a cycle of proposals into the least volume of operations, and
they do not give a safe order of operations for a pool.

| Feature | deberka-jordan | `jordan-form`, `multipers`, allocation schedulers |
|---|---|---|
| Hahn and Jordan decompositions of a finite signed measure on consumers and a pool | yes | no |
| Least-volume netting of a cycle, `W = Σ |ν({i})|`, with the sequential baseline | yes | no |
| Safe two-phase order that never overdraws the pool, with an executor that waits for freed memory | yes | no |
| Oscillation index `κ` and dead band `h` chosen on a demand trace | yes | no |
| Libvirt balloon backend (optional) | yes | no |

## Modules

| Module | Contents |
|---|---|
| `measure` | `SignedMeasure`, `HahnDecomposition`, `JordanDecomposition` |
| `plan` | `jordan_plan`, `Plan`, `ration`, netting: `netting_report`, `netting_by_cycle` |
| `order` | `two_phase`, `recipients_first`, `shuffled`, `pairwise`, `min_pool`, `is_safe` |
| `execute` | `execute_two_phase`, `execute_simultaneous`, `RateLimitedSim` |
| `churn` | `kappa`, `replay_reserve`, `deadband_sweep`, `choose_deadband`, `cycles_bound` |
| `kvm` | `LibvirtBackend`, `host_mem_available` (optional, needs libvirt-python) |

## When it helps

The numbers of the article are measured on the testbed and are not in this
package. The examples show the mechanisms on small inputs:
`examples/02_netting_log.py` (a ring of proposals nets 74 % of the volume, a
fan-out does not net at all) and `examples/03_two_phase_fake.py` (the executor
moves memory in the safe order).

## Development

```sh
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy
uv run pytest
bash scripts/install_hooks.sh   # once per clone: commit message limits
```

Commit messages in this repository have a subject of at most 8 characters and no
body. The hook is installed by `scripts/install_hooks.sh`; CI checks the same rule
with `scripts/check_commit_msg.py`.

## Citation

See [CITATION.cff](https://github.com/89605502155/deberka-jordan/blob/main/CITATION.cff)
or the "Cite this repository" button on GitHub.

## License

MIT. Copyright (c) 2026 Andrey Ferubko. See [LICENSE](https://github.com/89605502155/deberka-jordan/blob/main/LICENSE).
