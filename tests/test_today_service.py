"""today_service 테스트 — Phase 7a D5 + Phase 7b L2 내러티브."""
from __future__ import annotations

from unittest.mock import patch

from src.services import today_service


def _seed_metric(conn, date, name, value):
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, "
        "numeric_value, is_primary) VALUES ('daily', ?, ?, 'runpulse', ?, 1)",
        (date, name, value),
    )


def _seed_activity(conn, *, activity_id, start_time, name="Easy Run"):
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, "
        "start_time, distance_m, duration_sec) VALUES (?, 'garmin', ?, ?, 'running', ?, 10000, 3000)",
        (activity_id, str(activity_id), name, start_time),
    )


class TestGetTodayStatus:
    def test_empty_data_returns_none_metrics(self, db_conn):
        status = today_service.get_today_status(db_conn, date="2026-09-22")
        assert status["date"] == "2026-09-22"
        assert status["readiness"]["utrs"] is None
        assert status["training_status"]["tsb"] is None
        assert status["providers"] == {}

    def test_with_metrics(self, db_conn):
        _seed_metric(db_conn, "2026-09-22", "utrs", 72)
        _seed_metric(db_conn, "2026-09-22", "tsb", -4)
        db_conn.commit()

        status = today_service.get_today_status(db_conn, date="2026-09-22")
        assert status["readiness"]["utrs"]["value"] == 72
        assert status["training_status"]["tsb"] == -4

    def test_providers_surfaced_for_metric_cell(self, db_conn):
        """MetricCell(C2)의 P3 요건 — provider 없이 표시되는 숫자는 없다."""
        _seed_metric(db_conn, "2026-09-22", "utrs", 72)
        _seed_metric(db_conn, "2026-09-22", "cirs", 20)
        _seed_metric(db_conn, "2026-09-22", "tsb", -4)
        db_conn.commit()

        status = today_service.get_today_status(db_conn, date="2026-09-22")
        assert status["providers"] == {"utrs": "runpulse", "cirs": "runpulse", "tsb": "runpulse"}


class TestGetRecentActivities:
    def test_empty(self, db_conn):
        assert today_service.get_recent_activities(db_conn) == []

    def test_respects_limit_and_order(self, db_conn):
        _seed_activity(db_conn, activity_id=1, start_time="2026-09-20T06:00:00")
        _seed_activity(db_conn, activity_id=2, start_time="2026-09-21T06:00:00")
        _seed_activity(db_conn, activity_id=3, start_time="2026-09-22T06:00:00")
        db_conn.commit()

        result = today_service.get_recent_activities(db_conn, limit=2)
        assert [r["id"] for r in result] == [3, 2]


class TestGetTodayBriefing:
    def test_no_data_fallback(self, db_conn):
        briefing = today_service.get_today_briefing(db_conn, date="2026-09-22")
        assert "수집 중" in briefing["headline"]
        assert briefing["evidence"] == []

    def test_low_tsb_recommends_rest(self, db_conn):
        _seed_metric(db_conn, "2026-09-22", "tsb", -25)
        db_conn.commit()
        briefing = today_service.get_today_briefing(db_conn, date="2026-09-22")
        assert "휴식" in briefing["headline"] or "회복" in briefing["headline"]
        assert briefing["evidence"][0]["metric"] == "tsb"

    def test_balanced_tsb(self, db_conn):
        _seed_metric(db_conn, "2026-09-22", "tsb", -4)
        db_conn.commit()
        briefing = today_service.get_today_briefing(db_conn, date="2026-09-22")
        assert "균형" in briefing["evidence"][0]["label"]


class TestGetTodaysCheckin:
    def test_no_checkin_returns_none(self, db_conn):
        assert today_service.get_todays_checkin(db_conn, date="2026-09-22") is None

    def test_returns_saved_checkin(self, db_conn):
        today_service.save_checkin(db_conn, fatigue=6, pain="none", input_date="2026-09-22")
        result = today_service.get_todays_checkin(db_conn, date="2026-09-22")
        assert result["fatigue"] == 6
        assert result["pain"] == "none"

    def test_defaults_to_today_date(self, db_conn):
        # date 미지정 시 SQLite date('now') 기준 — 오늘 체크인이 없으면 None.
        assert today_service.get_todays_checkin(db_conn) is None


class TestGetTodayMilestones:
    def test_empty(self, db_conn):
        result = today_service.get_today_milestones(db_conn)
        assert result == []

    def test_returns_milestones(self, db_conn):
        db_conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('distance_threshold', '2026-09-01', '누적 100km 돌파')"
        )
        db_conn.commit()
        result = today_service.get_today_milestones(db_conn, limit=5)
        assert len(result) == 1
        assert result[0]["title"] == "누적 100km 돌파"


class TestGetTodayNarrative:
    def test_no_data_rule_fallback(self, db_conn):
        """AI 미설정(config=None) + 데이터 없음 → 규칙 기반 fallback."""
        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert result["source"] == "rule"
        assert isinstance(result["text"], str)
        assert len(result["text"]) > 0
        assert result["date"] == "2026-09-22"
        assert isinstance(result["evidence"], list)
        assert isinstance(result["milestones"], list)

    def test_rule_fallback_no_data_text(self, db_conn):
        """데이터 전혀 없을 때 fallback 문구에 '데이터 수집 중' 포함."""
        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert "데이터 수집 중" in result["text"] or "훈련 기록이 아직 없습니다" in result["text"]

    def test_with_ctl_and_distance(self, db_conn):
        """CTL + 이번 달 활동 있을 때 evidence에 해당 항목 포함."""
        _seed_metric(db_conn, "2026-09-22", "ctl", 70)
        _seed_metric(db_conn, "2026-09-01", "ctl", 60)
        _seed_activity(db_conn, activity_id=10, start_time="2026-09-15T06:00:00")
        db_conn.commit()

        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert result["source"] == "rule"
        metric_names = [e["metric"] for e in result["evidence"]]
        assert "ctl" in metric_names
        assert "monthly_distance" in metric_names

    def test_ctl_increase_in_rule_text(self, db_conn):
        """CTL 상승 시 fallback 텍스트에 증가 표현 포함."""
        _seed_metric(db_conn, "2026-09-22", "ctl", 75)
        _seed_metric(db_conn, "2026-09-01", "ctl", 60)
        _seed_activity(db_conn, activity_id=11, start_time="2026-09-10T06:00:00")
        db_conn.commit()

        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert "높아지고 있습니다" in result["text"]

    def test_ai_success_source_is_ai(self, db_conn):
        """_call_provider 목업으로 AI 성공 케이스 — source='ai'."""
        _seed_metric(db_conn, "2026-09-22", "ctl", 70)
        db_conn.commit()

        config = {"ai": {"provider": "gemini", "gemini_api_key": "test"}}
        with patch("src.ai.chat_engine._call_provider", return_value="AI 내러티브 텍스트"):
            result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
        assert result["source"] == "ai"
        assert result["text"] == "AI 내러티브 텍스트"

    def test_ai_failure_falls_back_to_rule(self, db_conn):
        """_call_provider가 None 반환 시 source='rule'로 fallback."""
        config = {"ai": {"provider": "gemini", "gemini_api_key": "test"}}
        with patch("src.ai.chat_engine._call_provider", return_value=None):
            result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=config)
        assert result["source"] == "rule"
        assert isinstance(result["text"], str)

    def test_evidence_excludes_none_metrics(self, db_conn):
        """데이터 없는 메트릭은 evidence에 포함되지 않는다."""
        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        for item in result["evidence"]:
            assert item["value"] is not None

    def test_milestones_in_response(self, db_conn):
        """milestones 키가 결과에 포함된다."""
        db_conn.execute(
            "INSERT INTO milestones (type, date, title) VALUES ('distance_threshold', '2026-09-01', '누적 100km 돌파')"
        )
        db_conn.commit()
        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert len(result["milestones"]) >= 1


class TestGetTodayNarrativeYearMonth:
    def test_highlights_field_present(self, db_conn):
        """highlights 키가 항상 결과에 포함된다."""
        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        h = result["highlights"]
        assert "total_distance_km" in h
        assert "activity_count" in h
        assert "longest_run_km" in h
        assert "peak_ctl" in h

    def test_highlights_no_data_zeros(self, db_conn):
        """활동 없을 때 거리·횟수·최장은 0, peak_ctl은 None."""
        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        h = result["highlights"]
        assert h["total_distance_km"] == 0.0
        assert h["activity_count"] == 0
        assert h["longest_run_km"] == 0.0
        assert h["peak_ctl"] is None

    def test_highlights_with_activities(self, db_conn):
        """활동 있을 때 total_distance_km, activity_count, longest_run_km 집계."""
        # distance_m: 10000 each (seeded by _seed_activity)
        _seed_activity(db_conn, activity_id=20, start_time="2026-09-10T06:00:00")
        _seed_activity(db_conn, activity_id=21, start_time="2026-09-15T06:00:00")
        db_conn.commit()

        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        h = result["highlights"]
        assert h["activity_count"] == 2
        assert h["total_distance_km"] == 20.0
        assert h["longest_run_km"] == 10.0

    def test_past_month_uses_last_day(self, db_conn):
        """과거 달(year/month)은 말일까지 집계."""
        _seed_activity(db_conn, activity_id=30, start_time="2026-08-31T06:00:00")
        db_conn.commit()

        result = today_service.get_today_narrative(
            db_conn, date="2026-09-22", config=None, year=2026, month=8
        )
        assert result["highlights"]["activity_count"] == 1

    def test_year_month_label_in_evidence(self, db_conn):
        """year/month 지정 시 evidence label에 해당 연월 포함."""
        _seed_activity(db_conn, activity_id=31, start_time="2026-08-15T06:00:00")
        db_conn.commit()

        result = today_service.get_today_narrative(
            db_conn, date="2026-09-22", config=None, year=2026, month=8
        )
        monthly_ev = next((e for e in result["evidence"] if e["metric"] == "monthly_distance"), None)
        assert monthly_ev is not None
        assert "2026년 8월" in monthly_ev["label"]

    def test_peak_ctl_in_highlights(self, db_conn):
        """peak_ctl은 해당 기간 최대 CTL."""
        _seed_metric(db_conn, "2026-09-05", "ctl", 65)
        _seed_metric(db_conn, "2026-09-15", "ctl", 72)
        _seed_metric(db_conn, "2026-09-22", "ctl", 70)
        db_conn.commit()

        result = today_service.get_today_narrative(db_conn, date="2026-09-22", config=None)
        assert result["highlights"]["peak_ctl"] == 72.0


class TestSaveCheckin:
    def test_save_and_return(self, db_conn):
        result = today_service.save_checkin(
            db_conn, fatigue=6, pain="none", note="괜찮음", input_date="2026-09-22"
        )
        assert result["fatigue"] == 6
        assert result["pain"] == "none"
        assert result["input_date"] == "2026-09-22"

    def test_upsert_same_day(self, db_conn):
        today_service.save_checkin(db_conn, fatigue=6, pain="none", input_date="2026-09-22")
        result = today_service.save_checkin(db_conn, fatigue=8, pain="mild", input_date="2026-09-22")
        assert result["fatigue"] == 8

        rows = db_conn.execute(
            "SELECT COUNT(*) FROM user_inputs WHERE input_date = '2026-09-22'"
        ).fetchone()
        assert rows[0] == 1

    def test_defaults_to_today_date(self, db_conn):
        result = today_service.save_checkin(db_conn, fatigue=5, pain="none")
        assert result["input_date"]  # 'YYYY-MM-DD' — SQLite date('now') 반환
