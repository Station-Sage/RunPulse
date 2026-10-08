"""calendar_feed_service — RFC 5545 준수, 제외 필드, 결정성, UID 안정성."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

import pytest

from src.services import calendar_feed_service as cfs

SECRET = "SECRET_NOTE_강남역"


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE planned_workouts (id INTEGER PRIMARY KEY, date TEXT, workout_type TEXT,
        distance_km REAL, target_pace_min REAL, target_pace_max REAL, target_hr_zone TEXT,
        description TEXT, rationale TEXT, skip_reason TEXT, completed INTEGER, matched_activity_id INTEGER,
        interval_prescription TEXT, updated_at TEXT)""")
    c.executemany(
        "INSERT INTO planned_workouts (date, workout_type, distance_km, target_pace_min, target_pace_max,"
        " target_hr_zone, description, rationale, skip_reason, completed, interval_prescription, updated_at)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        [("2026-10-10", "tempo", 3.74, 273, 288, "3", SECRET, SECRET, SECRET, 1, None, "2026-10-01 09:00:00"),
         ("2026-10-11", "rest", None, None, None, None, "", "", "", 0, None, None),
         ("2026-10-12", "interval", 8.0, None, None, None, "", "", "", 0,
          '{"sets":5,"rep_m":1000,"interval_pace":240}', None),
         ("2026-10-12", "easy", 5.0, 330, 330, "Z2", "", "", "", 0, None, None)])
    return c


def test_valid_structure_and_crlf(conn):
    out = cfs.build_ics(conn, "2026-10-01", "2026-10-31", "s")
    assert out.startswith("BEGIN:VCALENDAR\r\n") and out.endswith("END:VCALENDAR\r\n")
    assert "\n" not in out.replace("\r\n", "")
    assert out.count("BEGIN:VEVENT") == 3 and "TRANSP:TRANSPARENT" in out


def test_rest_excluded_and_dtend_next_day(conn):
    out = cfs.build_ics(conn, "2026-10-01", "2026-10-31")
    assert "20261011" not in out.replace("DTEND;VALUE=DATE:20261011", "")
    assert "DTSTART;VALUE=DATE:20261010\r\nDTEND;VALUE=DATE:20261011" in out


def test_summary_description_format(conn):
    out = cfs.build_ics(conn, "2026-10-01", "2026-10-31")
    assert "SUMMARY:RunPulse · 템포 3.7km" in out.replace("\r\n ", "")
    assert "DESCRIPTION:목표 4:33–4:48/km · Z3" in out.replace("\r\n ", "")
    assert "1000m × 5" in out.replace("\r\n ", "")


def test_excluded_fields_absent(conn):
    assert "SECRET" not in cfs.build_ics(conn, "2026-10-01", "2026-10-31")


def test_deterministic_bytes_and_dtstamp(conn):
    a = cfs.build_ics(conn, "2026-10-01", "2026-10-31", "s")
    assert a == cfs.build_ics(conn, "2026-10-01", "2026-10-31", "s")
    assert "DTSTAMP:20261001T090000Z" in a and "DTSTAMP:20261012T000000Z" in a


def test_uid_stable_across_regeneration_and_salt(conn):
    a = cfs.build_ics(conn, "2026-10-01", "2026-10-31", "s")
    conn.execute("UPDATE planned_workouts SET id = id + 100")
    assert a == cfs.build_ics(conn, "2026-10-01", "2026-10-31", "s")
    assert a != cfs.build_ics(conn, "2026-10-01", "2026-10-31", "other")


def test_escape_and_fold():
    assert cfs.escape_text("a,b;c\\d\ne") == "a\\,b\\;c\\\\d\\ne"
    folded = cfs.fold_line("X:" + "가" * 60)
    for ln in folded.split("\r\n"):
        assert len(ln.encode()) <= 75
    assert folded.replace("\r\n ", "") == "X:" + "가" * 60


def test_empty_plan_valid():
    c = sqlite3.connect(":memory:")
    c.execute("CREATE TABLE planned_workouts (id INTEGER PRIMARY KEY, date TEXT, workout_type TEXT,"
              " distance_km REAL, target_pace_min REAL, target_pace_max REAL, target_hr_zone TEXT,"
              " interval_prescription TEXT, updated_at TEXT)")
    out = cfs.build_ics(c, "2026-10-01", "2026-10-31")
    assert "BEGIN:VEVENT" not in out and "END:VCALENDAR" in out


def test_no_identity_and_event_cap(conn):
    out = cfs.build_ics(conn, "2026-10-01", "2026-10-31")
    assert "@runpulse" in out and "X-WR-CALNAME:RunPulse 훈련 계획" in out
    conn.executemany("INSERT INTO planned_workouts (date, workout_type, distance_km) VALUES (?, 'easy', 5)",
                     [("2026-11-01",)] * 600)
    assert cfs.build_ics(conn, "2026-10-01", "2026-12-31").count("BEGIN:VEVENT") == cfs.MAX_EVENTS


def test_default_range(conn):
    today = date(2026, 10, 8)
    frm, to = cfs.default_range(conn, today)
    assert frm == (today - timedelta(days=28)).isoformat() and to == "2026-10-12"
