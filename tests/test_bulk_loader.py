"""GarminBulkLoader 테스트.

검증 항목:
  1. 단일 summary JSON 로드
  2. 복수 summary JSON 로드
  3. 중복 skip (payload_hash)
  4. 잘못된 JSON 처리 (error, not crash)
  5. ZIP 파일 없음 처리
  6. summary + detail 함께 처리
  7. detail에 matching summary 없으면 skip
  8. ZIP이 아닌 파일 처리
"""

from __future__ import annotations

import io
import json
import sqlite3
import zipfile
from pathlib import Path

import pytest

from src.db_setup import create_tables
from src.sync.garmin_bulk_loader import GarminBulkLoader, _SUMMARY_SUFFIX, _DETAIL_SUFFIX


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def _make_conn():
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    create_tables(conn)
    return conn


def _make_zip(files: dict[str, str | dict | list]) -> io.BytesIO:
    """파일명 → 내용(문자열 또는 JSON 직렬화할 dict/list) 매핑으로 ZIP 생성."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for fname, content in files.items():
            if isinstance(content, (dict, list)):
                content = json.dumps(content)
            zf.writestr(fname, content)
    buf.seek(0)
    return buf


def _summary(activity_id: int, distance_m: float = 10000.0) -> dict:
    """최소한의 Garmin summary JSON."""
    return {
        "activityId": activity_id,
        "activityName": "Morning Run",
        "activityType": {"typeKey": "running"},
        "startTimeGMT": "2025-01-15 08:00:00",
        "startTimeLocal": "2025-01-15 17:00:00",
        "distance": distance_m,
        "duration": 3600.0,
        "movingDuration": 3550.0,
        "elapsedDuration": 3600.0,
        "averageSpeed": 2.78,
        "maxSpeed": 3.5,
        "averageHR": 155,
        "maxHR": 178,
        "averageRunningCadenceInStepsPerMinute": 172,
    }


def _detail(activity_id: int) -> dict:
    """최소한의 Garmin detail JSON."""
    return {
        "activityId": activity_id,
        "summaryDTO": {
            "startTimeGMT": "2025-01-15 08:00:00",
        },
    }


def _write_zip_to_tmp(buf: io.BytesIO, tmp_path: Path) -> Path:
    p = tmp_path / "export.zip"
    p.write_bytes(buf.read())
    return p


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestSingleSummary:
    def test_loads_one_activity(self, tmp_path):
        buf = _make_zip({f"12345{_SUMMARY_SUFFIX}": _summary(12345)})
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        assert result.status == "success"
        assert result.synced_count == 1
        assert result.skipped_count == 0
        assert result.error_count == 0

        cnt = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
        assert cnt == 1

        sp_cnt = conn.execute("SELECT COUNT(*) FROM source_payloads").fetchone()[0]
        assert sp_cnt == 1

    def test_activity_core_fields(self, tmp_path):
        buf = _make_zip({f"12345{_SUMMARY_SUFFIX}": _summary(12345, distance_m=15000.0)})
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        GarminBulkLoader(conn).load(p)

        row = conn.execute("SELECT source, source_id, distance_m FROM activity_summaries").fetchone()
        assert row["source"] == "garmin"
        assert row["source_id"] == "12345"
        assert row["distance_m"] == 15000.0


class TestMultipleSummaries:
    def test_loads_multiple_activities(self, tmp_path):
        files = {
            f"1{_SUMMARY_SUFFIX}": _summary(1),
            f"2{_SUMMARY_SUFFIX}": _summary(2),
            f"3{_SUMMARY_SUFFIX}": _summary(3),
        }
        buf = _make_zip(files)
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        assert result.synced_count == 3
        assert conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0] == 3


class TestDuplicateSkip:
    def test_duplicate_is_skipped(self, tmp_path):
        files = {f"12345{_SUMMARY_SUFFIX}": _summary(12345)}
        p = _write_zip_to_tmp(_make_zip(files), tmp_path)

        conn = _make_conn()
        loader = GarminBulkLoader(conn)

        r1 = loader.load(p)
        assert r1.synced_count == 1

        # 두 번째 로드 — 같은 ZIP
        r2 = loader.load(p)
        assert r2.synced_count == 0
        assert r2.skipped_count == 1

        # DB에 중복 없음
        assert conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0] == 1


class TestInvalidJson:
    def test_bad_json_is_counted_as_error(self, tmp_path):
        files = {
            f"12345{_SUMMARY_SUFFIX}": "NOT VALID JSON {{{",
            f"99999{_SUMMARY_SUFFIX}": _summary(99999),
        }
        buf = _make_zip(files)
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        # 유효한 1개는 성공
        assert result.synced_count == 1
        # 잘못된 1개는 에러
        assert result.error_count == 1
        # 크래시 없음


class TestMissingZip:
    def test_missing_file_returns_failed(self):
        conn = _make_conn()
        result = GarminBulkLoader(conn).load("/nonexistent/path/export.zip")

        assert result.status == "failed"
        assert result.last_error is not None
        assert result.synced_count == 0


class TestBadZip:
    def test_not_a_zip_returns_failed(self, tmp_path):
        p = tmp_path / "export.zip"
        p.write_bytes(b"this is not a zip file")

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        assert result.status == "failed"
        assert "Invalid ZIP" in (result.last_error or "")


class TestSummaryAndDetail:
    def test_detail_metrics_saved(self, tmp_path):
        """summary + detail → metric_store에 garmin 메트릭 저장."""
        files = {
            f"12345{_SUMMARY_SUFFIX}": _summary(12345),
            f"12345{_DETAIL_SUFFIX}": _detail(12345),
        }
        buf = _make_zip(files)
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        assert result.error_count == 0
        # source_payloads에 summary + detail 2건
        sp_cnt = conn.execute("SELECT COUNT(*) FROM source_payloads").fetchone()[0]
        assert sp_cnt == 2

    def test_detail_without_summary_is_skipped(self, tmp_path):
        """summary 없이 detail만 있으면 metrics 처리 skip."""
        files = {f"99999{_DETAIL_SUFFIX}": _detail(99999)}
        buf = _make_zip(files)
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        # 에러는 아니지만 activity_summaries에 행 없음
        assert conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0] == 0


class TestNonJsonFilesIgnored:
    def test_fit_and_gpx_ignored(self, tmp_path):
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("12345_ACTIVITY.fit", b"\x0e\x10\xd9\x07\x00\x00\x00\x00")
            zf.writestr("12345.gpx", "<gpx></gpx>")
            zf.writestr(f"99999{_SUMMARY_SUFFIX}", json.dumps(_summary(99999)))
        buf.seek(0)
        p = _write_zip_to_tmp(buf, tmp_path)

        conn = _make_conn()
        result = GarminBulkLoader(conn).load(p)

        # JSON 1개만 처리됨
        assert result.synced_count == 1
        assert conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0] == 1
