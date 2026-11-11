"""Command line tool ``deberka-jordan``.

Subcommands:

* ``plan``     build the Jordan plan for a state CSV and check the order;
* ``net``      netting gain per cycle for a proposal log;
* ``deadband`` replay a reserve controller with dead bands on a demand trace.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
import sys
from collections.abc import Sequence

from . import __version__
from .churn import choose_deadband, deadband_sweep
from .csvio import read_proposals, read_state, read_trace, write_rows
from .order import min_pool, recipients_first, two_phase
from .plan import jordan_plan, netting_by_cycle, plan_volume


def _floats(text: str) -> list[float]:
    return [float(x) for x in text.split(",") if x.strip()]


def _factor(text: str) -> float:
    """Argparse type of ``--factor``: a finite positive number."""
    try:
        value = float(text)
    except ValueError:
        msg = f"factor must be a number, got {text!r}"
        raise argparse.ArgumentTypeError(msg) from None
    if not math.isfinite(value) or value <= 0.0:
        msg = f"factor must be finite and positive, got {text!r}"
        raise argparse.ArgumentTypeError(msg)
    return value


def _cmd_plan(args: argparse.Namespace) -> int:
    cur, tgt = read_state(args.state)
    p = jordan_plan(cur, tgt, args.pool, deadband=args.deadband)
    out = {
        "donors": p.donors,
        "recipients": p.recipients,
        "skipped": p.skipped,
        "take": p.take,
        "give": p.give,
        "volume": plan_volume(p, factor=args.factor),
        "volume_factor": args.factor,
        "pool_before": p.pool_before,
        "pool_peak": p.peak,
        "pool_after": p.pool_after,
        "rationed": p.rationed,
        "min_pool_two_phase": min_pool(two_phase(p), args.pool),
        "min_pool_recipients_first": min_pool(recipients_first(p), args.pool),
        "phase1": [[c, cur[c] - x] for c, x in p.donors.items()],
        "phase2": [[c, cur[c] + x] for c, x in p.recipients.items()],
    }
    json.dump(out, sys.stdout, indent=2, ensure_ascii=False)
    print()
    return 0


def _cmd_net(args: argparse.Namespace) -> int:
    reps = netting_by_cycle(read_proposals(args.log), factor=args.factor)
    rows = [
        {
            "cycle": r.cycle,
            "n_transfers": r.n_transfers,
            "seq_volume": r.sequential_volume,
            "jordan_volume": r.jordan_volume,
            "ratio": r.ratio,
        }
        for r in reps
    ]
    if args.out:
        write_rows(args.out, rows)
    ratios = [r.ratio for r in reps if r.sequential_volume > 0]
    seq = sum(r.sequential_volume for r in reps)
    jor = sum(r.jordan_volume for r in reps)
    summary = {
        "cycles": len(reps),
        "sequential_volume": seq,
        "jordan_volume": jor,
        "overall_gain": 1.0 - jor / seq if seq else 0.0,
        "volume_factor": args.factor,
        "median_ratio": statistics.median(ratios) if ratios else None,
    }
    json.dump(summary, sys.stdout, indent=2)
    print()
    return 0


def _cmd_deadband(args: argparse.Namespace) -> int:
    dt, demand = read_trace(args.trace)
    res = deadband_sweep(
        demand,
        dt,
        _floats(args.h),
        reserve=args.reserve,
        interval=args.interval,
        theta=args.theta,
        kappa_window=args.window,
    )
    rows = [
        {
            "h": r.h,
            "cycles": r.cycles,
            "jumps": len(r.jumps),
            "bound_V_over_h": r.bound,
            "volume": r.volume,
            "kappa_median": r.kappa_median,
            "deficit_integral": r.deficit_integral,
            "deficit_share": r.deficit_share,
        }
        for r in res
    ]
    if args.out:
        write_rows(args.out, rows)
    print("h\tcycles\tjumps\tbound\tvolume\tkappa\tdeficit_int\tdeficit_share")
    for r in rows:
        print("\t".join(f"{v:.4g}" if isinstance(v, float) else str(v) for v in r.values()))
    print(f"chosen h (kappa <= {args.kappa_target}): {choose_deadband(res, args.kappa_target)}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Run the command line and return the exit status."""
    ap = argparse.ArgumentParser(prog="deberka-jordan", description=__doc__.splitlines()[0])
    ap.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("plan", help="Jordan plan for a state CSV (consumer,current,target)")
    p.add_argument("state")
    p.add_argument("--pool", type=float, required=True, help="free pool before the cycle")
    p.add_argument("--deadband", type=float, default=0.0)
    p.add_argument(
        "--factor",
        type=_factor,
        default=2.0,
        help="balloon operations per byte moved between consumers (default 2)",
    )
    p.set_defaults(func=_cmd_plan)

    p = sub.add_parser(
        "net", help="netting gain for a proposal log (cycle,source,recipient,amount)"
    )
    p.add_argument("log")
    p.add_argument("--out", help="per-cycle CSV")
    p.add_argument(
        "--factor",
        type=_factor,
        default=2.0,
        help="balloon operations per byte moved between consumers (default 2)",
    )
    p.set_defaults(func=_cmd_net)

    p = sub.add_parser("deadband", help="dead band sweep on a demand trace (t_s,<consumers>)")
    p.add_argument("trace")
    p.add_argument("--h", default="0,8,16,32,64,96,128,192,256", help="comma separated")
    p.add_argument("--reserve", type=float, default=256.0)
    p.add_argument("--interval", type=float, default=None, help="monitoring interval, s")
    p.add_argument("--theta", type=float, default=64.0, help="deficit threshold")
    p.add_argument("--window", type=float, default=60.0, help="kappa window, s")
    p.add_argument("--kappa-target", type=float, default=0.5)
    p.add_argument("--out", help="CSV with one row per dead band")
    p.set_defaults(func=_cmd_deadband)

    args = ap.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
