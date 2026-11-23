"""audit.procs 레지스트리와 audit.cycle 스킵 판정."""
import json
import subprocess
import sys
import time

from scripts.audit import cycle, procs


def test_reap_kills_only_registered_matching(tmp_path, monkeypatch):
    monkeypatch.setattr(procs, "PROCS_PATH", tmp_path / "procs.json")
    reg = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)  # marker_reg"])
    other = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)  # marker_other"])
    try:
        procs.register(reg.pid, "marker_reg")
        procs.register(other.pid, "wrong_tag")        # 태그 불일치(PID 재사용 가정) — 건드리지 않음
        time.sleep(0.3)
        assert procs.reap() == [reg.pid]
        reg.wait(timeout=5)
        assert other.poll() is None
        assert json.loads((tmp_path / "procs.json").read_text()) == {}
    finally:
        other.kill()
        other.wait()


def test_cycle_skips_below_min_interval(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "CYCLES_PATH", tmp_path / "cycles.jsonl")
    monkeypatch.setattr(cycle.pacing, "check", lambda now: cycle.pacing.Pacing(True))
    now = time.time()
    (tmp_path / "cycles.jsonl").write_text(json.dumps({"ts": now - 60, "ran": True}) + "\n")
    assert "최소 간격" in cycle.skip_reason(now)
    assert cycle.skip_reason(now, force=True) is None
    assert cycle.skip_reason(now + 3 * 3600) is None


def test_cycle_logs_skip_when_pacing_blocks(tmp_path, monkeypatch):
    monkeypatch.setattr(cycle, "CYCLES_PATH", tmp_path / "cycles.jsonl")
    monkeypatch.setattr(cycle.pacing, "check", lambda now: cycle.pacing.Pacing(False, "세션 대기"))
    e = cycle.run_cycle()
    assert e["ran"] is False and e["reason"] == "세션 대기"
    assert "세션 대기" in (tmp_path / "cycles.jsonl").read_text()
