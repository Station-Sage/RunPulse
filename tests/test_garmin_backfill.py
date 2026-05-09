"""garmin_backfill.py 테스트 — Layer 0 저장 + 라우팅 검증."""
import json
import sqlite3
import tempfile
import os

import pytest

from src.db_setup import create_tables
from src.sync.garmin_backfill import backfill_from_zip, _save_zip_metrics


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _make_db_file():
    """임시 DB 파일 생성 (backfill_from_zip은 파일 경로 사용)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    conn = sqlite3.connect(path)
    create_tables(conn)
    conn.commit()
    conn.close()
    return path


# ZIP export 포맷 샘플 (epoch ms, cm 단위)
SAMPLE_ZIP_ACT = {
    "activityId": 99001,
    "name": "Morning Run",
    "activityType": "running",
    "startTimeLocal": 1743480000000,  # epoch ms
    "distance": 1000000,  # cm → 10,000 m
    "duration": 3600000,  # ms → 3600 sec
    "movingDuration": 3500000,
    "avgHr": 150,
    "maxHr": 175,
    "elevationGain": 10000,  # cm → 100 m
    "elevationLoss": 9800,
    # non-DDL 필드 (metric_store로 라우팅)
    "bmrCalories": 400,
    "steps": 8000,
    "differenceBodyBattery": -15,
    "vO2MaxValue": 55.0,
    "moderateIntensityMinutes": 10,
    "vigorousIntensityMinutes": 45,
    # non-DDL 필드 (source_payloads에만 보존)
    "lapCount": 10,
    "deviceId": 12345678,
    "favorite": False,
    "minLatitude": 37.5,
    "maxLatitude": 37.6,
}


class TestSaveZipMetrics:
    def test_routes_metric_fields_to_metric_store(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, name, start_time) "
            "VALUES ('garmin', '99001', 'Run', '2026-04-01T08:00:00')"
        )
        activity_id = conn.execute(
            "SELECT id FROM activity_summaries WHERE source_id='99001'"
        ).fetchone()[0]

        fields = {
            "bmr_calories": 400,
            "steps": 8000,
            "body_battery_diff": -15,
            "vo2max_activity": 55.0,
            "moderate_intensity_min": 10,
            "vigorous_intensity_min": 45,
        }
        _save_zip_metrics(conn, activity_id, fields)

        rows = conn.execute(
            "SELECT metric_name, numeric_value FROM metric_store "
            "WHERE scope_type='activity' AND provider='garmin'"
        ).fetchall()
        metric_map = {r[0]: r[1] for r in rows}

        assert metric_map["bmr_calories"] == 400
        assert metric_map["steps"] == 8000
        assert metric_map["body_battery_diff"] == -15
        assert metric_map["vo2max_activity"] == 55.0
        assert metric_map["moderate_intensity_min"] == 10
        assert metric_map["vigorous_intensity_min"] == 45

    def test_skips_none_values(self):
        conn = _conn()
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, name, start_time) "
            "VALUES ('garmin', '99002', 'Run', '2026-04-01T08:00:00')"
        )
        activity_id = conn.execute(
            "SELECT id FROM activity_summaries WHERE source_id='99002'"
        ).fetchone()[0]

        _save_zip_metrics(conn, activity_id, {"bmr_calories": None, "steps": None})

        count = conn.execute(
            "SELECT COUNT(*) FROM metric_store WHERE scope_type='activity'"
        ).fetchone()[0]
        assert count == 0


class TestBackfillFromZip:
    def _write_zip_json(self, tmpdir, activities):
        path = os.path.join(tmpdir, "summarizedActivities.json")
        with open(path, "w") as f:
            json.dump([{"summarizedActivitiesExport": activities}], f)
        return tmpdir

    def test_insert_new_stores_raw_payload(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        create_tables(conn)
        conn.commit()
        conn.close()

        export_dir = self._write_zip_json(str(tmp_path), [SAMPLE_ZIP_ACT])
        backfill_from_zip(export_dir, db_path, dry_run=False, insert_new=True)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT payload FROM source_payloads "
            "WHERE source='garmin' AND entity_type='activity_zip' AND entity_id='99001'"
        ).fetchone()
        assert row is not None
        payload = json.loads(row[0])
        assert payload["activityId"] == 99001
        assert payload["lapCount"] == 10  # non-DDL 필드 보존 확인
        conn.close()

    def test_insert_new_no_operationalerror_on_nondll_columns(self, tmp_path):
        """non-DDL 컬럼(lapCount, deviceId 등) 포함 시 OperationalError 없음."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        create_tables(conn)
        conn.commit()
        conn.close()

        export_dir = self._write_zip_json(str(tmp_path), [SAMPLE_ZIP_ACT])
        # OperationalError 발생하면 테스트 실패
        backfill_from_zip(export_dir, db_path, dry_run=False, insert_new=True)

        conn = sqlite3.connect(db_path)
        count = conn.execute(
            "SELECT COUNT(*) FROM activity_summaries WHERE source='garmin'"
        ).fetchone()[0]
        assert count == 1
        conn.close()

    def test_insert_new_routes_metrics(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        create_tables(conn)
        conn.commit()
        conn.close()

        export_dir = self._write_zip_json(str(tmp_path), [SAMPLE_ZIP_ACT])
        backfill_from_zip(export_dir, db_path, dry_run=False, insert_new=True)

        conn = sqlite3.connect(db_path)
        rows = conn.execute(
            "SELECT metric_name, numeric_value FROM metric_store "
            "WHERE scope_type='activity' AND provider='garmin'"
        ).fetchall()
        metric_map = {r[0]: r[1] for r in rows}

        assert metric_map.get("bmr_calories") == 400
        assert metric_map.get("steps") == 8000
        conn.close()

    def test_update_filters_nondll_columns(self, tmp_path):
        """기존 활동 업데이트 시 non-DDL 컬럼으로 OperationalError 없음."""
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        create_tables(conn)
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, name, start_time) "
            "VALUES ('garmin', '99001', 'Old Name', '2026-04-01T08:00:00')"
        )
        conn.commit()
        conn.close()

        export_dir = self._write_zip_json(str(tmp_path), [SAMPLE_ZIP_ACT])
        backfill_from_zip(export_dir, db_path, dry_run=False, insert_new=False)

        conn = sqlite3.connect(db_path)
        row = conn.execute(
            "SELECT avg_hr FROM activity_summaries WHERE source='garmin' AND source_id='99001'"
        ).fetchone()
        assert row[0] == 150  # DDL 컬럼은 업데이트됨
        conn.close()

    def test_update_links_raw_payload_to_activity(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        conn = sqlite3.connect(db_path)
        create_tables(conn)
        conn.execute(
            "INSERT INTO activity_summaries (source, source_id, name, start_time) "
            "VALUES ('garmin', '99001', 'Old Name', '2026-04-01T08:00:00')"
        )
        conn.commit()
        conn.close()

        export_dir = self._write_zip_json(str(tmp_path), [SAMPLE_ZIP_ACT])
        backfill_from_zip(export_dir, db_path, dry_run=False, insert_new=False)

        conn = sqlite3.connect(db_path)
        activity_id = conn.execute(
            "SELECT id FROM activity_summaries WHERE source_id='99001'"
        ).fetchone()[0]
        sp_row = conn.execute(
            "SELECT activity_id FROM source_payloads "
            "WHERE source='garmin' AND entity_type='activity_zip' AND entity_id='99001'"
        ).fetchone()
        assert sp_row is not None
        assert sp_row[0] == activity_id
        conn.close()
