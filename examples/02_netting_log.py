"""Netting of a proposal log: the volume of the Jordan plan against one-by-one transfers.

The log has one row per proposal: ``cycle, source, recipient, amount``. The same
format is written by the command line tool ``deberka-jordan net``.

Run: uv run python examples/02_netting_log.py
"""

import csv
import tempfile
from pathlib import Path

from deberka_jordan import netting_by_cycle
from deberka_jordan.csvio import read_proposals

LOG = [
    # cycle 1: three guests pass memory around in a ring, nearly cancelling out
    ("c1", "vm1", "vm2", "300"),
    ("c1", "vm2", "vm3", "280"),
    ("c1", "vm3", "vm1", "120"),
    # cycle 2: one donor feeds two recipients, nothing to cancel
    ("c2", "vm4", "vm5", "200"),
    ("c2", "vm4", "vm6", "150"),
]

with tempfile.TemporaryDirectory() as tmp:
    path = Path(tmp) / "proposals.csv"
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["cycle", "source", "recipient", "amount"])
        writer.writerows(LOG)
    reports = netting_by_cycle(read_proposals(path))

for r in reports:
    print(
        f"{r.cycle}: {r.n_transfers} proposals, one by one {r.sequential_volume:.0f} MiB, "
        f"Jordan {r.jordan_volume:.0f} MiB, gain {r.gain:.0%}"
    )
