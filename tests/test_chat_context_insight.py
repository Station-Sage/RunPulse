"""Coach 컨텍스트 해석 보강(C-2) — Lap 요약·플랜 이행·HRV 분포."""
import sqlite3
from datetime import date, timedelta

from src.ai.chat_context_insight import add_insight_context, format_insight_lines
from src.ai.chat_context_scope import describe_scope
from src.db_setup import create_tables


def _conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    return c


def test_empty_db_adds_nothing():
    c = _conn()
    ctx = {}
    add_insight_context(c, ctx, date.today().isoformat())
    assert ctx == {}
    assert format_insight_lines(ctx) == []


def test_plan_adherence_and_hrv():
    c = _conn()
    today = date.today()
    for i in range(1, 9):
        d = (today - timedelta(days=i)).isoformat()
        c.execute("INSERT INTO planned_workouts(date, workout_type, completed, skip_reason) "
                  "VALUES (?,?,?,?)", (d, "tempo" if i % 2 else "easy", 1 if i < 5 else 0,
                                       None if i < 5 else "피로"))
    for i in range(10):
        d = (today - timedelta(days=i)).isoformat()
        c.execute("INSERT INTO daily_wellness(date, hrv_last_night) VALUES (?,?)",
                  (d, 50 + i))
    ctx = {}
    add_insight_context(c, ctx, today.isoformat())
    assert ctx["plan_adherence"]["planned"] == 8
    assert ctx["plan_adherence"]["done"] == 4
    assert ctx["plan_adherence"]["skip_reasons"] == {"피로": 4}
    assert ctx["hrv_dist"]["days"] == 10
    text = "\n".join(format_insight_lines(ctx))
    assert "플랜 이행" in text and "HRV 분포" in text
    items = {s["item"] for s in describe_scope(ctx)}
    assert {"플랜 이행 요약", "HRV 분포"} <= items


def test_lap_summary_fade():
    c = _conn()
    day = date.today().isoformat()
    c.execute("INSERT INTO activity_summaries (id, source, source_id, name, activity_type, start_time,"
              " distance_m, duration_sec, avg_hr, avg_pace_sec_km) "
              "VALUES (1,'garmin','1','r','running',?,8000,2400,150,300)", (f"{day}T06:00:00",))
    for i, (pace, hr) in enumerate([(300, 145), (302, 148), (310, 155), (320, 160)]):
        c.execute("INSERT INTO activity_laps(activity_id, source, lap_index, duration_sec, distance_m,"
                  " avg_hr, avg_pace_sec_km, lap_kind) VALUES (1,'garmin',?,600,2000,?,?,'ACTIVE')",
                  (i, hr, pace))
    ctx = {}
    add_insight_context(c, ctx, day)
    ls = ctx["lap_summary"]
    assert ls["work_laps"] == 4 and ls["pace_delta_sec"] > 0
    assert "후반" in "\n".join(format_insight_lines(ctx))
