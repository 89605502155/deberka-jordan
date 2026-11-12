# Theory

This page states the claims of article 2 and the conditions under which they
hold. The numbering follows the article. Status: *elementary* means a proof of
two or three lines; *sketch* means the argument is given here and the full
proof is to be written in the article.

## 1. A reallocation cycle as a signed measure

Let `X = {pool, consumer_1, …, consumer_N}`, where `pool` is the free capacity
of the shared resource. A cycle `a → a'` defines the atom values
`ν({i}) = a'_i − a_i` for consumers and `ν({pool}) = −Σ_i ν({i})`, so that
`ν(X) = 0`. Then `ν` is a signed measure with finitely many atoms (Halmos,
*Measure Theory*, §28).

By the Hahn theorem (§29) the set `X` splits into a positive part (recipients)
and a negative part (donors). The Jordan decomposition gives `ν = ν⁺ − ν⁻` with
mutually singular non-negative parts, and the total variation `|ν| = ν⁺ + ν⁻`.
In the library: `SignedMeasure.hahn()`, `SignedMeasure.jordan()`.

## 2. Claim 2.1: the lower bound on volume (elementary)

Any sequence of operations that moves the shares from `a` to `a'` has volume at
least

    W = Σ_{i ≥ 1} |a'_i − a_i|    (balloon operations, factor 2)

Proof: for each consumer the volume of its operations is at least the absolute
value of its net change, by the triangle inequality. The bound is attained when
every consumer only gives or only receives. The Jordan plan does exactly that: it
nets all proposals of the cycle per consumer and executes only the net change.
The plan has `Plan.operations = Σ |ν({i})|` balloon operations; in bytes, the
default unit, its volume is `Plan.volume = plan_volume(plan)` with the default pool mode
`max`: `max(take, give)`. It equals `Σ |ν({i})| / 2` when the pool does not change. The proposals executed
one by one cost `2 Σ amount` operations, that is `Σ amount` bytes, so the gain is
`1 − W / W_seq` (`netting_report`).

### The unit: bytes by default

A byte moved from a donor to a recipient is two balloon operations: the donor's
balloon deflates (it releases the byte) and the recipient's balloon inflates (it
takes the byte). The volume is reported in bytes by default (`factor=1`, each
transferred byte counted once). `factor=2` gives the balloon operations, the unit
of `W` as first stated. The factor only sets the unit: it scales the sequential
and the Jordan volume alike (`plan_volume` and `netting_report` use
`(factor / 2) Σ |net|`), so the gain `1 − W / W_seq` does not depend on it. A plan
that leaves the pool unchanged moves `Σ |net| / 2` bytes, so its volume in bytes is
exactly `Σ |ν| / 2`.

A byte moved into or out of the pool is one balloon operation, while a byte moved
between consumers is two. The volume must therefore say how a pool byte counts
(the `pool` argument of `plan_volume`):

* `pool="max"` (default): `factor · max(take, give)`. Every byte moved, between
  consumers or into or out of the pool, counts once. This is the number of bytes
  moved, and it is the article's choice.
* `pool="weighted"`: `factor · (min(take, give) + pool_weight · |take − give|)` with
  `pool_weight = 0.5` by default. At `factor=2` this is `Σ |ν|`, the balloon
  operations; earlier versions used it.

Both modes coincide for a plan that does not change the pool, and the gain
`1 − W / W_seq` does not depend on the mode. Netting logs contain transfers between
consumers only, so `netting_report` has no pool term.

## 3. Claim 2.2: the safe order (elementary)

Let the pool be non-negative before and after the cycle. Execute all donors
first and all recipients after them. The pool first only grows (by the amounts
taken from donors), then decreases monotonically to its final value. So its
lowest level is `min(pool_before, pool_after) ≥ 0`. Other orders can overdraw it:
recipients first gives a minimum of `pool_before − Σ recipients`.

Limit of practice: inflating a balloon has finite speed. Therefore the executor
`execute_two_phase` waits until donors have actually freed memory (with a
timeout), and then grants recipients no more than the freed amount plus the free
pool. If donors fall short, recipients are rationed (`ration`). Tests check that
the pool never goes below zero when the backend is feasible.

`jordan_plan` guarantees the budget `pool_free + take ≥ give` by rationing, so
the plan itself is safe under the instantaneous model.

## 4. Oscillation index on the time axis

The share `a_i(t)` is a step function. Its jumps form the atomic measure `ξ_i` on
the time axis. In a window `W`:

* `|ξ_i|(W)` is the total variation: the volume of operations;
* `ξ_i(W)` is the net change;
* `κ_i(W) = 1 − |ξ_i(W)| / |ξ_i|(W)` is the oscillation index.

`κ` is 0 when the share moves in one direction and tends to 1 when it swings
back and forth. `kappa`, `window_stats` and `kappa_series` compute it.

## 5. Claim 2.3: the dead band (elementary)

Let the controller keep the target `d + s` and execute a change only when
`|target − a| > h`, or when the consumer is short (`a < d`). Let `s ≥ h`. Then
the number of jumps of a consumer is at most `V / h` and their total volume is at
most `V`, where `V = Σ |d_k − d_{k−1}|` is the variation of the observed demand.

Why the short-consumer rule does not break the count: after a jump the share is
`d + s`. A consumer becomes short only after its demand has grown by at least
`s ≥ h` since that jump. So every jump is paid for by at least `h` of demand
variation. The bound is `cycles_bound`; the replay checks it on the trace.

## 6. Choosing the dead band

`deadband_sweep` replays the controller for several values of `h`, and
`choose_deadband` returns the smallest `h` whose median oscillation index does
not exceed the target. A larger `h` reduces jumps and the oscillation index, but
it also lets the share lag behind demand. The replay reports the deficit integral
and its share, so the trade-off can be seen before a value is chosen.

## 7. Limits

- The theory is for an instantaneous actuator; `RateLimitedSim` and the executors
  model the finite speed of the balloon.
- A dead band removes changes from the plan. The skipped changes are reported in
  `Plan.skipped`, and the pool atom absorbs them, so the plan is not zero-sum when
  they are present.
- Rationing changes the recipients' amounts, not the donors'. The plan reports
  `rationed = True` in that case.
- The claims are about one cycle. Their effect over many cycles is what the
  experiments of the article measure.
