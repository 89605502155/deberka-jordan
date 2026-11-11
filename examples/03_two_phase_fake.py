"""Two-phase execution against a fake libvirt-like backend (no host needed).

``LibvirtBackend`` takes any object with ``memoryStats()`` and
``setMemoryFlags()``. Here two fake domains change their balloon at once, so the
example runs in milliseconds and shows the safe order of operations.

Run: uv run python examples/03_two_phase_fake.py
"""

from deberka_jordan import execute_two_phase, jordan_plan
from deberka_jordan.kvm import LibvirtBackend


class FakeDomain:
    """Balloon that reaches the requested size at once."""

    def __init__(self, mib: float) -> None:
        self.kib = round(mib * 1024)

    def memoryStats(self) -> dict[str, int]:  # noqa: N802 - libvirt API name
        return {"actual": self.kib}

    def setMemoryFlags(self, kib: int, flags: int) -> None:  # noqa: N802
        self.kib = kib


domains = {"vm1": FakeDomain(2048.0), "vm2": FakeDomain(1024.0), "vm3": FakeDomain(1024.0)}
backend = LibvirtBackend(domains, pool=lambda: 128.0)
current = backend.snapshot()
plan = jordan_plan(current, {"vm1": 1536.0, "vm2": 1536.0}, backend.pool_free())
report = execute_two_phase(backend, plan, current, timeout_s=1.0)
print(f"donors {sorted(plan.donors)}, recipients {sorted(plan.recipients)}")
print(f"volume {plan.volume:.0f} MiB, pool peak {plan.peak:.0f} MiB, rationed {report.rationed}")
print("final shares:", {name: round(d.kib / 1024) for name, d in domains.items()})
