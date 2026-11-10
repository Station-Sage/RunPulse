"""V2-AUDIT-INDIV 묶음 C(지표·웰니스·이야기·소스 비교) 서버 측 수정 테스트."""
from __future__ import annotations

from datetime import date, timedelta

from src.metrics.algo_changelog import AlgoChange
from src.services import metrics_changelog_events as mce
from src.services.metric_display import display_meta
from src.services.metrics_explain import _baseline
from src.services.provider_matrix_collect import signed_pct, summarize_pairs
from src.services.provider_matrix_service import mark_lagging
from src.services.story_compare import compare_basis
from src.services.story_stats import _get_risk_peak
from src.services.wellness_day import _headline
from src.utils.korean_josa import has_final, josa
from src.utils.metric_labels import METRIC_LABELS


def _metric(conn, d, name, v, provider="runpulse:formula_v1"):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value, is_primary)"
        " VALUES ('daily', ?, ?, 'x', ?, ?, 1)", (d, name, provider, v))


def test_display_meta_formats_m10_m21():
    assert display_meta("acwr", "")["decimal_places"] == 2
    assert display_meta("utrs", "")["format"] == "score"
    assert display_meta("utrs", "")["decimal_places"] == 0
    assert display_meta("sleep_deep_sec", "sec")["format"] == "duration_hm"
    assert display_meta("x", "sec")["format"] == "duration"
    assert display_meta("ctl", "")["decimal_places"] == 1


def test_josa_m31():
    assert josa("수면", "이", "가") == "수면이"
    assert josa("폼", "이", "가") == "폼이"
    assert josa("심박변이(HRV)", "이", "가") == "심박변이(HRV)가"
    assert josa("바디 배터리", "이", "가") == "바디 배터리가"
    assert has_final("") is None
    assert josa("…", "이", "가") == "…이(가)"


def test_merge_reasons_groups_same_input_m31():
    hits = [(AlgoChange("trimp", "v2", "2026-09-28", "A", "v1"), "tsb"),
            (AlgoChange("ctl", "2.0", "2026-09-28", "B", "1.0"), "tsb"),
            (AlgoChange("utrs", "v2", "2026-09-28", "C", "v1"), None)]
    text = mce._merge_reasons(hits)
    assert text.count("입력 지표(") == 1
    assert text.startswith("C; 입력 지표(") and text.endswith("A, B")


def test_explain_avg7d_uses_seven_days_m11(db_conn):
    d0 = date(2026, 4, 30)
    for i in range(8):  # d-7..d, d-7 은 창 밖
        _metric(db_conn, (d0 - timedelta(days=i)).isoformat(), "utrs", 100.0 if i == 7 else 70.0)
    b = _baseline(db_conn, "daily", d0.isoformat(), "utrs")
    assert b["avg_7d"] == 70.0


def test_compare_basis_partial_month_m14():
    b = compare_basis("month", "2026-10-01", "2026-10-11", "2026-09-01", "2026-09-30", "2026-10-11")
    assert b["partial"] is True and b["prev_end"] == "2026-09-11"
    assert "11일(1~11일)" in b["label"]
    full = compare_basis("month", "2026-09-01", "2026-09-30", "2026-08-01", "2026-08-31", "2026-10-11")
    assert full == {"prev_end": "2026-08-31", "partial": False, "label": None}


def test_story_future_month_has_no_next_and_no_compare_m16(db_conn):
    from src.services.story_service import get_story
    nxt = (date.today().replace(day=1) + timedelta(days=40)).replace(day=1)
    s = get_story(db_conn, f"{nxt.year}-{nxt.month:02d}")
    assert s["is_future"] is True and s["compare"] == [] and s["period"]["next"] is None
    cur = get_story(db_conn, date.today().strftime("%Y-%m"))
    assert cur["period"]["next"] is None and cur["is_future"] is False


def test_risk_peak_carries_grade_m15(db_conn):
    _metric(db_conn, "2026-09-10", "acwr", 0.86)
    r = _get_risk_peak(db_conn, "2026-09-01", "2026-09-30")
    assert r["status"] == "good" and r["status_label"] == "적정"


def test_headline_adds_cirs_caveat_m17():
    ready = {"utrs": {"status": "good", "status_label": "좋음"}, "cirs": {"status": "caution", "status_label": "높음"}}
    h = _headline(ready, [])
    assert h["text"].startswith("회복 좋음") and "부상 위험(CIRS)은 '높음'이에요" in h["text"]
    assert _headline({"utrs": None, "cirs": {"status": "good", "status_label": "낮음"}}, [])["caveat"] is None


def test_signed_pct_and_lagging_m19():
    assert signed_pct(-0.3) == "0%"
    assert signed_pct(-0.04, 1) == "0.0%"
    assert signed_pct(12.6) == "+13%"
    d = summarize_pairs([(1.0, 1.0001)] * 3, "garmin", "runpulse", "same", 15)
    assert "(중앙 차이 0.0%)" in d["explain_text"]
    cells = mark_lagging({"garmin": {"last_date": "2026-09-27"}, "runpulse": {"last_date": "2026-10-11"}})
    assert cells["garmin"]["lagging"] is True and cells["runpulse"]["lagging"] is False
    assert mark_lagging({"garmin": {"last_date": "2026-09-27"}})["garmin"]["lagging"] is False


def test_second_batch_descriptions_m07():
    for n in ("rec", "steps", "sleep_deep_sec", "avg_spo2", "heat_model", "training_response"):
        assert METRIC_LABELS[n].description_short
    # 1차분 문구는 덮지 않는다
    assert METRIC_LABELS["sleep_score"].description_short == "지난밤 수면의 종합 점수"


def test_trend_reports_source_m08(db_conn, monkeypatch):
    from src.services import metrics_trend_service as mts
    today = date(2026, 4, 30)
    monkeypatch.setattr(mts, "_today", lambda: today)
    _metric(db_conn, today.isoformat(), "rec", 1.1, provider="garmin")
    db_conn.execute("INSERT INTO daily_wellness (date, sleep_score) VALUES (?, 80)", (today.isoformat(),))
    assert mts.get_metric_trend(db_conn, "rec")["source"] == "garmin"
    assert mts.get_metric_trend(db_conn, "sleep_score")["source"] == "wellness"
