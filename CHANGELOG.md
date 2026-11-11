# Changelog

## 0.1.0 — 2026-11-11

First release: the reallocation plans of article 2 (A. Ferubko, BGITU). The project was
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
