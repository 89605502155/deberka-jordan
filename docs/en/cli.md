# Command line

The program is `deberka-jordan`. Its subcommands are `plan`, `net` and `deadband`.

    deberka-jordan --version

## `plan`

Builds the Jordan plan of one cycle and checks the order of operations. The
input is a CSV file with the columns `consumer,current,target` (MiB).

    deberka-jordan plan state.csv --pool 100 --deadband 64

Prints a JSON object with `donors`, `recipients`, `skipped`, `take`, `give`,
`volume`, `pool_before`, `pool_peak`, `pool_after`, `rationed`,
`min_pool_two_phase`, `min_pool_recipients_first`, and the phase lists `phase1`
and `phase2`.

| Option | Meaning | Default |
|---|---|---|
| `--pool` | free pool before the cycle, MiB | required |
| `--deadband` | changes below this size are skipped, MiB | 0 |

## `net`

Netting gain per cycle for a proposal log with the columns
`cycle,source,recipient,amount` (`donor` and `amount_mib` are accepted as aliases).

    deberka-jordan net proposals.csv --out netting.csv

Prints a summary JSON: number of cycles, sequential and Jordan volumes, the overall
gain and the median ratio. `--out` writes one row per cycle.

## `deadband`

Replays a reserve controller with several dead bands on a demand trace. The trace
is a wide CSV with the column `t_s` (a uniform grid) and one column per consumer.

    deberka-jordan deadband trace.csv --h 0,64,128 --reserve 256 --theta 64 --out sweep.csv

| Option | Meaning | Default |
|---|---|---|
| `--h` | comma separated dead bands, MiB | `0,8,16,32,64,96,128,192,256` |
| `--reserve` | reserve above demand, MiB | 256 |
| `--interval` | monitoring interval, s | the trace step |
| `--theta` | deficit threshold, MiB | 64 |
| `--window` | oscillation window, s | 60 |
| `--kappa-target` | target median `κ` for the choice | 0.5 |
| `--out` | CSV with one row per dead band | none |

The table ends with the chosen dead band: the smallest one whose median index does
not exceed the target. The exit status is 0 on success.
