"""claude 스트림 실행기 — rate_limit_event 도착 즉시 원장 기록(값이 바뀐 경우만), 관측 시각 노출."""
import sys
import time

from scripts.autopilot import ledger, settings, stream
from scripts.console import overview


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "STATE_DIR", tmp_path)
    monkeypatch.setattr(settings, "LEDGER_PATH", tmp_path / "ledger.jsonl")


def test_append_observation_dedupes_unchanged(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    rl = {"rateLimitType": "five_hour", "utilization": 0.3, "status": "allowed", "resetsAt": 9e9}
    assert ledger.append_observation(rl, "u") is True
    assert ledger.append_observation(dict(rl), "u") is False
    assert ledger.append_observation({**rl, "utilization": 0.4}, "u") is True
    assert ledger.append_observation({**rl, "rateLimitType": "seven_day"}, "u") is True
    assert len(ledger.read_all()) == 3


def test_stream_run_records_observation_before_exit(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    ev = '{"type":"rate_limit_event","rate_limit_info":{"rateLimitType":"five_hour","utilization":0.5,"resetsAt":9000000000}}'
    code = f"import sys,time; print({ev!r}); sys.stdout.flush(); time.sleep(0.2); print('{{\"type\":\"result\"}}')"
    out, rc, timed_out = stream.run([sys.executable, "-c", code], 10, unit_id="U-1")
    assert (rc, timed_out) == (0, False) and "result" in out
    es = ledger.read_all()
    assert es[0]["unit_id"] == "U-1" and es[0]["rate_limit"]["utilization"] == 0.5


def test_stream_run_timeout_kills(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    out, rc, timed_out = stream.run([sys.executable, "-c", "import time; time.sleep(30)"], 0.5)
    assert (rc, timed_out) == (-1, True)


def test_budget_summary_exposes_observed_at():
    now = time.time()
    es = [{"ts": now - 120, "rate_limit": {"rateLimitType": "five_hour", "utilization": 0.1, "resetsAt": now + 3600}}, {"ts": now - 10}]
    assert overview.budget_summary(now, es)["observed_at"] == now - 120
