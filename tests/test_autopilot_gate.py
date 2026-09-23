"""tests/test_autopilot_gate.py — gate.check()의 ignore_budget 옵션 테스트."""
from __future__ import annotations

import time

from scripts.autopilot import gate, ledger, settings


def _write_ledger(tmp_path, monkeypatch, entries: list[dict]) -> None:
    ledger_path = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(settings, "LEDGER_PATH", ledger_path)
    monkeypatch.setattr(settings, "STOP_PATH", tmp_path / "STOP")
    monkeypatch.setattr(settings, "PAUSE_PATH", tmp_path / "PAUSE")
    for e in entries:
        ledger.append(e)


def test_ignore_budget_false_blocks_when_over_daily_cap(tmp_path, monkeypatch):
    _write_ledger(tmp_path, monkeypatch, [
        {"ts": time.time(), "cost_usd": settings.DAILY_MAX_USD + 1, "outcome": "success"},
    ])
    result = gate.check(ignore_night_window=True, ignore_idle=True, ignore_budget=False)
    assert result.allowed is False
    assert "예산" in result.reason


def test_ignore_budget_true_skips_budget_check(tmp_path, monkeypatch):
    _write_ledger(tmp_path, monkeypatch, [
        {"ts": time.time(), "cost_usd": settings.DAILY_MAX_USD + 1, "outcome": "success"},
    ])
    result = gate.check(ignore_night_window=True, ignore_idle=True, ignore_budget=True)
    assert result.allowed is True
