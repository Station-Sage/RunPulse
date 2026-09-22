"""today_service 테스트 — Phase 7a D5."""
from __future__ import annotations

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
