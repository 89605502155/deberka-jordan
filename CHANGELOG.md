# Changelog

## 0.1.0

First release.

- `SignedMeasure` with Hahn and Jordan decompositions.
- `jordan_plan`: least-volume plan with dead band, bounds and rationing.
- Netting of proposal logs: `netting_report`, `netting_by_cycle`.
- Orders and the pool invariant: `two_phase`, `recipients_first`, `shuffled`, `pairwise`.
- Executors `execute_two_phase`, `execute_simultaneous`, simulator `RateLimitedSim`.
- Oscillation index, `replay_reserve`, `deadband_sweep`, `choose_deadband`.
- Optional `jordanplan.kvm.LibvirtBackend`.
- Command line tool `jordanplan`.
