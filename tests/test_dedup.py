"""dedup 유틸리티 테스트."""

from src.utils.dedup import is_duplicate, find_duplicates, assign_group_id


class TestIsDuplicate:
    def test_same_activity(self):
        assert is_duplicate(
            "2026-03-18T07:00:00", 10.0,
            "2026-03-18T07:00:00", 10.0,
        )

    def test_within_tolerance(self):
        """시간 3분 차이, 거리 2% 차이 → 중복."""
        assert is_duplicate(
            "2026-03-18T07:00:00", 10.0,
            "2026-03-18T07:03:00", 10.15,
        )

    def test_time_outside_tolerance(self):
        """시간 6분 차이 → 중복 아님."""
        assert not is_duplicate(
            "2026-03-18T07:00:00", 10.0,
            "2026-03-18T07:06:00", 10.0,
        )

    def test_distance_outside_tolerance(self):
        """거리 5% 차이 → 중복 아님."""
        assert not is_duplicate(
            "2026-03-18T07:00:00", 10.0,
            "2026-03-18T07:01:00", 10.5,
        )

    def test_both_zero_distance(self):
        """거리 둘 다 0 → 중복."""
        assert is_duplicate(
            "2026-03-18T07:00:00", 0,
            "2026-03-18T07:02:00", 0,
        )


class TestFindDuplicates:
    def test_no_duplicates(self):
        activities = [
            {"start_time": "2026-03-18T07:00:00", "distance_km": 10.0},
            {"start_time": "2026-03-18T18:00:00", "distance_km": 5.0},
        ]
        assert find_duplicates(activities) == []

    def test_one_group(self):
        activities = [
            {"start_time": "2026-03-18T07:00:00", "distance_km": 10.0, "source": "garmin"},
            {"start_time": "2026-03-18T07:02:00", "distance_km": 10.1, "source": "strava"},
        ]
        groups = find_duplicates(activities)
        assert len(groups) == 1
        assert len(groups[0]) == 2

    def test_multiple_groups(self):
        activities = [
            {"start_time": "2026-03-18T07:00:00", "distance_km": 10.0},
            {"start_time": "2026-03-18T07:01:00", "distance_km": 10.1},
            {"start_time": "2026-03-18T18:00:00", "distance_km": 5.0},
            {"start_time": "2026-03-18T18:02:00", "distance_km": 5.05},
        ]
        groups = find_duplicates(activities)
        assert len(groups) == 2


class TestAssignGroupId:
    def test_no_match(self, db_conn):
        db_conn.execute(
            "INSERT INTO activities (source, source_id, start_time, distance_km) VALUES ('garmin', '1', '2026-03-18T07:00:00', 10.0)"
        )
        db_conn.execute(
            "INSERT INTO activities (source, source_id, start_time, distance_km) VALUES ('strava', '2', '2026-03-18T18:00:00', 5.0)"
        )
        result = assign_group_id(db_conn, 2)
        assert result is None

    def test_match_assigns_group(self, db_conn):
        db_conn.execute(
            "INSERT INTO activities (source, source_id, start_time, distance_km) VALUES ('garmin', '1', '2026-03-18T07:00:00', 10.0)"
        )
        db_conn.execute(
            "INSERT INTO activities (source, source_id, start_time, distance_km) VALUES ('strava', '2', '2026-03-18T07:02:00', 10.1)"
        )
        group_id = assign_group_id(db_conn, 2)
        assert group_id is not None

        # 두 활동 모두 같은 group_id를 가짐
        rows = db_conn.execute(
            "SELECT matched_group_id FROM activities ORDER BY id"
        ).fetchall()
        assert rows[0][0] == rows[1][0] == group_id
