"""daily_fitness 테이블 및 관련 분석 모듈 테스트."""

import sqlite3
import pytest
from datetime import date, timedelta

from src.db_setup import create_tables, migrate_db
from src.analysis.trends import fitness_trend
from src.analysis.compare import compare_periods


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    yield c
    c.close()


def _insert_daily_fitness(conn, date_str, source, **kwargs):
    """daily_fitness 삽입 헬퍼."""
    cols = ["date", "source"] + list(kwargs.keys())
    placeholders = ", ".join("?" * len(cols))
    values = [date_str, source] + list(kwargs.values())
    conn.execute(
        f"INSERT OR REPLACE INTO daily_fitness ({', '.join(cols)}) VALUES ({placeholders})",
        values,
    )


def _insert_activity(conn, source, source_id, start_time, distance_km=10.0):
    conn.execute("""
        INSERT INTO activity_summaries
            (source, source_id, start_time, distance_km, activity_type)
        VALUES (?, ?, ?, ?, 'running')
    """, (source, source_id, start_time, distance_km))
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


# ── daily_fitness 테이블 기본 동작 ──────────────────────────────────────

def test_insert_and_replace(conn):
    """같은 (date, source) 조합 INSERT OR REPLACE 동작."""
    _insert_daily_fitness(conn, "2026-01-01", "intervals", ctl=50.0, atl=55.0)
    _insert_daily_fitness(conn, "2026-01-01", "intervals", ctl=52.0, atl=56.0)

    row = conn.execute(
        "SELECT ctl, atl FROM daily_fitness WHERE date='2026-01-01' AND source='intervals'"
    ).fetchone()
    assert row[0] == pytest.approx(52.0)  # 최신 값으로 대체됨


def test_different_sources_same_date(conn):
    """같은 날짜에 다른 source 독립 저장."""
    _insert_daily_fitness(conn, "2026-01-01", "intervals", ctl=50.0)
    _insert_daily_fitness(conn, "2026-01-01", "runalyze", runalyze_evo2max=48.5)
    _insert_daily_fitness(conn, "2026-01-01", "garmin", garmin_vo2max=47.0)

    rows = conn.execute(
        "SELECT source FROM daily_fitness WHERE date='2026-01-01' ORDER BY source"
    ).fetchall()
    sources = [r[0] for r in rows]
    assert "garmin" in sources
    assert "intervals" in sources
    assert "runalyze" in sources


def test_unique_constraint(conn):
    """(date, source) UNIQUE 제약 위반 시 IntegrityError."""
    conn.execute(
        "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'intervals', 50.0)"
    )
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO daily_fitness (date, source, ctl) VALUES ('2026-01-01', 'intervals', 55.0)"
        )


# ── migrate_db 안전성 ───────────────────────────────────────────────────

def test_migrate_db_on_fresh_db(conn):
    """migrate_db()가 빈 DB에서 오류 없이 실행."""
    migrate_db(conn)
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    assert "daily_fitness" in tables


def test_migrate_db_idempotent(conn):
    """migrate_db()를 여러 번 실행해도 데이터 유지."""
    _insert_daily_fitness(conn, "2026-01-01", "intervals", ctl=50.0)
    migrate_db(conn)
    migrate_db(conn)
    row = conn.execute("SELECT ctl FROM daily_fitness").fetchone()
    assert row[0] == pytest.approx(50.0)


# ── fitness_trend() daily_fitness 참조 확인 ─────────────────────────────

def test_fitness_trend_reads_daily_fitness(conn):
    """fitness_trend()가 daily_fitness에서 CTL/ATL/TSB를 읽음."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    _insert_daily_fitness(conn, monday.isoformat(), "intervals",
                          ctl=65.0, atl=70.0, tsb=-5.0)

    result = fitness_trend(conn, weeks=1)
    assert len(result) == 1
    assert result[0]["intervals_ctl"] == pytest.approx(65.0)
    assert result[0]["intervals_atl"] == pytest.approx(70.0)
    assert result[0]["intervals_tsb"] == pytest.approx(-5.0)


def test_fitness_trend_falls_back_to_source_metrics(conn):
    """daily_fitness 데이터 없을 때 source_metrics로 폴백."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    act_id = _insert_activity(conn, "intervals", "i1",
                              f"{monday.isoformat()}T08:00:00")
    conn.execute("""
        INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value)
        VALUES (?, 'intervals', 'ctl', 55.0)
    """, (act_id,))

    result = fitness_trend(conn, weeks=1)
    assert result[0]["intervals_ctl"] == pytest.approx(55.0)


def test_fitness_trend_runalyze(conn):
    """daily_fitness의 runalyze VO2Max/VDOT 조회."""
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    _insert_daily_fitness(conn, monday.isoformat(), "runalyze",
                          runalyze_evo2max=49.5, runalyze_vdot=45.0)

    result = fitness_trend(conn, weeks=1)
    assert result[0]["runalyze_evo2max"] == pytest.approx(49.5)
    assert result[0]["runalyze_vdot"] == pytest.approx(45.0)


# ── compare_periods() daily_fitness 참조 확인 ───────────────────────────

def test_compare_uses_daily_fitness_for_ctl(conn):
    """compare_periods()가 daily_fitness에서 CTL을 읽음."""
    _insert_daily_fitness(conn, "2026-01-02", "intervals", ctl=45.0)
    _insert_daily_fitness(conn, "2026-01-09", "intervals", ctl=50.0)

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    assert result["period1"]["intervals_ctl_last"] == pytest.approx(45.0)
    assert result["period2"]["intervals_ctl_last"] == pytest.approx(50.0)
    assert result["delta"]["intervals_ctl_last"] == pytest.approx(5.0)


def test_compare_no_daily_fitness_falls_back(conn):
    """daily_fitness 없으면 source_metrics 폴백."""
    act_id = _insert_activity(conn, "intervals", "i1", "2026-01-02T08:00:00")
    conn.execute("""
        INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value)
        VALUES (?, 'intervals', 'ctl', 42.0)
    """, (act_id,))

    result = compare_periods(conn, "2026-01-01", "2026-01-08",
                             "2026-01-08", "2026-01-15")
    assert result["period1"]["intervals_ctl_last"] == pytest.approx(42.0)


# ── graceful 처리 ───────────────────────────────────────────────────────

def test_fitness_trend_empty(conn):
    """데이터 전혀 없을 때 모든 지표 None."""
    result = fitness_trend(conn, weeks=2)
    assert len(result) == 2
    for w in result:
        assert w["intervals_ctl"] is None
        assert w["runalyze_evo2max"] is None
        assert w["garmin_vo2max"] is None
