from src.training import constraints as C


def _w(d, t, km, pace=None):
    return {"date": d, "workout_type": t, "distance_km": km, "target_pace_min": pace, "target_pace_max": pace}


WEEK = [_w("2026-10-05", "easy", 8, 360), _w("2026-10-06", "tempo", 10, 300), _w("2026-10-07", "easy", 8, 360),
        _w("2026-10-08", "rest", 0), _w("2026-10-09", "easy", 8, 360), _w("2026-10-10", "easy", 6, 360),
        _w("2026-10-11", "long", 20, 370)]


def test_heat_moves_quality_and_keeps_km():
    out = C.heat_adjust(WEEK, {"2026-10-06": 4.0, "2026-10-05": 3.0, "2026-10-07": 0.0})
    q = next(r for r in out if r["workout_type"] == "tempo")
    assert q["date"] == "2026-10-07" and q["distance_km"] == 10
    hot = C.heat_adjust(WEEK, {"2026-10-11": 5.0})
    assert next(r for r in hot if r["workout_type"] == "long")["target_pace_min"] == 388.5
    assert WEEK[6]["target_pace_min"] == 370


def test_heat_below_threshold_noop():
    assert C.heat_adjust(WEEK, {"2026-10-05": 1.5}) == sorted(WEEK, key=lambda r: r["date"])


def test_blocked_redistribute_cap():
    out = C.redistribute_blocked(WEEK, {"2026-10-06"})
    assert next(r for r in out if r["date"] == "2026-10-06")["workout_type"] == "rest"
    assert all(r["distance_km"] <= 12 for r in out if r["workout_type"] == "easy")
    assert sum(r["distance_km"] for r in out) <= sum(r["distance_km"] for r in WEEK)


def test_b_race_week():
    out = C.b_race_week(WEEK, "2026-10-10", 10)
    assert next(r for r in out if r["date"] == "2026-10-10")["workout_type"] == "race"
    assert next(r for r in out if r["date"] == "2026-10-11")["workout_type"] == "rest"
    assert next(r for r in out if r["date"] == "2026-10-09")["workout_type"] == "easy"
    assert next(r for r in out if r["date"] == "2026-10-05")["distance_km"] == 6.4


def test_cross_substituted():
    assert C.cross_substituted(WEEK, {"2026-10-05", "2026-10-08"}) == {"2026-10-05"}


def test_race_impact_windows_and_protection():
    rows = [dict(r) for r in WEEK]
    rows[0]["completed"] = 1  # 10-05 완료 행은 보호
    race = {"race_date": "2026-10-10", "distance_km": 10}
    out = {c["before"]["date"]: c["after"] for c in C.race_impact(rows, race, (4, 2))}
    assert "2026-10-05" not in out and "2026-10-08" not in out  # 완료·rest 보호
    assert out["2026-10-06"]["distance_km"] == 8.0 and out["2026-10-06"]["workout_type"] == "tempo"
    assert out["2026-10-09"]["workout_type"] == "easy"
    assert out["2026-10-10"]["workout_type"] == "race"
    assert out["2026-10-11"]["workout_type"] == "rest"


def test_race_impact_empty_outside_window():
    assert C.race_impact(WEEK, {"race_date": "2026-12-01", "distance_km": 10}, (3, 2)) == []
