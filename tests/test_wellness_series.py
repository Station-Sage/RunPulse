"""wellness_series: Garmin 실제 payload 구조 파싱·저장·파생 요약 (REVIEW-10 A6)."""
import sqlite3
from datetime import date

import pytest

from src.db_setup import create_tables
from src.sync import wellness_series as ws

TODAY = date(2026, 11, 17)
T0 = 1_763_000_000_000  # ms


@pytest.fixture
def conn(tmp_path):
    c = sqlite3.connect(tmp_path / "t.db")
    create_tables(c)
    return c


HRV = {"hrvReadings": [
    {"hrvValue": 40, "readingTimeGMT": "2026-11-17T01:00:00.0"},
    {"hrvValue": 60, "readingTimeGMT": "2026-11-17T01:05:00.0"},
    {"hrvValue": 80, "readingTimeGMT": "2026-11-17T01:10:00.0"},
]}
SLEEP = {
    "sleepLevels": [
        {"startGMT": "2026-11-17T00:00:00.0", "endGMT": "2026-11-17T01:00:00.0", "activityLevel": 0.0},
        {"startGMT": "2026-11-17T01:00:00.0", "endGMT": "2026-11-17T01:30:00.0", "activityLevel": 2.0},
    ],
    "sleepHeartRate": [{"value": 48, "startGMT": T0}, {"value": 52, "startGMT": T0 + 60000}],
    "wellnessEpochSPO2DataDTOList": [{"spo2Reading": 95, "epochTimestamp": "2026-11-17T00:10:00.0"}],
    "wellnessEpochRespirationDataDTOList": [{"respirationValue": 14.5, "startTimeGMT": T0}],
}
BB = [{"bodyBatteryValuesArray": [[T0, "MEASURED", 70, 1.0], [T0 + 180000, "MEASURED", 68, 1.0]]}]
STRESS = {"stressValuesArray": [[T0, 25], [T0 + 180000, -1], [T0 + 360000, 30]]}
HR = {"heartRateValues": [[T0, 60], [T0 + 120000, None], [T0 + 240000, 0], [T0 + 360000, 150]]}


def kinds(rows):
    return sorted({r[0] for r in rows})


def test_parsers_extract_real_structures():
    assert [r[2] for r in ws.parse_hrv(HRV)] == [40, 60, 80]
    s = ws.parse_sleep(SLEEP)
    assert kinds(s) == ["respiration", "sleep_hr", "sleep_stage", "spo2"]
    assert [r[2] for r in ws.parse_body_battery(BB)] == [70, 68]
    assert [r[2] for r in ws.parse_body_battery({"data": BB})] == [70, 68]
    assert [r[2] for r in ws.parse_stress(STRESS)] == [25, 30]  # -1(측정 불가) 제외
    assert [r[2] for r in ws.parse_hr_day(HR)] == [60, 150]  # None/0 제외


def test_parsers_tolerate_empty_and_garbage():
    assert ws.parse_hrv(None) == [] and ws.parse_sleep({}) == []
    assert ws.parse_body_battery(None) == [] and ws.parse_stress({"stressValuesArray": [1, "x"]}) == []


def test_derive_summary():
    d = ws.derive_summary(ws.parse_hrv(HRV) + ws.parse_sleep(SLEEP))
    assert d["hrv_night_min"] == 40 and d["hrv_night_p10"] == 44.0 and d["hrv_night_p90"] == 76.0
    assert d["sleep_hr_min"] == 48
    assert d["sleep_stage_deep_min"] == 60.0 and d["sleep_stage_rem_min"] == 30.0


def test_ingest_day_saves_series_and_summary_idempotently(conn):
    payloads = {"wellness_hrv": HRV, "wellness_sleep": SLEEP,
                "wellness_body_battery": {"data": BB}, "wellness_stress": STRESS}
    n1 = ws.ingest_day(conn, "2026-11-17", payloads, today=TODAY)
    n2 = ws.ingest_day(conn, "2026-11-17", payloads, today=TODAY)
    assert n1 == n2
    assert conn.execute("SELECT COUNT(*) FROM wellness_series").fetchone()[0] == n1
    v = conn.execute(
        "SELECT numeric_value FROM metric_store WHERE scope_id='2026-11-17' AND metric_name='hrv_night_min'"
    ).fetchone()
    assert v and v[0] == 40


def test_resave_replaces_stale_rows_of_same_kind(conn):
    ws.save_series(conn, "2026-11-17", [("stress", 1, 10.0, None), ("stress", 2, 20.0, None)], today=TODAY)
    ws.save_series(conn, "2026-11-17", [("stress", 3, 30.0, None)], today=TODAY)
    assert [r[0] for r in conn.execute("SELECT ts FROM wellness_series")] == [3]


def test_retention_drops_old_days(conn):
    old = "2025-01-01"
    ws.save_series(conn, "2026-11-17", [("stress", 1, 10.0, None)], today=TODAY)
    conn.execute("INSERT INTO wellness_series VALUES (?, 'garmin', 'stress', 5, 1, NULL)", (old,))
    assert ws.save_series(conn, old, [("stress", 9, 1.0, None)], today=TODAY) == 0
    assert conn.execute("SELECT COUNT(*) FROM wellness_series WHERE date=?", (old,)).fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM wellness_series").fetchone()[0] == 1


def test_ingest_hr_day(conn):
    assert ws.ingest_hr_day(conn, "2026-11-17", HR, today=TODAY) == 2
