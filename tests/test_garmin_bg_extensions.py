"""웹 bg_sync 확장 동기화 — 호출 구성·최근 N일 제한·429 전파."""
from __future__ import annotations

import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables
from src.sync import garmin_bg_extensions as ext


class _TooMany(Exception):
    pass


class _Client:
    def __init__(self, fail_on: str | None = None):
        self.calls: list[tuple] = []
        self.fail_on = fail_on

    def _rec(self, name, *a):
        self.calls.append((name, *a))
        if name == self.fail_on:
            raise _TooMany("429")
        return {}

    def get_training_status(self, d): return self._rec("ts", d)
    def get_heart_rates(self, d): return self._rec("hr", d)
    def get_race_predictions(self): return self._rec("rp")
    def get_lactate_threshold(self): return self._rec("lt")


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(tmp_path / "t.db")
    create_tables(c)
    return c


@pytest.fixture(autouse=True)
def _patch(monkeypatch):
    monkeypatch.setattr(ext, "_429_type", lambda: _TooMany)


def test_window_with_today_calls_snapshots_and_daily(conn):
    cl = _Client()
    n = ext.sync_bg_extensions(conn, cl, "2026-11-16", "2026-11-17", today=date(2026, 11, 17), sleep=lambda s: None)
    assert n == 2 + 2 * 2
    assert [c[0] for c in cl.calls] == ["rp", "lt", "ts", "hr", "ts", "hr"]


def test_old_window_is_skipped_beyond_recent_days(conn):
    cl = _Client()
    n = ext.sync_bg_extensions(conn, cl, "2025-01-01", "2025-03-01", today=date(2026, 11, 17), sleep=lambda s: None)
    assert n == 0 and cl.calls == []


def test_window_partly_recent_is_clamped_without_snapshots(conn):
    cl = _Client()
    n = ext.sync_bg_extensions(conn, cl, "2026-10-01", "2026-10-20", today=date(2026, 11, 17), sleep=lambda s: None)
    assert n == 2 * 3  # 10-18 이후 부분만(10-18~10-20), 오늘 미포함이라 스냅샷 없음
    assert all(c[0] in ("ts", "hr") for c in cl.calls)


@pytest.mark.parametrize("name", ["rp", "ts", "hr"])
def test_429_propagates_even_though_inner_sync_swallows(conn, name):
    cl = _Client(fail_on=name)
    with pytest.raises(_TooMany):
        ext.sync_bg_extensions(conn, cl, "2026-11-17", "2026-11-17", today=date(2026, 11, 17), sleep=lambda s: None)
