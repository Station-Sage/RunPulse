"""P2-7: 중복 매칭 통합 테스트."""

from src.utils.dedup import assign_group_id


class TestCrossSourceDedup:
    def test_garmin_strava_same_activity(self, db_conn):
        """Garmin과 Strava에서 같은 활동 → 동일 그룹."""
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('garmin', 'g1', '2026-03-18T07:00:00', 10.0)""",
        )
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('strava', 's1', '2026-03-18T07:02:00', 10.1)""",
        )

        group_id = assign_group_id(db_conn, 2)
        assert group_id is not None

        rows = db_conn.execute(
            "SELECT matched_group_id FROM activity_summaries ORDER BY id"
        ).fetchall()
        assert rows[0][0] == rows[1][0]

    def test_three_sources_same_activity(self, db_conn):
        """3개 소스 같은 활동 → 모두 동일 그룹."""
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('garmin', 'g2', '2026-03-18T07:00:00', 10.0)""",
        )
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('strava', 's2', '2026-03-18T07:01:00', 10.05)""",
        )
        # Garmin → Strava 매칭
        group1 = assign_group_id(db_conn, 2)
        assert group1 is not None

        # Intervals 추가
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('intervals', 'i2', '2026-03-18T07:02:00', 10.08)""",
        )
        group2 = assign_group_id(db_conn, 3)

        # 모두 같은 그룹
        assert group2 is not None
        rows = db_conn.execute(
            "SELECT matched_group_id FROM activity_summaries ORDER BY id"
        ).fetchall()
        group_ids = {r[0] for r in rows if r[0]}
        assert len(group_ids) == 1

    def test_different_activities_no_match(self, db_conn):
        """다른 시간대 활동 → 매칭 없음."""
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('garmin', 'g3', '2026-03-18T07:00:00', 10.0)""",
        )
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('strava', 's3', '2026-03-18T18:00:00', 5.0)""",
        )

        group_id = assign_group_id(db_conn, 2)
        assert group_id is None

    def test_source_metrics_linked_correctly(self, db_conn):
        """소스별 지표가 올바른 activity_id에 연결."""
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('garmin', 'g4', '2026-03-18T07:00:00', 10.0)""",
        )
        db_conn.execute(
            """INSERT INTO activity_summaries (source, source_id, start_time, distance_km)
               VALUES ('strava', 's4', '2026-03-18T07:01:00', 10.05)""",
        )

        # 각 소스별 지표 삽입
        db_conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value) VALUES (1, 'garmin', 'vo2max', 48.5)"
        )
        db_conn.execute(
            "INSERT INTO activity_detail_metrics (activity_id, source, metric_name, metric_value) VALUES (2, 'strava', 'suffer_score', 87)"
        )

        assign_group_id(db_conn, 2)

        # 그룹 내 모든 지표 조회
        rows = db_conn.execute(
            """SELECT sm.source, sm.metric_name, sm.metric_value
               FROM activity_detail_metrics sm
               JOIN activity_summaries a ON sm.activity_id = a.id
               WHERE a.matched_group_id IS NOT NULL
               ORDER BY sm.source"""
        ).fetchall()

        assert len(rows) == 2
        sources = {r[0] for r in rows}
        assert sources == {"garmin", "strava"}
