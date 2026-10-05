"""U16f: R7 주간 구조(순수 함수)."""
from src.training import week_structure as W


def _row(d, t, km, pace=None):
    return {"date": d, "workout_type": t, "distance_km": km, "target_pace_min": pace}


def test_default_run_days_median_and_clamp():
    assert W.default_run_days([4, 4, 5, 3, 4, 4, 4, 4]) == 4
    assert W.default_run_days([1, 2, 2]) == 3
    assert W.default_run_days([7, 7, 7]) == 6
    assert W.default_run_days([]) == 4


def test_long_ratio_branches():
    assert W.long_ratio(50, 23) == 0.45       # 50km 미만 60, 최장 22.5 이상
    assert W.long_ratio(50, 15) == 0.35
    assert W.long_ratio(70, 40) == 0.35       # 60km 이상은 0.35


def test_long_cap_design_example():
    assert W.long_cap_km(50, 360, 0) == 17.5
    assert W.long_cap_km(50, 360, 23) == 22.5          # min(22.5, 25.0, 32)
    assert W.long_cap_km(100, 360, 0) == 25.0


def test_long_cap_by_time():
    assert W.long_cap_km(100, 420, 0) == 150 * 60 / 420


def test_short_session_merged_to_rest_and_redistributed_to_easy():
    rows = [_row("2026-01-05", "easy", 4.0), _row("2026-01-06", "easy", 8.0),
            _row("2026-01-07", "long", 16.0)]
    out = W.apply_week_structure(rows, 3, 28, 360)
    assert out[0]["workout_type"] == "rest" and out[0]["distance_km"] == 0.0
    assert out[1]["distance_km"] == 12.0            # 8 + 4, 이지 12km 이내
    assert rows[0]["workout_type"] == "easy"          # 입력 불변


def test_shakeout_before_race_kept():
    rows = [_row("2026-11-21", "easy", 4.0), _row("2026-11-22", "race", 42.2)]
    out = W.apply_week_structure(rows, 2, 46, 360, race_date="2026-11-22")
    assert out[0]["workout_type"] == "easy" and out[0]["distance_km"] == 4.0


def test_long_run_capped_and_excess_to_easy():
    rows = [_row("2026-01-05", "easy", 8.0), _row("2026-01-07", "easy", 8.0), _row("2026-01-11", "long", 24.0)]
    out = W.apply_week_structure(rows, 3, 50, 360, long_max_12w=0)
    assert out[2]["distance_km"] == 17.5 and out[0]["distance_km"] == 12.0 and out[1]["distance_km"] == 10.5


def test_recap_long_when_pool_left_over():
    rows = [_row("2026-01-05", "easy", 8.0), _row("2026-01-11", "long", 24.0)]
    out = W.apply_week_structure(rows, 2, 50, 360, long_max_12w=0)
    total = sum(r["distance_km"] for r in out)
    assert out[1]["distance_km"] <= 0.35 * total + 0.1


def test_feasible_week_km_grows_with_days():
    assert W.feasible_week_km(3) < W.feasible_week_km(4) < W.feasible_week_km(6)


def test_run_days_surplus_trims_smallest_easy():
    rows = [_row("2026-01-05", "easy", 7.0), _row("2026-01-06", "easy", 9.0),
            _row("2026-01-07", "tempo", 10.0), _row("2026-01-11", "long", 16.0)]
    out = W.apply_week_structure(rows, 3, 42, 360)
    assert sum(r["workout_type"] != "rest" for r in out) == 3
    assert out[0]["workout_type"] == "rest"


def test_min_pass_by_minutes():
    r = _row("2026-01-05", "easy", 5.5, pace=400)   # 36.7분 → 유지
    out = W.apply_week_structure([r, _row("2026-01-11", "long", 14.0)], 2, 20, 360)
    assert out[0]["workout_type"] == "easy"
