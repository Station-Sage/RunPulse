"""tests/test_hr_zone_bpm.py — 플랜 심박존 → LTHR 기준 bpm 구간."""
from __future__ import annotations

import sqlite3

from src.db_setup import create_tables
from src.training.hr_zone_bpm import latest_lthr, zone_bpm


def _conn(lthr=None):
    c = sqlite3.connect(":memory:")
    create_tables(c)
    if lthr:
        c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary) "
                  "VALUES ('daily','2026-11-10','lthr_self','runpulse:formula_v1',?,1)", (lthr,))
    return c


def test_no_lthr_returns_none():
    c = _conn()
    assert latest_lthr(c) is None
    assert zone_bpm(c, 2) is None


def test_zone_ranges_from_lthr():
    c = _conn(170)
    assert zone_bpm(c, 2) == {"zone": 2, "lo": 144, "hi": 153, "lthr": 170}
    assert zone_bpm(c, "Z1")["hi"] == 144
    assert zone_bpm(c, 5)["hi"] is None


def test_invalid_zone():
    c = _conn(170)
    assert zone_bpm(c, None) is None
    assert zone_bpm(c, 9) is None
    assert zone_bpm(c, "x") is None
