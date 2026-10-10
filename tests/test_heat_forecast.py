"""예보 기온 → 폭염 보정(E10) 순수 변환."""
from src.services import heat_forecast as H


def test_morning_temps_and_pct():
    h = {"time": ["2026-10-12T05:00", "2026-10-12T06:00", "2026-10-12T08:00", "2026-10-12T12:00"],
         "temperature_2m": [10, 24, 26, 35]}
    t = H.morning_temps(h)
    assert t == {"2026-10-12": 25.0}
    assert H.heat_pcts(t) == {"2026-10-12": 6.2}
    assert H.heat_pcts({"d": 12.0}) == {"d": 0.0}
