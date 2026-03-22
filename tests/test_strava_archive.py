"""Strava archive import 테스트 — parse_tcx, parse_file_data(.gz), import_strava_archive."""
from __future__ import annotations

import csv
import gzip
import io
import json
import sqlite3
import tempfile
import textwrap
from pathlib import Path

import pytest

from src.db_setup import create_tables, migrate_db
from src.import_history import parse_tcx, parse_file_data
from src.import_export.strava_archive import (
    _find_activity_file,
    _merge,
    import_strava_archive,
)


# ── TCX 픽스처 ─────────────────────────────────────────────────────────────

_TCX_SAMPLE = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase
    xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Running">
      <Id>2026-03-22T07:00:00Z</Id>
      <Lap StartTime="2026-03-22T07:00:00Z">
        <TotalTimeSeconds>3600.0</TotalTimeSeconds>
        <DistanceMeters>10000.0</DistanceMeters>
        <Calories>550</Calories>
        <AverageHeartRateBpm><Value>148</Value></AverageHeartRateBpm>
        <MaximumHeartRateBpm><Value>172</Value></MaximumHeartRateBpm>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
""").encode()

_TCX_TWO_LAPS = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase
    xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Cycling">
      <Id>2026-03-22T08:00:00Z</Id>
      <Lap>
        <TotalTimeSeconds>1800.0</TotalTimeSeconds>
        <DistanceMeters>15000.0</DistanceMeters>
        <Calories>300</Calories>
        <AverageHeartRateBpm><Value>140</Value></AverageHeartRateBpm>
        <MaximumHeartRateBpm><Value>165</Value></MaximumHeartRateBpm>
      </Lap>
      <Lap>
        <TotalTimeSeconds>1800.0</TotalTimeSeconds>
        <DistanceMeters>15000.0</DistanceMeters>
        <Calories>300</Calories>
        <AverageHeartRateBpm><Value>150</Value></AverageHeartRateBpm>
        <MaximumHeartRateBpm><Value>170</Value></MaximumHeartRateBpm>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
""").encode()

_TCX_INVALID = b"<notXML>oops"
_TCX_NO_ACTIVITIES = b"<TrainingCenterDatabase/>"


# ── DB 픽스처 ──────────────────────────────────────────────────────────────

@pytest.fixture()
def mem_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


# ── parse_tcx 단위 테스트 ──────────────────────────────────────────────────

class TestParseTcx:
    def test_basic_fields(self, tmp_path):
        f = tmp_path / "run.tcx"
        f.write_bytes(_TCX_SAMPLE)
        result = parse_tcx(f)
        assert result is not None
        assert result["distance_km"] == pytest.approx(10.0)
        assert result["duration_sec"] == 3600
        assert result["activity_type"] == "running"
        assert result["avg_hr"] == 148
        assert result["max_hr"] == 172
        assert result["calories"] == 550

    def test_start_time_present(self, tmp_path):
        f = tmp_path / "run.tcx"
        f.write_bytes(_TCX_SAMPLE)
        result = parse_tcx(f)
        assert result["start_time"] == "2026-03-22T07:00:00Z"

    def test_two_laps_aggregated(self, tmp_path):
        f = tmp_path / "ride.tcx"
        f.write_bytes(_TCX_TWO_LAPS)
        result = parse_tcx(f)
        assert result is not None
        assert result["distance_km"] == pytest.approx(30.0)
        assert result["duration_sec"] == 3600
        assert result["activity_type"] == "cycling"
        assert result["calories"] == 600
        assert result["max_hr"] == 170
        # avg_hr = mean of lap averages = (140+150)/2 = 145
        assert result["avg_hr"] == 145

    def test_from_bytes(self, tmp_path):
        """data= 파라미터로도 동작한다."""
        f = tmp_path / "run.tcx"  # 실제 파일 불필요, stem만 사용
        result = parse_tcx(f, data=_TCX_SAMPLE)
        assert result is not None
        assert result["distance_km"] == pytest.approx(10.0)

    def test_invalid_xml_returns_none(self, tmp_path):
        f = tmp_path / "bad.tcx"
        f.write_bytes(_TCX_INVALID)
        assert parse_tcx(f) is None

    def test_no_activities_returns_none(self, tmp_path):
        f = tmp_path / "empty.tcx"
        f.write_bytes(_TCX_NO_ACTIVITIES)
        assert parse_tcx(f) is None

    def test_pace_calculated(self, tmp_path):
        f = tmp_path / "run.tcx"
        f.write_bytes(_TCX_SAMPLE)
        result = parse_tcx(f)
        # 3600s / 10km = 360 sec/km
        assert result["avg_pace_sec_km"] == 360


# ── parse_file_data + .gz 단위 테스트 ─────────────────────────────────────

class TestParseFileData:
    def test_tcx_file(self, tmp_path):
        f = tmp_path / "run.tcx"
        f.write_bytes(_TCX_SAMPLE)
        result = parse_file_data(f)
        assert result is not None
        assert result["distance_km"] == pytest.approx(10.0)

    def test_tcx_gz(self, tmp_path):
        gz_path = tmp_path / "run.tcx.gz"
        with gzip.open(gz_path, "wb") as gz:
            gz.write(_TCX_SAMPLE)
        result = parse_file_data(gz_path)
        assert result is not None
        assert result["distance_km"] == pytest.approx(10.0)

    def test_gz_corrupted_returns_none(self, tmp_path):
        gz_path = tmp_path / "bad.fit.gz"
        gz_path.write_bytes(b"not gzip data")
        assert parse_file_data(gz_path) is None

    def test_unknown_extension_returns_none(self, tmp_path):
        f = tmp_path / "data.csv"
        f.write_text("hello")
        assert parse_file_data(f) is None

    def test_unknown_gz_extension_returns_none(self, tmp_path):
        gz_path = tmp_path / "data.csv.gz"
        with gzip.open(gz_path, "wb") as gz:
            gz.write(b"hello")
        assert parse_file_data(gz_path) is None


# ── _find_activity_file 단위 테스트 ──────────────────────────────────────

class TestFindActivityFile:
    def test_finds_file(self, tmp_path):
        (tmp_path / "12345.fit.gz").write_bytes(b"dummy")
        result = _find_activity_file(tmp_path, "activities/12345.fit.gz")
        assert result is not None
        assert result.name == "12345.fit.gz"

    def test_bare_filename(self, tmp_path):
        (tmp_path / "12345.tcx").write_bytes(b"dummy")
        result = _find_activity_file(tmp_path, "12345.tcx")
        assert result is not None

    def test_not_found_returns_none(self, tmp_path):
        result = _find_activity_file(tmp_path, "activities/missing.fit.gz")
        assert result is None

    def test_none_filename_returns_none(self, tmp_path):
        assert _find_activity_file(tmp_path, None) is None

    def test_empty_filename_returns_none(self, tmp_path):
        assert _find_activity_file(tmp_path, "") is None


# ── _merge 단위 테스트 ────────────────────────────────────────────────────

class TestMerge:
    _csv = {
        "source_id": "111", "start_time": "2026-03-22T16:00:00",
        "activity_type": "running", "description": "Morning Run",
        "distance_km": 9.8, "duration_sec": 3500,
        "avg_hr": 145, "max_hr": 170, "calories": 520, "avg_power": None,
    }

    def test_csv_only_no_file(self):
        merged = _merge(self._csv, None)
        assert merged["distance_km"] == 9.8
        assert merged["description"] == "Morning Run"

    def test_file_overrides_precise_metrics(self):
        file_d = {"distance_km": 10.05, "duration_sec": 3610,
                  "avg_hr": 148, "max_hr": 172, "avg_cadence": 170, "elevation_gain": 45.0}
        merged = _merge(self._csv, file_d)
        assert merged["distance_km"] == pytest.approx(10.05)
        assert merged["avg_hr"] == 148
        assert merged["avg_cadence"] == 170

    def test_pace_recalculated(self):
        file_d = {"distance_km": 10.0, "duration_sec": 3600}
        merged = _merge(self._csv, file_d)
        assert merged["avg_pace_sec_km"] == 360

    def test_csv_description_preserved(self):
        file_d = {"distance_km": 10.0, "duration_sec": 3600, "description": "12345.tcx"}
        merged = _merge(self._csv, file_d)
        # description은 CSV 우선 (파일명 stem이 아닌 활동 이름)
        assert merged["description"] == "Morning Run"

    def test_activity_type_fallback_from_file(self):
        csv_no_type = {**self._csv, "activity_type": None}
        file_d = {"activity_type": "cycling"}
        merged = _merge(csv_no_type, file_d)
        assert merged["activity_type"] == "cycling"


# ── import_strava_archive 통합 테스트 ─────────────────────────────────────

def _make_archive(tmp_path: Path, rows: list[dict], files: dict[str, bytes]) -> Path:
    """테스트용 archive 폴더 생성.

    Args:
        rows:  activities.csv 행 목록
        files: {filename: content} — activities/ 폴더에 생성할 파일
    """
    acts_dir = tmp_path / "activities"
    acts_dir.mkdir()

    if rows:
        fieldnames = list(rows[0].keys())
        with open(tmp_path / "activities.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

    for name, content in files.items():
        (acts_dir / name).write_bytes(content)

    return tmp_path


def _csv_row(activity_id: str, filename: str = "", **kwargs) -> dict:
    """activities.csv 행 기본 템플릿."""
    return {
        "Activity ID": activity_id,
        "Activity Date": "Nov 17, 2023, 10:56:10 AM",
        "Activity Name": kwargs.get("name", "Test Run"),
        "Activity Type": kwargs.get("activity_type", "Run"),
        "Elapsed Time": kwargs.get("elapsed_time", "3600"),
        "Moving Time": kwargs.get("moving_time", "3500"),
        "Distance": kwargs.get("distance", "10000"),
        "Average Heart Rate": kwargs.get("avg_hr", "150"),
        "Max Heart Rate": kwargs.get("max_hr", "175"),
        "Calories": kwargs.get("calories", "500"),
        "Average Speed": kwargs.get("avg_speed", "2.78"),
        "Average Cadence": "",
        "Elevation Gain": "",
        "Average Watts": "",
        "Relative Effort": "",
        "Activity Gear": "",
        "Filename": filename,
    }


class TestImportStravaArchive:
    def test_no_csv_returns_error(self, mem_db, tmp_path):
        stats = import_strava_archive(mem_db, tmp_path)
        assert stats["errors"] == 1
        assert stats["inserted"] == 0

    def test_csv_only_fallback(self, mem_db, tmp_path):
        """파일 없을 때 CSV-only row 생성."""
        rows = [_csv_row("111111", filename="")]
        _make_archive(tmp_path, rows, {})
        stats = import_strava_archive(mem_db, tmp_path)
        assert stats["inserted"] == 1
        assert stats["csv_only"] == 1
        assert stats["file_linked"] == 0

    def test_source_id_is_activity_id(self, mem_db, tmp_path):
        rows = [_csv_row("9876543210", filename="")]
        _make_archive(tmp_path, rows, {})
        import_strava_archive(mem_db, tmp_path)
        row = mem_db.execute(
            "SELECT source_id FROM activity_summaries WHERE source='strava'"
        ).fetchone()
        assert row[0] == "9876543210"

    def test_file_linked_with_tcx_gz(self, mem_db, tmp_path):
        """TCX.gz 파일이 연결되면 file_linked 카운트."""
        gz_content = gzip.compress(_TCX_SAMPLE)
        rows = [_csv_row("222222", filename="activities/222222.tcx.gz")]
        _make_archive(tmp_path, rows, {"222222.tcx.gz": gz_content})
        stats = import_strava_archive(mem_db, tmp_path)
        assert stats["inserted"] == 1
        assert stats["file_linked"] == 1
        assert stats["gz_ok"] == 1
        assert stats["csv_only"] == 0

    def test_file_parse_failure_falls_back_to_csv(self, mem_db, tmp_path):
        """파일 파싱 실패 시 CSV-only fallback."""
        rows = [_csv_row("333333", filename="activities/333333.tcx.gz")]
        _make_archive(tmp_path, rows, {"333333.tcx.gz": b"corrupted gz data"})
        stats = import_strava_archive(mem_db, tmp_path)
        assert stats["inserted"] == 1
        assert stats["csv_only"] == 1

    def test_duplicate_skipped(self, mem_db, tmp_path):
        rows = [_csv_row("444444"), _csv_row("444444")]
        _make_archive(tmp_path, rows, {})
        stats = import_strava_archive(mem_db, tmp_path)
        assert stats["inserted"] == 1
        assert stats["skipped"] == 1

    def test_multiple_activities(self, mem_db, tmp_path):
        rows = [_csv_row(str(i)) for i in range(5)]
        _make_archive(tmp_path, rows, {})
        stats = import_strava_archive(mem_db, tmp_path)
        assert stats["inserted"] == 5
        assert stats["csv_total"] == 5

    def test_file_data_overrides_distance(self, mem_db, tmp_path):
        """TCX 파일 거리가 CSV 거리를 대체한다."""
        gz_content = gzip.compress(_TCX_SAMPLE)  # 10km
        rows = [_csv_row("555555", filename="activities/555555.tcx.gz", distance="9000")]
        _make_archive(tmp_path, rows, {"555555.tcx.gz": gz_content})
        import_strava_archive(mem_db, tmp_path)
        row = mem_db.execute(
            "SELECT distance_km FROM activity_summaries WHERE source_id='555555'"
        ).fetchone()
        # TCX에서 10km, CSV에서 9km — 파일 우선
        assert row[0] == pytest.approx(10.0)

    def test_csv_description_preserved(self, mem_db, tmp_path):
        """활동 이름(description)은 CSV 우선."""
        gz_content = gzip.compress(_TCX_SAMPLE)
        rows = [_csv_row("666666", filename="activities/666666.tcx.gz", name="My Best Run")]
        _make_archive(tmp_path, rows, {"666666.tcx.gz": gz_content})
        import_strava_archive(mem_db, tmp_path)
        row = mem_db.execute(
            "SELECT description FROM activity_summaries WHERE source_id='666666'"
        ).fetchone()
        assert row[0] == "My Best Run"

    def test_raw_payload_stored(self, mem_db, tmp_path):
        rows = [_csv_row("777777")]
        _make_archive(tmp_path, rows, {})
        import_strava_archive(mem_db, tmp_path)
        row = mem_db.execute(
            "SELECT entity_type FROM raw_source_payloads WHERE entity_id='777777'"
        ).fetchone()
        assert row is not None
        assert row[0] == "archive_import"

    def test_export_filename_stored(self, mem_db, tmp_path):
        rows = [_csv_row("888888", filename="activities/888888.fit.gz")]
        _make_archive(tmp_path, rows, {})
        import_strava_archive(mem_db, tmp_path)
        row = mem_db.execute(
            "SELECT export_filename FROM activity_summaries WHERE source_id='888888'"
        ).fetchone()
        assert row[0] == "activities/888888.fit.gz"
