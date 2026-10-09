"""plan_load: 세션 부하, 이지 u 중앙값, load_delta (주 부하 변화율·ACWR)."""
import sqlite3
from datetime import date, timedelta

from src.db_setup import create_tables
from src.services import plan_adjustment_service as svc
from src.services import plan_load

TODAY = date(2026, 10, 7)  # 수요일
T = TODAY.isoformat()


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def _run(c, i, day, km, trimp, pace=360):
    c.execute("INSERT INTO activity_summaries(source, source_id, name, activity_type, start_time, distance_m,"
              " avg_pace_sec_km) VALUES ('garmin', ?, 'r', 'running', ?, ?, ?)",
              (f"s{i}", day.isoformat() + "T07:00:00Z", km * 1000, pace))
    aid = c.execute("SELECT id FROM activity_summaries WHERE source_id=?", (f"s{i}",)).fetchone()[0]
    c.execute("INSERT INTO metric_store(scope_type, scope_id, metric_name, category, provider, numeric_value,"
              " is_primary) VALUES ('activity', ?, 'trimp', 'load', 'runpulse:formula_v1', ?, 1)", (str(aid), trimp))


def _seed(c):
    for i in range(1, 60):
        _run(c, i, TODAY - timedelta(days=i), 10, 90)  # u = 9.0
    ws = TODAY - timedelta(days=TODAY.weekday())
    for i, (wt, km) in enumerate([("easy", 8), ("easy", 8), ("interval", 10), ("easy", 8), ("long", 20)]):
        c.execute("INSERT INTO planned_workouts(id, date, workout_type, distance_km) VALUES (?,?,?,?)",
                  (i + 1, (ws + timedelta(days=i)).isoformat(), wt, km))
    c.commit()


def test_session_load_and_u():
    assert plan_load.session_load("rest", 10, 9) == 0 and plan_load.session_load("easy", None, 9) == 0
    assert plan_load.session_load("interval", 10, 9) == 1.23 * 90
    c = _conn()
    assert plan_load.easy_u(c, T) == plan_load.DEFAULT_U
    _seed(c)
    assert plan_load.easy_u(c, T) == 9.0


def test_load_delta_rest_lowers_week_and_acwr():
    c = _conn()
    _seed(c)
    after = svc.preview_after(c, 3, "rest")  # 오늘(수) = id 3 인터벌
    d = plan_load.load_delta(c, 3, after, today=T)
    assert d["week_pct"] < -10 and d["acwr_after"] < d["acwr_before"]
    none = plan_load.load_delta(c, 3, svc.preview_after(c, 3, "easy"), today=T)
    assert none["week_pct"] < 0
    assert plan_load.load_delta(c, 3, None, today=T) is None


def test_load_delta_none_without_history_or_other_week():
    c = _conn()
    c.execute("INSERT INTO planned_workouts(id,date,workout_type,distance_km) VALUES (50,?,'easy',8)", (T,))
    assert plan_load.load_delta(c, 50, {"workout_type": "rest", "distance_km": None}, today=T) is None
    _seed(c)
    assert plan_load.load_delta(c, 99, {"workout_type": "rest", "distance_km": None}, today=T) is None
