"""coach_evidence 테스트 — 답변 근거 v2 (role·스냅샷·drift·legacy)."""
from __future__ import annotations

from src.services import coach_evidence as ce

DAY = "2026-09-30"


def _metric(conn, date, name, value, version="pmc_v1", updated="2026-09-25 10:51:00"):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value,"
        " is_primary, algorithm_version, updated_at) VALUES ('daily', ?, ?, 'runpulse', ?, 1, ?, ?)",
        (date, name, value, version, updated))


def _wellness(conn, date, bb=None, sleep=None):
    conn.execute("INSERT INTO daily_wellness (date, body_battery_high, sleep_score) VALUES (?, ?, ?)",
                 (date, bb, sleep))


def _checkin(conn, date, fatigue=None, pain=None):
    conn.execute("INSERT INTO user_inputs (input_date, input_type, fatigue, pain) VALUES (?, 'checkin', ?, ?)",
                 (date, fatigue, pain))


class TestPureHelpers:
    def test_rest_signal(self):
        assert ce._rest_signal("tsb", -20) is True
        assert ce._rest_signal("tsb", -12) is None
        assert ce._rest_signal("tsb", 5) is False
        assert ce._rest_signal("body_battery", 30) is True
        assert ce._rest_signal("utrs", 60) is None
        assert ce._rest_signal("tsb", None) is None

    def test_is_drifted_threshold_and_sign(self):
        assert ce.is_drifted(-10.7, -3.3) is True      # 변화 7.4 ≥ max(5, 2.7)
        assert ce.is_drifted(-10.7, -8.0) is False     # 변화 2.7
        assert ce.is_drifted(100, 120) is False        # 20 < 25
        assert ce.is_drifted(100, 130) is True         # 30 ≥ 25
        assert ce.is_drifted(-1.0, 1.0) is True        # 부호 반전
        assert ce.is_drifted(None, 3) is False

    def test_cited_needs_keyword_and_number(self):
        item = {"metric": "tsb", "value": -10.7}
        assert ce._cited("TSB가 -10.7로 낮아요", item)
        assert ce._cited("폼이 −10.7 정도", item)
        assert not ce._cited("TSB가 낮아요", item)
        assert not ce._cited("오늘은 12.3km 달려요", item)
        assert not ce._cited("수면이 -10.7", item)

    def test_cited_rounding_tolerance(self):
        assert ce._cited("tsb -11", {"metric": "tsb", "value": -10.7})
        assert not ce._cited("tsb -14", {"metric": "tsb", "value": -10.7})


class TestBuildAnswerEvidence:
    def test_rule_path_roles_and_snapshot(self, db_conn):
        _metric(db_conn, DAY, "tsb", -20.0)
        _wellness(db_conn, DAY, bb=30, sleep=80)
        _checkin(db_conn, DAY, fatigue=3)
        items = ce.build_answer_evidence(db_conn, "쉬세요", llm=False, as_of=DAY)
        by = {i["metric"]: i for i in items}
        assert by["tsb"]["role"] == "supports"
        assert by["tsb"]["drill"] == {"scope_type": "daily", "scope_id": DAY}
        assert by["tsb"]["snapshot"]["version"] == "pmc_v1"
        assert by["tsb"]["snapshot"]["computed_at"] == "2026-09-25 10:51:00"
        assert by["body_battery"]["drill"] is None
        assert by["checkin"]["pinned"] is True
        assert by["checkin"]["role"] == "caveat"   # 피로 3은 진행 신호 ↔ 쉬라는 판정
        assert items[-1]["role"] == "caveat"       # caveat는 뒤로

    def test_llm_path_keeps_only_cited_and_pinned(self, db_conn):
        _metric(db_conn, DAY, "tsb", -20.0)
        _wellness(db_conn, DAY, bb=30, sleep=40)
        _checkin(db_conn, DAY, fatigue=8)
        items = ce.build_answer_evidence(db_conn, "TSB -20이라 쉬는 게 좋아요", llm=True, as_of=DAY)
        assert {i["metric"] for i in items} == {"tsb", "checkin"}

    def test_exception_returns_empty(self):
        assert ce.build_answer_evidence(None, "x", llm=False, as_of=DAY) == []

    def test_dedupes_by_metric(self, db_conn):
        _metric(db_conn, DAY, "tsb", -20.0)
        items = ce.build_answer_evidence(db_conn, "tsb -20", llm=True, as_of=DAY)
        assert [i["metric"] for i in items].count("tsb") == 1


class TestViewEvidence:
    def _msg(self, items, created_at="2026-09-25 16:00:00"):
        return {"role": "assistant", "evidence": items, "created_at": created_at, "as_of": None}

    def test_legacy_without_snapshot(self, db_conn):
        msg = self._msg([{"type": "metric", "metric": "tsb", "value": -5, "label": "TSB -5",
                          "drill": {"scope_type": "daily", "scope_id": "2026-09-25"}}])
        ce.view_evidence(db_conn, msg)
        assert msg["evidence_legacy"] is True
        assert msg["evidence"][0]["role"] == "legacy"
        assert msg["evidence"][0]["drill"] is None
        assert msg["as_of"] == "2026-09-26"   # KST 변환(+9h)

    def test_user_message_and_empty(self, db_conn):
        m1 = {"role": "user", "evidence": [{"metric": "x"}]}
        m2 = self._msg([])
        ce.view_evidence(db_conn, m1)
        ce.view_evidence(db_conn, m2)
        assert m1["evidence_legacy"] is False and m2["evidence_legacy"] is False

    def test_drift_detected_after_recalc(self, db_conn):
        _metric(db_conn, DAY, "tsb", -20.0)
        items = ce.build_answer_evidence(db_conn, "쉬세요", llm=False, as_of=DAY)
        db_conn.execute("UPDATE metric_store SET numeric_value=-3.3, updated_at='2026-09-27 11:57:00'"
                        " WHERE metric_name='tsb'")
        msg = self._msg(items)
        ce.view_evidence(db_conn, msg)
        tsb = next(i for i in msg["evidence"] if i["metric"] == "tsb")
        assert msg["evidence_legacy"] is False
        assert tsb["drifted"] is True
        assert tsb["current"]["value"] == -3.3
        assert tsb["current"]["display"] == "\u22123.3"
        assert tsb["snapshot"]["value"] == -20.0

    def test_no_drift_when_unchanged(self, db_conn):
        _metric(db_conn, DAY, "tsb", -20.0)
        items = ce.build_answer_evidence(db_conn, "쉬세요", llm=False, as_of=DAY)
        msg = self._msg(items)
        ce.view_evidence(db_conn, msg)
        tsb = next(i for i in msg["evidence"] if i["metric"] == "tsb")
        assert tsb["drifted"] is False

    def test_wellness_current(self, db_conn):
        _wellness(db_conn, DAY, bb=30)
        item = {"type": "wellness", "metric": "body_battery", "value": 30, "label": "BB 30",
                "snapshot": {"value": 30, "as_of": DAY}}
        db_conn.execute("UPDATE daily_wellness SET body_battery_high=80")
        out = ce.with_current(db_conn, item)
        assert out["current"]["value"] == 80
        assert out["drifted"] is True

    def test_kst_date_invalid(self):
        assert ce._kst_date(None) is None
        assert ce._kst_date("garbage") is None


def test_adjustment_in_effect_follows_state(monkeypatch):
    import src.services.plan_adjustment_service as pas

    for state, expected in (("accepted", True), ("proposed", True), ("none", True),
                            ("declined", False), ("undone", False), ("stale", False), ("expired", False)):
        monkeypatch.setattr(pas, "get_day_adjustment", lambda *a, _s=state, **k: {"state": _s, "adjustment": None})
        assert ce._adjustment_in_effect(None, "2026-10-08") is expected
