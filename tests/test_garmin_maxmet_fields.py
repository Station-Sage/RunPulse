from src.sync.extractors.garmin_extractor import GarminExtractor
from src.sync.extractors.garmin_maxmet_fields import extract_vo2max_daily


def _item(day, precise, integer=None):
    return {"generic": {"calendarDate": day, "vo2MaxPreciseValue": precise,
                        "vo2MaxValue": integer, "maxMetCategory": 0}}


def test_normal_list_by_date():
    out = extract_vo2max_daily(GarminExtractor(), [_item("2026-10-09", 53.9, 54.0)])
    rec = out["2026-10-09"][0]
    assert rec.metric_name == "vo2max" and rec.numeric_value == 53.9
    assert rec.raw_name == "vo2MaxPreciseValue"


def test_integer_fallback_when_no_precise():
    out = extract_vo2max_daily(GarminExtractor(), [_item("2026-10-09", None, 54.0)])
    assert out["2026-10-09"][0].numeric_value == 54.0
    assert out["2026-10-09"][0].raw_name == "vo2MaxValue"


def test_skips_missing_generic_and_empty():
    assert extract_vo2max_daily(GarminExtractor(), []) == {}
    assert extract_vo2max_daily(GarminExtractor(), None) == {}
    assert extract_vo2max_daily(GarminExtractor(), [{"generic": None}, {}]) == {}


def test_invalid_values_ignored():
    items = [_item("2026-10-01", "x", None), _item("2026-10-02", True, None), _item("2026-10-03", 0, 0)]
    assert extract_vo2max_daily(GarminExtractor(), items) == {}
