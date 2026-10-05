"""what-if(B-5) 순수 함수 테스트."""
from src.metrics.utrs import UTRSCalculator
from src.services.metrics_explain_whatif import build_what_if, tomorrow_tsb_if_rest, utrs_with_tsb

TODAY = "2026-10-05"


def _terms(tsb_norm=50.0):
    return [
        {"slug": "utrs_body_battery", "normalized": 80.0},
        {"slug": "utrs_tsb", "normalized": tsb_norm},
        {"slug": "utrs_sleep", "normalized": 60.0},
    ]


def test_tsb_one_step_formula():
    assert abs(tomorrow_tsb_if_rest(42.0, 7.0) - (42 * 41 / 42 - 7 * 6 / 7)) < 1e-9
    out = build_what_if("tsb", TODAY, ctl=42.0, atl=70.0, terms=[], today=TODAY)
    assert out[0]["key"] == "rest_today" and out[0]["value_est"] == round(41 - 60)


def test_utrs_only_tsb_term_changes():
    w = UTRSCalculator.WEIGHTS
    new = utrs_with_tsb(_terms(), 0.0)
    tot = w["body_battery"] + w["tsb"] + w["sleep"]
    exp = (80 * w["body_battery"] + 50 * w["tsb"] + 60 * w["sleep"]) / tot
    assert abs(new - exp) < 1e-9
    assert utrs_with_tsb([t for t in _terms() if t["slug"] != "utrs_tsb"], 0.0) is None


def test_past_date_omitted():
    assert build_what_if("tsb", "2026-10-04", ctl=40.0, atl=50.0, terms=[], today=TODAY) == []
    assert build_what_if("ctl", TODAY, ctl=40.0, atl=50.0, terms=[], today=TODAY) == []
