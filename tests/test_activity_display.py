"""activity_display.build_display 단위 테스트 (NRA-3/4/5)."""
from src.services.activity_display import build_display


def _core(t, **kw):
    return {"activity_type": t, "distance_m": 10000, "duration_sec": 3600, "moving_time_sec": 3000,
            "elapsed_time_sec": 3600, **kw}


def test_running_pace_moving_basis():
    d = build_display(_core("running"))
    assert d["family"] == "running" and d["show_distance"]
    assert d["pace"] == {"value_sec": 300.0, "unit": "/km", "basis": "moving"}
    assert d["times"] == {"moving_sec": 3000, "elapsed_sec": 3600}


def test_elapsed_fallback_basis():
    d = build_display(_core("running", moving_time_sec=None))
    assert d["pace"]["basis"] == "elapsed" and d["pace"]["value_sec"] == 360.0


def test_swimming_per_100m():
    d = build_display(_core("lap_swimming", distance_m=1000, moving_time_sec=1800))
    assert d["pace"] == {"value_sec": 180.0, "unit": "/100m", "basis": "moving"}


def test_strength_hides_distance_and_pace():
    d = build_display(_core("strength_training", avg_hr=110, calories=300), sets=12)
    assert not d["show_distance"] and d["pace"] is None and d["speed_kmh"] is None
    assert [f["key"] for f in d["alt_fields"]] == ["duration", "avg_hr", "calories", "sets"]


def test_cycling_speed():
    d = build_display(_core("cycling", distance_m=30000, moving_time_sec=3600))
    assert d["speed_kmh"] == 30.0 and d["pace"] is None


def test_walking_pace_km():
    assert build_display(_core("walking"))["pace"]["unit"] == "/km"


def test_hiit_is_other():
    d = build_display(_core("hiit", distance_m=0))
    assert d["family"] == "other" and not d["show_distance"]


def test_unknown_type_is_other_and_alt_only_existing():
    d = build_display({"activity_type": "zzz", "duration_sec": 600})
    assert d["family"] == "other" and d["alt_fields"] == [{"key": "duration", "value": 600}]


def test_times_equal_when_no_moving():
    d = build_display({"activity_type": "running", "distance_m": 1000, "duration_sec": 300})
    assert d["times"]["moving_sec"] == d["times"]["elapsed_sec"] == 300
