# Changelog

## [0.0.1] — 2026-11-11

First release: the reallocation plans of article 2 (A. Ferubko, O. Kazakov, BGITU). The project was
built under the working name `jordanplan-deberka` (module `jordanplan`) and renamed to
`deberka-jordan` (module `deberka_jordan`, command `deberka-jordan`) before publication.

- `SignedMeasure` with Hahn and Jordan decompositions.
- `jordan_plan`: least-volume plan with dead band, bounds and rationing.
- Netting of proposal logs: `netting_report`, `netting_by_cycle`.
- Orders and the pool invariant: `two_phase`, `recipients_first`, `shuffled`, `pairwise`.
- Executors `execute_two_phase`, `execute_simultaneous`, simulator `RateLimitedSim`.
- Oscillation index, `replay_reserve`, `deadband_sweep`, `choose_deadband`.
- Optional `deberka_jordan.kvm.LibvirtBackend`, tested with fake domains.
- Command line tool `deberka_jordan`.
- Volume unit (default 1, bytes): `sequential_volume`, `netting_report`, `netting_by_cycle`
  take `factor`, and `plan_volume(plan, *, factor=1.0)` is the volume of a plan. The default
  `factor=1` counts each byte moved between two consumers once; `factor=2` gives the balloon
  operations (an inflation at the donor and a deflation at the recipient). Must be finite and
  positive (`ValueError`), a number (`TypeError`). The gain does not depend on it.
- `Plan.volume` is `plan_volume(plan)` with the default `pool="max"`: `max(take, give)`, the
  bytes moved (equal to `Plan.operations / 2` when the pool does not change).
  `Plan.operations = Σ |ν({i})|` is the balloon-operation measure of Claim 1.
  `lower_bound_volume` is that measure (operations).
- Command line `plan --factor` and `net --factor` (default 1); the JSON output adds
  `volume_factor`.
  The `deadband` volume is not scaled: a dead-band jump is one operation on one consumer.
- Pool term of the plan volume: `plan_volume(plan, *, factor=1.0, pool="max", pool_weight=0.5)`.
  `pool="max"` (default) counts a byte moved into or out of the pool as a byte:
  `factor · max(take, give)`. `pool="weighted"` gives `factor · (min(take, give) + pool_weight ·
  |pool change|)`; `pool_weight=0.5` reproduces the balloon operations over two of earlier
  versions. Errors: `pool` not a string (`TypeError`) or not in `("max", "weighted")`
  (`ValueError`); `pool_weight` not a real number (`TypeError`) or not finite and
  non-negative (`ValueError`). For a plan that does not change the pool all modes coincide.
  `netting_report` has no pool term: its logs are transfers between consumers.
- Command line `plan --pool-mode {max,weighted}` (default `max`) and `--pool-weight W`
  (default 0.5); the `plan` output adds `volume_pool_mode` and `volume_pool_weight`. The
  free pool level stays `--pool`.
