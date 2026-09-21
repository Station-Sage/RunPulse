"""도구 응답 압축 헬퍼 — columnar, 반올림, 주별 롤업."""
from src.ai.tool_format import (
    AUTO_WEEKLY_OVER_DAYS, MAX_DAILY_DAYS, columnar, num, resolve_granularity,
    span_days, week_start_of, weekly_activity_rows, weekly_last, weekly_mean,
)


class TestNum:
    def test_integer_valued_float_becomes_int(self):
        assert num(84.0) == 84 and isinstance(num(84.0), int)

    def test_rounds_to_digits(self):
        assert num(7.7425, 1) == 7.7

    def test_none_passthrough(self):
        assert num(None) is None

    def test_integer_after_rounding_drops_decimal(self):
        assert num(6.98, 1) == 7 and isinstance(num(6.98, 1), int)


class TestColumnar:
    def test_rows_follow_fields(self):
        out = columnar(["a", "b"], [[1, 2], [3, 4]])
        assert out == {"fields": ["a", "b"], "rows": [[1, 2], [3, 4]]}

    def test_all_null_column_is_dropped(self):
        out = columnar(["a", "b", "c"], [[1, None, 3], [4, None, None]])
        assert out["fields"] == ["a", "c"]
        assert out["rows"] == [[1, 3], [4, None]]

    def test_empty_rows(self):
        assert columnar(["a"], []) == {"fields": [], "rows": []}


class TestGranularity:
    def test_auto_short_is_daily(self):
        assert resolve_granularity(None, AUTO_WEEKLY_OVER_DAYS) == ("day", None)

    def test_auto_long_is_weekly(self):
        assert resolve_granularity("auto", AUTO_WEEKLY_OVER_DAYS + 1) == ("week", None)

    def test_explicit_day_within_limit(self):
        assert resolve_granularity("day", MAX_DAILY_DAYS) == ("day", None)

    def test_explicit_day_beyond_limit_falls_back_with_note(self):
        gran, note = resolve_granularity("day", MAX_DAILY_DAYS + 1)
        assert gran == "week" and note

    def test_explicit_week(self):
        assert resolve_granularity("week", 7) == ("week", None)

    def test_unknown_value_is_auto(self):
        assert resolve_granularity("month", 10) == ("day", None)

    def test_span_days_inclusive(self):
        assert span_days("2026-09-01", "2026-09-07") == 7


class TestWeekStart:
    def test_sunday_start(self):
        # 2026-09-20 은 일요일
        assert week_start_of("2026-09-20") == "2026-09-20"
        assert week_start_of("2026-09-26") == "2026-09-20"
        assert week_start_of("2026-09-19") == "2026-09-13"

    def test_monday_start(self):
        assert week_start_of("2026-09-20", "mon") == "2026-09-14"
        assert week_start_of("2026-09-21", "mon") == "2026-09-21"

    def test_accepts_timestamp(self):
        assert week_start_of("2026-09-22 07:00:00") == "2026-09-20"


class TestWeeklyActivity:
    def test_totals_pace_and_long_run(self):
        acts = [("2026-09-14", 10.0, 3000, 150), ("2026-09-16", 5.0, 1500, 140),
                ("2026-09-20", 20.0, 6600, 145)]
        rows = weekly_activity_rows(acts, "sun")
        assert rows[0] == ["2026-09-13", 2, 15, 75, "5:00", 147, 10]
        assert rows[1][:3] == ["2026-09-20", 1, 20]

    def test_pace_is_time_over_distance_not_mean_of_paces(self):
        # 1km 4:00 + 10km 6:00 → 단순 평균 5:00 이 아니라 총시간/총거리 ≈ 5:49
        rows = weekly_activity_rows([("2026-09-14", 1.0, 240, None),
                                     ("2026-09-15", 10.0, 3600, None)], "sun")
        assert rows[0][4] == "5:49"

    def test_hr_is_time_weighted(self):
        rows = weekly_activity_rows([("2026-09-14", 1.0, 600, 100),
                                     ("2026-09-15", 1.0, 1800, 160)], "sun")
        assert rows[0][5] == 145

    def test_gap_weeks_are_filled_within_span(self):
        rows = weekly_activity_rows([("2026-09-01", 10.0, 3000, 150),
                                     ("2026-09-22", 10.0, 3000, 150)], "sun",
                                    ("2026-09-01", "2026-09-22"))
        assert [r[0] for r in rows] == ["2026-08-30", "2026-09-06", "2026-09-13", "2026-09-20"]
        assert rows[1][1] == 0 and rows[2][1] == 0

    def test_no_span_keeps_only_active_weeks(self):
        rows = weekly_activity_rows([("2026-09-01", 10.0, 3000, 150),
                                     ("2026-09-22", 10.0, 3000, 150)], "sun")
        assert len(rows) == 2


class TestWeeklyAggregates:
    def test_mean_skips_nulls_and_counts_days(self):
        rows = [["2026-09-14", 80, None], ["2026-09-15", 90, 7.0], ["2026-09-16", None, 8.0]]
        out = weekly_mean(rows, [0, 1], "sun")
        assert out == [["2026-09-13", 3, 85, 7.5]]

    def test_last_takes_final_non_null_per_column(self):
        rows = [["2026-09-14", 70.0, 1.0], ["2026-09-15", 72.0, None], ["2026-09-16", None, None]]
        assert weekly_last(rows, "sun") == [["2026-09-13", 72.0, 1.0]]
