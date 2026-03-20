"""analyze.py CLI 테스트."""

import json
import sqlite3

import pytest

from src import analyze
from src.db_setup import create_tables


@pytest.fixture
def temp_db(tmp_path, monkeypatch):
    db = tmp_path / "running.db"
    conn = sqlite3.connect(db)
    create_tables(conn)

    today = __import__("datetime").date.today().isoformat()
    conn.execute(
        """
        INSERT INTO activities
        (source, source_id, activity_type, start_time, distance_km, duration_sec,
         avg_pace_sec_km, avg_hr)
        VALUES ('garmin','g1','running',?,?,?,?,?)
        """,
        (today + "T08:00:00", 10.0, 3600, 360, 150),
    )
    conn.commit()
    conn.close()

    monkeypatch.setattr(analyze, "_db_path", lambda: db)
    monkeypatch.setattr(analyze, "copy_to_clipboard", lambda text: True)
    return db


def test_today_subcommand(temp_db, capsys):
    analyze.main(["today"])
    out = capsys.readouterr().out
    assert out.strip()


def test_week_subcommand(temp_db, capsys):
    analyze.main(["week"])
    out = capsys.readouterr().out
    assert out.strip()


def test_race_subcommand(temp_db, capsys):
    analyze.main(["race", "--date", "2026-06-01", "--distance", "42.195"])
    out = capsys.readouterr().out
    assert out.strip()


def test_deep_by_id(temp_db, capsys):
    analyze.main(["deep", "--id", "1"])
    out = capsys.readouterr().out
    assert out.strip()


def test_compare_week(temp_db, capsys):
    analyze.main(["compare", "--period", "week"])
    out = capsys.readouterr().out
    assert out.strip()


def test_trends_weeks(temp_db, capsys):
    analyze.main(["trends", "--weeks", "4"])
    out = capsys.readouterr().out
    assert out.strip()


def test_full_subcommand(temp_db, capsys):
    analyze.main(["full"])
    out = capsys.readouterr().out
    assert out.strip()


def test_json_output(temp_db, capsys):
    analyze.main(["full", "--json"])
    out = capsys.readouterr().out
    data = json.loads(out)
    assert isinstance(data, dict)


def test_ai_context_output(temp_db, capsys):
    analyze.main(["today", "--ai-context"])
    out = capsys.readouterr().out
    assert "[" in out and "]" in out


def test_save_option(temp_db, tmp_path, capsys):
    target = tmp_path / "out.md"
    analyze.main(["today", "--save", str(target)])
    capsys.readouterr()
    assert target.exists()
