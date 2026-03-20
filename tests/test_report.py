import sqlite3
from datetime import date

import pytest

from src.analysis.report import generate_ai_context, generate_report
from src.db_setup import create_tables


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()


def _insert_activity(conn, source="garmin", start_time=None, distance_km=10.0, duration_sec=3000, avg_hr=150):
    start_time = start_time or (date.today().isoformat() + "T06:00:00")
    source_id = f"{source}-{start_time}"
    cur = conn.execute(
        """
        INSERT INTO activity_summaries
        (source, source_id, activity_type, start_time, distance_km, duration_sec, avg_pace_sec_km, avg_hr)
        VALUES (?, ?, 'running', ?, ?, ?, ?, ?)
        """,
        (source, source_id, start_time, distance_km, duration_sec, int(duration_sec / distance_km), avg_hr),
    )
    return cur.lastrowid


def _insert_daily(conn, d, source, **values):
    cols = ["date", "source"] + list(values.keys())
    q = ", ".join(["?"] * len(cols))
    conn.execute(
        f"INSERT INTO daily_fitness ({', '.join(cols)}) VALUES ({q})",
        [d, source] + list(values.values()),
    )


def test_today_report_no_data(conn):
    assert generate_report(conn, "today") == "오늘 활동이 없습니다."


def test_today_report_has_header(conn):
    _insert_activity(conn)
    conn.commit()
    result = generate_report(conn, "today")
    assert "# 오늘 리포트" in result
    assert "## 기본 정보" in result


def test_week_report(conn):
    _insert_activity(conn)
    conn.commit()
    result = generate_report(conn, "week")
    assert "# 주간 리포트" in result


def test_month_report(conn):
    _insert_activity(conn)
    conn.commit()
    result = generate_report(conn, "month")
    assert "# 월간 리포트" in result


def test_full_report(conn):
    _insert_activity(conn)
    conn.commit()
    result = generate_report(conn, "full")
    assert "# 전체 리포트" in result
    assert "# 오늘 리포트" in result


def test_race_report_insufficient_data(conn):
    result = generate_report(conn, "race")
    assert "# 레이스 준비도 리포트" in result
    assert "## 안내" in result
    assert "충분한 데이터가 쌓이지 않았습니다" in result


def test_race_report_with_data(conn):
    today = date.today().isoformat()
    _insert_daily(conn, today, "intervals", ctl=45, atl=50, tsb=5)
    _insert_daily(conn, today, "garmin", garmin_vo2max=49)
    _insert_daily(conn, today, "runalyze", runalyze_vdot=46, runalyze_evo2max=49)
    conn.commit()

    result = generate_report(conn, "race")
    assert "# 레이스 준비도 리포트" in result
    assert "## 점수 구성" in result


def test_ai_context_brief_insufficient(conn):
    result = generate_ai_context(conn, "brief")
    assert "[AI_CONTEXT]" in result
    assert "[race_status=insufficient_data]" in result


def test_ai_context_brief_with_data(conn):
    today = date.today().isoformat()
    _insert_daily(conn, today, "intervals", ctl=45, atl=50, tsb=5)
    _insert_daily(conn, today, "garmin", garmin_vo2max=49)
    _insert_daily(conn, today, "runalyze", runalyze_vdot=46, runalyze_evo2max=49)
    conn.commit()

    result = generate_ai_context(conn, "brief")
    assert "[AI_CONTEXT]" in result
    assert "[race_status=ok]" in result
