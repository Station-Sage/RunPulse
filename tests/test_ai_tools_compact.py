"""토큰 최적화 도구 — 압축 응답(fields+rows), 주별 롤업, get_training_summary."""
import json
import sqlite3
from datetime import date, timedelta

from src.ai.tools import TOOL_DECLARATIONS, execute_tool
from src.db_setup import create_tables


def _conn():
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    return conn


def _call(conn, name, args):
    return json.loads(execute_tool(conn, name, args))


def _act(conn, aid, day, km=10.0, sec=3000, hr=150, name="러닝", wtype=None):
    pace = sec / km
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, "
        "start_time, distance_m, duration_sec, avg_pace_sec_km, avg_hr) "
        "VALUES (?,?,?,?,'running',?,?,?,?,?)",
        (aid, "garmin", f"g{aid}", name, f"{day} 07:00:00", km * 1000, sec, pace, hr),
    )
    if wtype:
        conn.execute(
            "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, text_value, is_primary) "
            "VALUES ('activity', ?, 'workout_type_classified', 'runpulse:rules', ?, 1)",
            (str(aid), wtype),
        )


def _daily_metric(conn, day, name, value):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary) "
        "VALUES ('daily', ?, ?, 'runpulse:formula_v1', ?, 1)", (day, name, value),
    )


def _rows(out):
    """{"fields","rows"} → [{field: value}]"""
    return [dict(zip(out["fields"], r)) for r in out["rows"]]


class TestActivitiesRange:
    def test_short_range_is_daily_columnar_with_id(self):
        conn = _conn()
        _act(conn, 7, "2026-09-14", km=10.0, sec=3000, hr=150, name="A")
        out = _call(conn, "get_activities_range", {"start_date": "2026-09-14", "end_date": "2026-09-20"})
        assert out["granularity"] == "day"
        row = _rows(out)[0]
        assert row["id"] == 7 and row["km"] == 10 and row["min"] == 50 and row["pace"] == "5:00"

    def test_long_range_rolls_up_weekly(self):
        conn = _conn()
        _act(conn, 1, "2026-06-01")
        _act(conn, 2, "2026-08-10")
        out = _call(conn, "get_activities_range", {"start_date": "2026-06-01", "end_date": "2026-09-01"})
        assert out["granularity"] == "week" and out["count"] == 2
        assert out["unit"].startswith("week(Sun")
        assert "id" not in out["fields"]

    def test_weekly_fills_gap_weeks(self):
        conn = _conn()
        _act(conn, 1, "2026-07-05")
        _act(conn, 2, "2026-09-06")
        out = _call(conn, "get_activities_range", {"start_date": "2026-07-05", "end_date": "2026-09-06"})
        runs = [r["runs"] for r in _rows(out)]
        assert 0 in runs and len(runs) == 10

    def test_explicit_day_overrides_auto_within_limit(self):
        conn = _conn()
        _act(conn, 1, "2026-06-01")
        out = _call(conn, "get_activities_range",
                    {"start_date": "2026-06-01", "end_date": "2026-09-01", "granularity": "day"})
        assert out["granularity"] == "day"

    def test_day_beyond_limit_falls_back_with_note(self):
        conn = _conn()
        out = _call(conn, "get_activities_range",
                    {"start_date": "2025-01-01", "end_date": "2026-01-01", "granularity": "day"})
        assert out["granularity"] == "week" and out["note"]

    def test_columnar_is_much_smaller_than_keyed_rows(self):
        conn = _conn()
        for i in range(30):
            _act(conn, i + 1, (date(2026, 8, 1) + timedelta(days=i)).isoformat(), name="기초체력 양성")
        out = execute_tool(conn, "get_activities_range", {"start_date": "2026-08-01", "end_date": "2026-08-30"})
        keyed = json.dumps([{"activity_id": 1, "date": "2026-08-01", "km": 10.0, "sec": 3000,
                             "pace": "5:00", "hr": 150, "name": "기초체력 양성"}] * 30, ensure_ascii=False)
        assert len(out) < len(keyed) * 0.6


class TestWellness:
    def _seed(self, conn, start, days):
        for i in range(days):
            d = (start + timedelta(days=i)).isoformat()
            conn.execute(
                "INSERT INTO daily_wellness (date, body_battery_high, sleep_score, sleep_duration_sec, "
                "hrv_last_night, avg_stress, resting_hr) VALUES (?,?,?,?,?,?,?)",
                (d, 80, 75, 6.5 * 3600 + 20, 84.0, 30, 42),
            )

    def test_daily_values_are_rounded(self):
        conn = _conn()
        self._seed(conn, date(2026, 9, 14), 3)
        out = _call(conn, "get_wellness", {"start_date": "2026-09-14", "end_date": "2026-09-16"})
        row = _rows(out)[0]
        assert row["sleep_h"] == 6.5 and row["hrv"] == 84 and isinstance(row["hrv"], int)

    def test_long_range_weekly_mean_with_day_count(self):
        conn = _conn()
        self._seed(conn, date(2026, 6, 1), 100)
        out = _call(conn, "get_wellness", {"start_date": "2026-06-01", "end_date": "2026-09-08"})
        assert out["granularity"] == "week"
        assert _rows(out)[0]["n"] <= 7 and _rows(out)[1]["n"] == 7


class TestFitness:
    def test_daily_and_weekly(self):
        conn = _conn()
        today = date.today()
        for i in range(120):
            d = (today - timedelta(days=i)).isoformat()
            _daily_metric(conn, d, "ctl", 60.0 + i / 10)
            _daily_metric(conn, d, "atl", 70.0)
            _daily_metric(conn, d, "tsb", -10.0)
        short = _call(conn, "get_fitness", {"days": 14})
        assert short["granularity"] == "day" and "vo2max" not in short["fields"]
        long = _call(conn, "get_fitness", {"days": 100})
        assert long["granularity"] == "week" and len(long["rows"]) <= 16

    def test_weekly_takes_end_of_week_value(self):
        conn = _conn()
        start = date.today() - timedelta(days=100)
        for i in range(101):
            _daily_metric(conn, (start + timedelta(days=i)).isoformat(), "ctl", float(i))
        out = _call(conn, "get_fitness", {"days": 100})
        first = _rows(out)[0]
        last_day_of_first_week = date.fromisoformat(first["week"]) + timedelta(days=6)
        assert first["ctl"] == float((last_day_of_first_week - start).days)


class TestMetricsTrend:
    def test_daily_columnar(self):
        conn = _conn()
        for i in range(5):
            _daily_metric(conn, (date.today() - timedelta(days=i)).isoformat(), "acwr", 1.234 + i)
        out = _call(conn, "get_metrics_trend", {"metric_name": "acwr", "days": 10})
        assert out["fields"] == ["date", "value"] and len(out["rows"]) == 5
        assert out["rows"][0][1] == 5.23      # 날짜 오름차순: 가장 오래된 값이 첫 행

    def test_long_period_weekly(self):
        conn = _conn()
        for i in range(90):
            _daily_metric(conn, (date.today() - timedelta(days=i)).isoformat(), "acwr", 1.0)
        out = _call(conn, "get_metrics_trend", {"metric_name": "acwr", "days": 90})
        assert out["granularity"] == "week" and out["fields"] == ["week", "n", "value"]


class TestTrainingSummary:
    def _seed_block(self, conn):
        _act(conn, 1, "2026-09-01", km=10, sec=3300, wtype="easy")
        _act(conn, 2, "2026-09-03", km=10, sec=3000, wtype="tempo", name="템포")
        # 09-06 ~ 09-12 주는 러닝 없음
        _act(conn, 3, "2026-09-16", km=8, sec=2700, wtype="easy", name="크루즈")
        for i, lap_pace in enumerate((270, 272)):
            conn.execute(
                "INSERT INTO activity_laps (activity_id, source, lap_index, distance_m, duration_sec, "
                "avg_pace_sec_km, lap_trigger) VALUES (3,'garmin',?,1000,?,?,'ACTIVE')",
                (i, lap_pace, lap_pace),
            )
        _act(conn, 4, "2026-09-20", km=21.1, sec=6300, wtype="race", name="하프")
        for d, ctl in (("2026-09-05", 60.0), ("2026-09-19", 66.0), ("2026-09-20", 67.0)):
            _daily_metric(conn, d, "ctl", ctl)
            _daily_metric(conn, d, "atl", 70.0)
            _daily_metric(conn, d, "tsb", ctl - 70.0)
        conn.commit()

    def test_totals_and_weekly_rows_include_gap_week(self):
        conn = _conn(); self._seed_block(conn)
        out = _call(conn, "get_training_summary", {"start_date": "2026-08-30", "end_date": "2026-09-20"})
        assert out["totals"]["runs"] == 4 and out["totals"]["km"] == 49.1
        rows = _rows(out)
        assert [r["week"] for r in rows] == ["2026-08-30", "2026-09-06", "2026-09-13", "2026-09-20"]
        assert rows[1]["runs"] == 0

    def test_weekly_load_is_end_of_week_value(self):
        conn = _conn(); self._seed_block(conn)
        out = _call(conn, "get_training_summary", {"start_date": "2026-08-30", "end_date": "2026-09-20"})
        rows = _rows(out)
        assert rows[0]["ctl"] == 60.0     # 09-05 (토) 값
        assert rows[2]["ctl"] == 66.0     # 09-19 값
        assert rows[3]["ctl"] == 67.0

    def test_notable_has_race_and_structured_session_with_sets(self):
        conn = _conn(); self._seed_block(conn)
        out = _call(conn, "get_training_summary", {"start_date": "2026-08-30", "end_date": "2026-09-20"})
        notable = _rows(out["notable"])
        by_id = {r["id"]: r for r in notable}
        assert set(by_id) == {2, 3, 4}          # easy 1번은 제외
        assert by_id[3]["type"] == "easy" and by_id[3]["sets"] == 2   # 랩이 있어 포함
        assert by_id[4]["type"] == "race"
        assert [r["date"] for r in notable] == sorted(r["date"] for r in notable)

    def test_notable_is_capped_with_omitted_count_and_races_first(self):
        conn = _conn()
        for i in range(14):
            _act(conn, i + 1, (date(2026, 6, 1) + timedelta(days=i)).isoformat(), wtype="tempo")
        _act(conn, 99, "2026-06-01", wtype="race", name="옛 대회")
        out = _call(conn, "get_training_summary", {"start_date": "2026-06-01", "end_date": "2026-06-20"})
        assert len(out["notable"]["rows"]) == 10 and out["notable"]["omitted"] == 5
        assert 99 in {r["id"] for r in _rows(out["notable"])}    # 오래된 대회도 우선 포함

    def test_empty_period_returns_zero_totals(self):
        out = _call(_conn(), "get_training_summary", {"start_date": "2026-09-01", "end_date": "2026-09-07"})
        assert out["totals"]["runs"] == 0 and "error" not in out

    def test_monday_week_start(self):
        conn = _conn(); self._seed_block(conn)
        out = _call(conn, "get_training_summary",
                    {"start_date": "2026-08-30", "end_date": "2026-09-20", "week_start": "mon"})
        assert all(date.fromisoformat(r["week"]).weekday() == 0 for r in _rows(out))
        assert "Mon" in out["unit"]


class TestWorkoutTypeFromTextValue:
    """분류는 metric_store.text_value에 저장된다 (numeric_value는 NULL)."""

    def test_get_activity_reports_workout_type(self):
        conn = _conn()
        _act(conn, 5, "2026-09-12", wtype="race", name="Forest run")
        out = _call(conn, "get_activity", {"date": "2026-09-12"})
        assert out["activities"][0]["workout_type"] == "race"

    def test_race_history_matches_classified_race_without_keyword_in_name(self):
        conn = _conn()
        _act(conn, 5, "2026-09-12", wtype="race", name="Forest run")
        out = _call(conn, "get_race_history", {})
        assert len(out["races"]) == 1


class TestWeather:
    def test_columnar_and_empty(self):
        conn = _conn()
        assert _call(conn, "get_weather", {"date": "2026-09-12"})["rows"] == []
        conn.execute(
            "INSERT INTO weather_cache (date, hour, latitude, longitude, temp_c, humidity_pct, "
            "wind_speed_ms, cloud_cover_pct, condition_text) VALUES ('2026-09-12', 7, 37.5, 127, 18.26, 60, 2.0, 30, '맑음')")
        out = _call(conn, "get_weather", {"date": "2026-09-12"})
        assert _rows(out)[0]["temp_c"] == 18.3 and _rows(out)[0]["condition"] == "맑음"


class TestDeclarations:
    def test_all_tools_execute_without_error_on_empty_db(self):
        conn = _conn()
        sample = {"date": "2026-09-12", "start_date": "2026-09-01", "end_date": "2026-09-20",
                  "activity_id": 1, "metric_name": "ctl", "days": 30,
                  "period_a_start": "2026-08-01", "period_a_end": "2026-08-31",
                  "period_b_start": "2026-09-01", "period_b_end": "2026-09-20"}
        for t in TOOL_DECLARATIONS:
            args = {k: sample[k] for k in t["parameters"].get("properties", {}) if k in sample}
            out = _call(conn, t["name"], args)
            assert not (isinstance(out, dict) and "error" in out), (t["name"], out)

    def test_list_tools_expose_granularity(self):
        names = {t["name"] for t in TOOL_DECLARATIONS
                 if "granularity" in t["parameters"]["properties"]}
        assert names == {"get_activities_range", "get_metrics_trend", "get_wellness", "get_fitness"}

    def test_response_json_has_no_padding_whitespace(self):
        out = execute_tool(_conn(), "get_training_summary", {"start_date": "2026-09-01", "end_date": "2026-09-07"})
        assert '": ' not in out and '", "' not in out
