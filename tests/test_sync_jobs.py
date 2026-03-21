"""sync_jobs / bg_sync 단위 테스트 — 실제 API 호출 없음 (임시 DB 사용)."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from src.utils.sync_jobs import (
    INTER_BATCH_SLEEP,
    RATE_LIMITS,
    WINDOW_DAYS,
    SyncJob,
    create_job,
    get_active_job,
    get_job,
    list_recent_jobs,
    update_job,
    windows,
)


# ── fixtures ─────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_db(tmp_path):
    """임시 DB — sync_jobs 테이블 생성."""
    db = tmp_path / "test.db"
    with sqlite3.connect(str(db)) as conn:
        conn.executescript("""
            CREATE TABLE sync_jobs (
                id TEXT PRIMARY KEY,
                service TEXT NOT NULL,
                from_date TEXT NOT NULL,
                to_date TEXT NOT NULL,
                window_days INTEGER NOT NULL,
                current_from TEXT,
                status TEXT NOT NULL DEFAULT 'pending',
                completed_days INTEGER NOT NULL DEFAULT 0,
                total_days INTEGER NOT NULL,
                synced_count INTEGER NOT NULL DEFAULT 0,
                req_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                retry_after TEXT,
                last_error TEXT
            );
        """)
    return db


@pytest.fixture(autouse=True)
def patch_db(tmp_db):
    """_conn()이 임시 DB를 가리키도록 패치."""
    with patch("src.utils.sync_jobs.get_db_path", return_value=tmp_db):
        yield


# ── windows() ────────────────────────────────────────────────────────────

class TestWindows:
    def test_single_window(self):
        result = windows("2025-01-01", "2025-01-10", 14)
        assert result == [("2025-01-01", "2025-01-10")]

    def test_exact_multiple(self):
        result = windows("2025-01-01", "2025-01-28", 14)
        assert len(result) == 2
        assert result[0] == ("2025-01-01", "2025-01-14")
        assert result[1] == ("2025-01-15", "2025-01-28")

    def test_remainder_window(self):
        result = windows("2025-01-01", "2025-01-20", 14)
        assert len(result) == 2
        assert result[0][1] == "2025-01-14"
        assert result[1] == ("2025-01-15", "2025-01-20")

    def test_single_day(self):
        result = windows("2025-06-15", "2025-06-15", 14)
        assert result == [("2025-06-15", "2025-06-15")]

    def test_90_day_garmin(self):
        result = windows("2025-01-01", "2025-04-01", 14)
        assert len(result) >= 6
        # 모든 창이 연속적인지 확인
        for i in range(len(result) - 1):
            prev_end = date.fromisoformat(result[i][1])
            next_start = date.fromisoformat(result[i + 1][0])
            assert next_start == prev_end + timedelta(days=1)

    def test_no_gap_no_overlap(self):
        """창들이 겹치거나 빠지는 날 없음."""
        result = windows("2025-03-01", "2025-06-30", 21)
        all_days = set()
        for wf, wt in result:
            d = date.fromisoformat(wf)
            while d <= date.fromisoformat(wt):
                assert d not in all_days, f"중복 날짜: {d}"
                all_days.add(d)
                d += timedelta(days=1)
        expected = {
            date.fromisoformat("2025-03-01") + timedelta(days=i)
            for i in range((date.fromisoformat("2025-06-30") - date.fromisoformat("2025-03-01")).days + 1)
        }
        assert all_days == expected


# ── SyncJob dataclass properties ─────────────────────────────────────────

class TestSyncJobProperties:
    def test_progress_pct_zero(self):
        job = _make_job(completed_days=0, total_days=100)
        assert job.progress_pct == 0.0

    def test_progress_pct_half(self):
        job = _make_job(completed_days=50, total_days=100)
        assert job.progress_pct == 50.0

    def test_progress_pct_capped(self):
        job = _make_job(completed_days=110, total_days=100)
        assert job.progress_pct == 100.0

    def test_progress_pct_zero_total(self):
        job = _make_job(completed_days=0, total_days=0)
        assert job.progress_pct == 0.0

    def test_current_to_within_range(self):
        job = _make_job(current_from="2025-01-01", window_days=14, to_date="2025-03-01")
        assert job.current_to == "2025-01-14"

    def test_current_to_capped_at_end(self):
        job = _make_job(current_from="2025-02-25", window_days=14, to_date="2025-03-01")
        assert job.current_to == "2025-03-01"

    def test_current_to_none_when_no_current_from(self):
        job = _make_job(current_from=None)
        assert job.current_to is None

    def test_rate_limit_known_service(self):
        job = _make_job(service="strava")
        assert job.rate_limit["per_15min"] == 100
        assert job.rate_limit["per_day"] == 1000

    def test_rate_limit_unknown_service(self):
        job = _make_job(service="unknown")
        assert job.rate_limit["per_15min"] == 50


# ── CRUD ─────────────────────────────────────────────────────────────────

class TestCRUD:
    def test_create_and_get(self):
        job = create_job("garmin", "2025-01-01", "2025-01-31")
        assert job.service == "garmin"
        assert job.from_date == "2025-01-01"
        assert job.to_date == "2025-01-31"
        assert job.status == "pending"
        assert job.total_days == 31
        assert job.window_days == WINDOW_DAYS["garmin"]

    def test_get_nonexistent_returns_none(self):
        assert get_job("nonexistent-id") is None

    def test_update_status(self):
        job = create_job("strava", "2025-01-01", "2025-01-14")
        update_job(job.id, status="running", current_from="2025-01-01")
        updated = get_job(job.id)
        assert updated.status == "running"
        assert updated.current_from == "2025-01-01"

    def test_update_progress(self):
        job = create_job("intervals", "2025-01-01", "2025-03-31")
        update_job(job.id, completed_days=30, synced_count=50, req_count=55)
        updated = get_job(job.id)
        assert updated.completed_days == 30
        assert updated.synced_count == 50
        assert updated.req_count == 55

    def test_get_active_job(self):
        job = create_job("garmin", "2025-01-01", "2025-01-31")
        active = get_active_job("garmin")
        assert active is not None
        assert active.id == job.id

    def test_get_active_job_none_after_completed(self):
        job = create_job("garmin", "2025-01-01", "2025-01-31")
        update_job(job.id, status="completed")
        assert get_active_job("garmin") is None

    def test_get_active_job_none_after_stopped(self):
        job = create_job("garmin", "2025-01-01", "2025-01-31")
        update_job(job.id, status="stopped")
        assert get_active_job("garmin") is None

    def test_get_active_job_paused_is_active(self):
        job = create_job("strava", "2025-01-01", "2025-01-31")
        update_job(job.id, status="paused")
        active = get_active_job("strava")
        assert active is not None

    def test_list_recent_jobs(self):
        create_job("garmin", "2025-01-01", "2025-01-31")
        create_job("garmin", "2025-02-01", "2025-02-28")
        jobs = list_recent_jobs("garmin")
        assert len(jobs) == 2
        from_dates = {j.from_date for j in jobs}
        assert from_dates == {"2025-01-01", "2025-02-01"}

    def test_list_recent_jobs_limit(self):
        for i in range(5):
            create_job("strava", f"2025-0{i+1}-01", f"2025-0{i+1}-14")
        jobs = list_recent_jobs("strava", limit=3)
        assert len(jobs) == 3


# ── 정책 상수 ────────────────────────────────────────────────────────────

class TestPolicyConstants:
    def test_all_services_have_window_days(self):
        for svc in ("garmin", "strava", "intervals", "runalyze"):
            assert svc in WINDOW_DAYS
            assert WINDOW_DAYS[svc] > 0

    def test_strava_rate_limit_is_half_of_official(self):
        assert RATE_LIMITS["strava"]["per_15min"] == 100   # official 200 / 2
        assert RATE_LIMITS["strava"]["per_day"] == 1000    # official 2000 / 2

    def test_others_half_of_strava(self):
        for svc in ("garmin", "intervals", "runalyze"):
            assert RATE_LIMITS[svc]["per_15min"] <= RATE_LIMITS["strava"]["per_15min"]

    def test_inter_batch_sleep_positive(self):
        for svc in ("garmin", "strava", "intervals", "runalyze"):
            assert INTER_BATCH_SLEEP.get(svc, 0) > 0

    def test_runalyze_most_conservative(self):
        """Runalyze는 fair use — 배치 간 대기가 가장 길어야 함."""
        assert INTER_BATCH_SLEEP["runalyze"] >= max(
            INTER_BATCH_SLEEP[s] for s in ("garmin", "strava", "intervals")
        )


# ── 헬퍼 ─────────────────────────────────────────────────────────────────

def _make_job(**overrides) -> SyncJob:
    defaults = dict(
        id="test-id",
        service="garmin",
        from_date="2025-01-01",
        to_date="2025-03-31",
        window_days=14,
        current_from="2025-01-01",
        status="running",
        completed_days=0,
        total_days=90,
        synced_count=0,
        req_count=0,
        created_at="2025-01-01T00:00:00",
        updated_at="2025-01-01T00:00:00",
        retry_after=None,
        last_error=None,
    )
    defaults.update(overrides)
    return SyncJob(**defaults)
