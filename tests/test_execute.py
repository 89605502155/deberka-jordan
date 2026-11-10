import pytest

from jordanplan import Backend, RateLimitedSim, execute_simultaneous, execute_two_phase, jordan_plan
from jordanplan.kvm import LibvirtBackend, host_mem_available

CUR = {"vm1": 2000.0, "vm2": 3000.0, "vm3": 1500.0, "vm4": 2500.0}
NEW = {"vm1": 2800.0, "vm2": 2200.0}


def test_sim_is_a_backend():
    assert isinstance(RateLimitedSim(CUR, 0.0), Backend)


def test_two_phase_keeps_pool_and_reaches_targets():
    p = jordan_plan(CUR, NEW, pool_free=0.0)
    sim = RateLimitedSim(CUR, 0.0, take_rate=200.0, give_rate=800.0)
    rep = execute_two_phase(sim, p, CUR, timeout_s=30.0)
    assert rep.pool_min is not None and rep.pool_min >= -1.0
    assert rep.given["vm1"] == pytest.approx(800.0, abs=1.0)
    assert not rep.unfinished and not rep.rationed
    # 800 MiB at 200 MiB/s, then 800 MiB at 800 MiB/s
    assert rep.duration_s == pytest.approx(5.0, abs=0.3)


def test_two_phase_uses_actually_freed_memory():
    p = jordan_plan(CUR, NEW, pool_free=0.0)
    sim = RateLimitedSim(CUR, 0.0, reclaimable={"vm2": 500.0})
    rep = execute_two_phase(sim, p, CUR, timeout_s=10.0)
    assert rep.freed["vm2"] == pytest.approx(500.0, abs=1.0)
    assert rep.given["vm1"] == pytest.approx(500.0, abs=1.0)
    assert rep.rationed and "vm2" in rep.unfinished
    assert sim.pool_min >= -1.0


def test_simultaneous_overdraws():
    p = jordan_plan(CUR, NEW, pool_free=0.0)
    sim = RateLimitedSim(CUR, 0.0)
    rep = execute_simultaneous(sim, p, CUR, timeout_s=10.0)
    assert rep.pool_min is not None and rep.pool_min < -100.0


def test_sim_validation():
    with pytest.raises(ValueError):
        RateLimitedSim(CUR, 0.0, take_rate=0.0)


class FakeDomain:
    def __init__(self, kib: int) -> None:
        self.kib = kib

    def memoryStats(self):
        return {"actual": self.kib}

    def setMemoryFlags(self, kib, flags):
        assert flags == 1
        self.kib = kib


def test_libvirt_backend_units(tmp_path):
    mi = tmp_path / "meminfo"
    mi.write_text("MemTotal: 8000000 kB\nMemAvailable: 2097152 kB\n")
    assert host_mem_available(mi) == 2048.0
    be = LibvirtBackend({"vm": FakeDomain(1024 * 1024)}, pool=lambda: 100.0)
    assert be.snapshot() == {"vm": 1024.0}
    be.set_target("vm", 512.5)
    assert be.get_actual("vm") == 512.5
    assert be.pool_free() == 100.0
    assert isinstance(be, Backend)
