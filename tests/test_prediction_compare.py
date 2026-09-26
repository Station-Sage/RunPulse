"""P7-PRED-71: 3경로 비교 서비스."""
from src.services.prediction_compare_service import compare
from src.utils.db_helpers import upsert_metric
from tests.helpers_pred import mem_conn


def _seed(c):
    upsert_metric(c, "daily", "2026-05-11", "race_pred_10k_sec", "garmin", numeric_value=2585)
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:ref_garmin", numeric_value=2741,
                  json_value={"low_s": 2602, "high_s": 2879, "confidence": 0.75, "reasons": [], "contributions": {}})
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739,
                  json_value={"low_s": 2601, "high_s": 2878, "confidence": 0.75, "reasons": ["기준 대회가 20주 전"]})
    upsert_metric(c, "daily", "2026-09-26", "hr_profile", "runpulse:formula_v1", numeric_value=177.4,
                  json_value={"self": {"lthr": 177.4}, "ref": {"lthr": 177.0}, "lthr_gap": 0.4})


def test_three_rows_and_notes():
    c = mem_conn()
    _seed(c)
    r = compare(c, "10k", "2026-09-26")
    assert [x["value_sec"] for x in r["rows"]] == [2585, 2741, 2739]
    assert r["rows"][0]["stale_days"] == 138
    assert r["notes"][0].startswith("Garmin 예측이 자체 추정보다 5.6% 빠름")
    assert r["notes"][1] == "Garmin 값은 138일 전 스냅샷"
    assert "영향 작음" in r["notes"][2] and r["hr_basis"]["lthr_gap"] == 0.4


def test_missing_paths():
    c = mem_conn()
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739)
    r = compare(c, "10k", "2026-09-26")
    assert r["rows"][0]["value_sec"] is None
    assert r["notes"] == ["Garmin 예측 없음(동기화 필요)", "기기 심박 기준값 없음 — 기기 LTHR 미수집"]


def test_race_hub_includes_compare():
    from src.services.race_hub_service import get_race_hub
    c = mem_conn()
    _seed(c)
    c.execute("INSERT INTO goals (name, race_date, distance_km, target_time_sec, status) "
              "VALUES ('가을 10K', '2026-11-01', 10.0, 2700, 'active')")
    hub = get_race_hub(c, "2026-09-26")
    assert hub["prediction"]["value_sec"] == 2739
    assert [r["value_sec"] for r in hub["prediction"]["compare"]["rows"]] == [2585, 2741, 2739]


def test_profile_reads_latest():
    from src.services.prediction_compare_service import profile
    c = mem_conn()
    _seed(c)
    p = profile(c, "2026-09-30")
    assert p["hr_profile"]["date"] == "2026-09-26" and p["hr_profile"]["lthr_gap"] == 0.4 and p["heat_model"] is None


def test_shadow_candidates_only_when_present():
    """P7-PRED-71: r4 섀도는 값이 있을 때만 candidate 행으로 붙는다(기본 'self' 는 r3)."""
    import sqlite3
    from src.db_setup import create_tables
    from src.services.prediction_compare_service import compare
    from src.utils.db_helpers import upsert_metric
    c = sqlite3.connect(":memory:")
    create_tables(c)
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:formula_v1", numeric_value=2739)
    assert [r["key"] for r in compare(c, "10k", "2026-09-26")["rows"]] == ["garmin", "ref", "self"]
    upsert_metric(c, "daily", "2026-09-26", "race_pred_10k_sec", "runpulse:shadow_r4", numeric_value=2775,
                  json_value={"contributions": {"T": 0.4}})
    rows = compare(c, "10k", "2026-09-26")["rows"]
    assert rows[-1]["key"] == "r4" and rows[-1]["candidate"] is True and rows[-1]["value_sec"] == 2775
