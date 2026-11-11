"""KVM/libvirt backend: memory ballooning of virtual machines.

Units are MiB. The free pool of the host is ``MemAvailable`` from
``/proc/meminfo``. Requires ``libvirt-python``:
``pip install "deberka-jordan[kvm]"``.

Example::

    from deberka_jordan import jordan_plan, execute_two_phase
    from deberka_jordan.kvm import LibvirtBackend

    be = LibvirtBackend.connect("qemu:///system", ["vm1", "vm2", "vm3"])
    cur = be.snapshot()
    plan = jordan_plan(cur, {"vm1": 2600, "vm2": 2500}, be.pool_free(), deadband=64)
    report = execute_two_phase(be, plan, cur, timeout_s=60)
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Any

VIR_DOMAIN_AFFECT_LIVE = 1
"""Value of ``libvirt.VIR_DOMAIN_AFFECT_LIVE``."""


def host_mem_available(meminfo: str | Path = "/proc/meminfo") -> float:
    """``MemAvailable`` of the host, MiB."""
    with Path(meminfo).open(encoding="ascii") as fh:
        for line in fh:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024.0
    msg = f"no MemAvailable in {meminfo}"
    raise RuntimeError(msg)


class LibvirtBackend:
    """Balloon targets of live libvirt domains.

    ``domains`` maps a name to a ``libvirt.virDomain`` (or any object with
    ``memoryStats()`` and ``setMemoryFlags()``). ``pool`` returns the free
    pool in MiB. By default it reads ``MemAvailable`` of the host.
    """

    def __init__(self, domains: Mapping[str, Any], pool: Any = None) -> None:
        self.domains = dict(domains)
        self._pool = pool or host_mem_available

    @classmethod
    def connect(
        cls, uri: str = "qemu:///system", names: Iterable[str] | None = None
    ) -> LibvirtBackend:
        """Open a libvirt connection and take the given (or all active) domains."""
        try:
            import libvirt
        except ImportError as exc:  # pragma: no cover - depends on the host
            msg = 'install libvirt-python: pip install "deberka-jordan[kvm]"'
            raise ImportError(msg) from exc
        conn = libvirt.open(uri)
        if names is None:
            active = conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)
            doms = {d.name(): d for d in active}
        else:
            doms = {n: conn.lookupByName(n) for n in names}
        return cls(doms)

    def now(self) -> float:
        """Monotonic time, seconds."""
        return time.monotonic()

    def get_actual(self, consumer: str) -> float:
        """Balloon ``actual`` of the domain, MiB."""
        return float(self.domains[consumer].memoryStats()["actual"]) / 1024.0

    def set_target(self, consumer: str, target: float) -> None:
        """Request a new share; the actuator moves towards it at its own pace."""
        self.domains[consumer].setMemoryFlags(round(target * 1024), VIR_DOMAIN_AFFECT_LIVE)

    def pool_free(self) -> float:
        """Free pool of the host, MiB."""
        return float(self._pool())

    def snapshot(self) -> dict[str, float]:
        """Return the current balloon ``actual`` of all domains, MiB."""
        return {n: self.get_actual(n) for n in self.domains}

    def sleep(self, dt: float) -> None:
        """Wait ``dt`` seconds; a simulator advances its clock."""
        time.sleep(dt)
