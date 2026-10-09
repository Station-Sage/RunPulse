"""plan_overlay: accepted 조정만 읽기 시점에 적용, 원본 불변, 지문 불일치는 stale."""
import json
import sqlite3

from src.db_schema_v31 import ensure_v31
from src.training.plan_overlay import apply, live_adjustments

ROW = {"id": 7, "date": "2026-10-08", "workout_type": "interval", "distance_km": 10.0,
       "target_pace_min": 4.5, "target_pace_max": 4.8, "description": "x"}


def _conn(decision="accepted", op="replace", before=None, after=None):
    c = sqlite3.connect(":memory:")
    ensure_v31(c)
    b = before or {"workout_type": "interval", "distance_km": 10.0}
    a = after or {"workout_type": "easy", "target_pace_min": None, "target_pace_max": None}
    c.execute("INSERT INTO plan_adjustments(workout_id,date,source,op,before_json,after_json,rule_version,decision)"
              " VALUES (7,'2026-10-08','crs',?,?,?,'adjuster_v1',?)", (op, json.dumps(b), json.dumps(a), decision))
    return c


def test_only_accepted_listed():
    assert 7 in live_adjustments(_conn(), "2026-10-05", "2026-10-12")
    assert live_adjustments(_conn("proposed"), "2026-10-05", "2026-10-12") == {}
    assert live_adjustments(_conn(), "2026-10-09", "2026-10-12") == {}


def test_apply_overrides_and_keeps_original():
    adjs = live_adjustments(_conn(), "2026-10-05", "2026-10-12")
    out = apply([ROW], adjs)[0]
    assert out["workout_type"] == "easy" and out["distance_km"] == 10.0 and out["adjusted"]
    assert out["original"]["workout_type"] == "interval"
    assert ROW["workout_type"] == "interval" and "adjusted" not in ROW


def test_fingerprint_mismatch_is_stale():
    adjs = live_adjustments(_conn(), "2026-10-05", "2026-10-12")
    out = apply([{**ROW, "distance_km": 12.0}], adjs)[0]
    assert out["adjustment_stale"] and out["workout_type"] == "interval" and "adjusted" not in out


def test_move_applies_and_unadjusted_untouched():
    adjs = live_adjustments(_conn(op="move", after={"date": "2026-10-10"}), "2026-10-05", "2026-10-12")
    out = apply([ROW], adjs)[0]
    assert out["date"] == "2026-10-10" and out["original"]["date"] == "2026-10-08" and out["workout_type"] == "interval"
    assert apply([{**ROW, "id": 8}], live_adjustments(_conn(), "2026-10-05", "2026-10-12")) == [{**ROW, "id": 8}]
