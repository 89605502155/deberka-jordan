"""LibvirtBackend driven by the two-phase executor, with fake domains (no libvirt needed)."""

import sys
from pathlib import Path

import pytest

from deberka_jordan import execute_two_phase, jordan_plan
from deberka_jordan.kvm import LibvirtBackend, host_mem_available


class FakeDomain:
    """Balloon with instant effect: ``actual`` jumps to the requested size."""

    def __init__(self, actual_mib: float) -> None:
        self.kib = round(actual_mib * 1024)
        self.calls: list[int] = []

    def memoryStats(self) -> dict[str, int]:
        return {"actual": self.kib}

    def setMemoryFlags(self, kib: int, flags: int) -> None:
        self.calls.append(kib)
        self.kib = kib


def test_snapshot_and_pool_come_from_the_domains() -> None:
    be = LibvirtBackend({"vm1": FakeDomain(2048.0), "vm2": FakeDomain(1024.0)}, pool=lambda: 512.0)
    assert be.snapshot() == {"vm1": 2048.0, "vm2": 1024.0}
    assert be.pool_free() == 512.0


def test_two_phase_on_fake_domains_respects_pool() -> None:
    doms = {"vm1": FakeDomain(2048.0), "vm2": FakeDomain(1024.0), "vm3": FakeDomain(1024.0)}
    be = LibvirtBackend(doms, pool=lambda: 128.0)
    current = be.snapshot()
    plan = jordan_plan(current, {"vm1": 1536.0, "vm2": 1536.0}, be.pool_free())
    report = execute_two_phase(be, plan, current, timeout_s=1.0)
    assert not report.unfinished
    assert not report.rationed
    assert doms["vm1"].kib == 1536 * 1024
    assert doms["vm2"].kib == 1536 * 1024
    assert doms["vm3"].kib == 1024 * 1024  # untouched
    # the donor was reclaimed first, then the recipient was granted
    assert doms["vm1"].calls[0] < doms["vm1"].calls[-1] or len(doms["vm1"].calls) == 1


def test_targets_are_in_kib_and_rounded() -> None:
    dom = FakeDomain(100.0)
    be = LibvirtBackend({"vm": dom})
    be.set_target("vm", 100.5)
    assert dom.calls == [round(100.5 * 1024)]
    assert be.get_actual("vm") == pytest.approx(100.5)


def test_host_mem_available_reads_meminfo(tmp_path: Path) -> None:
    info = tmp_path / "meminfo"
    info.write_text("MemTotal:       8192000 kB\nMemAvailable:    2048 kB\n", encoding="ascii")
    assert host_mem_available(info) == pytest.approx(2.0)


def test_host_mem_available_fails_loudly(tmp_path: Path) -> None:
    info = tmp_path / "meminfo"
    info.write_text("MemTotal:       8192000 kB\n", encoding="ascii")
    with pytest.raises(RuntimeError, match="MemAvailable"):
        host_mem_available(info)
    with pytest.raises(FileNotFoundError):
        host_mem_available(tmp_path / "absent")


def test_connect_without_libvirt_explains_the_extra(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setitem(sys.modules, "libvirt", None)
    with pytest.raises(ImportError, match="deberka-jordan\\[kvm\\]"):
        LibvirtBackend.connect()
