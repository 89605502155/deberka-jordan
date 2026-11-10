"""CSV formats used by the command line tool.

* Proposal log: columns ``cycle, source, recipient, amount``
  (``donor`` is accepted for ``source``, ``amount_mib`` for ``amount``).
* State: columns ``consumer, current, target``.
* Demand trace (wide): column ``t_s`` and one column per consumer, uniform grid.
"""

from __future__ import annotations

import csv
import itertools
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

_ALIASES = {"donor": "source", "amount_mib": "amount", "vm": "consumer"}


def _rows(path: str | Path) -> list[dict[str, str]]:
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        rows = []
        for raw in reader:
            rows.append({_ALIASES.get(k.strip(), k.strip()): (v or "").strip()
                         for k, v in raw.items() if k is not None})
        return rows


def _need(rows: list[dict[str, str]], cols: Iterable[str], path: str | Path) -> None:
    if rows:
        missing = [c for c in cols if c not in rows[0]]
        if missing:
            raise ValueError(f"{path}: missing columns {missing}")


def read_proposals(path: str | Path) -> list[tuple[str, str, str, float]]:
    rows = _rows(path)
    _need(rows, ["cycle", "source", "recipient", "amount"], path)
    return [(r["cycle"], r["source"], r["recipient"], float(r["amount"])) for r in rows]


def read_state(path: str | Path) -> tuple[dict[str, float], dict[str, float]]:
    rows = _rows(path)
    _need(rows, ["consumer", "current", "target"], path)
    cur = {r["consumer"]: float(r["current"]) for r in rows}
    tgt = {r["consumer"]: float(r["target"]) for r in rows if r["target"] != ""}
    return cur, tgt


def read_trace(path: str | Path) -> tuple[float, dict[str, list[float]]]:
    """Return ``(dt, {consumer: samples})``. The time grid must be uniform."""
    with open(path, newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    header, body = rows[0], [r for r in rows[1:] if r]
    if header[0].strip() != "t_s":
        raise ValueError(f"{path}: the first column must be t_s")
    if len(body) < 2:
        raise ValueError(f"{path}: need at least two samples")
    t = [float(r[0]) for r in body]
    steps = [b - a for a, b in itertools.pairwise(t)]
    dt = sorted(steps)[len(steps) // 2]
    if dt <= 0 or max(abs(s - dt) for s in steps) > 1e-5 + 1e-6 * dt:
        raise ValueError(f"{path}: the time grid is not uniform, resample the trace first")
    names = [h.strip() for h in header[1:]]
    return dt, {n: [float(r[j + 1]) for r in body] for j, n in enumerate(names)}


def write_rows(path: str | Path, rows: Sequence[Mapping[str, Any]]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as fh:
        if not rows:
            return
        w = csv.DictWriter(fh, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
