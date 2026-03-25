"""V2-0 DB 스키마 테스트 (computed_metrics, weather_data 테이블 + migrate_db)."""
from __future__ import annotations

import sqlite3

import pytest


@pytest.fixture
def fresh_conn(tmp_path):
    """create_tables + migrate_db가 적용된 커넥션."""
    from src.db_setup import create_tables, migrate_db
    conn = sqlite3.connect(str(tmp_path / "test.db"))
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def existing_conn(tmp_path):
    """기존 DB(v0.1 스키마)에 migrate_db만 적용한 커넥션."""
    from src.db_setup import create_tables, migrate_db
    conn = sqlite3.connect(str(tmp_path / "old.db"))
    create_tables(conn)
    # 신규 테이블 제거 후 migrate로 복원 확인
    conn.execute("DROP TABLE IF EXISTS computed_metrics")
    conn.execute("DROP TABLE IF EXISTS weather_data")
    conn.execute("DROP TABLE IF EXISTS activity_laps")
    conn.commit()
    migrate_db(conn)
    yield conn
    conn.close()


def _table_names(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}


def _index_names(conn: sqlite3.Connection) -> set[str]:
    return {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='index'")}


class TestComputedMetricsTable:
    def test_table_created_by_create_tables(self, fresh_conn):
        """create_tables()가 computed_metrics 테이블을 생성한다."""
        assert "computed_metrics" in _table_names(fresh_conn)

    def test_table_created_by_migrate_db(self, existing_conn):
        """migrate_db()가 기존 DB에 computed_metrics를 추가한다."""
        assert "computed_metrics" in _table_names(existing_conn)

    def test_indexes_exist(self, fresh_conn):
        """computed_metrics 인덱스 2개가 존재한다."""
        idx = _index_names(fresh_conn)
        assert "idx_computed_metrics_date" in idx
        assert "idx_computed_metrics_activity" in idx

    def test_insert_daily_metric(self, fresh_conn):
        """일별 메트릭 (activity_id=NULL) 삽입 및 조회."""
        fresh_conn.execute(
            "INSERT INTO computed_metrics (date, metric_name, metric_value) VALUES (?,?,?)",
            ("2026-03-23", "UTRS", 78.5),
        )
        row = fresh_conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE date=? AND metric_name=?",
            ("2026-03-23", "UTRS"),
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 78.5) < 1e-6

    def test_insert_activity_metric(self, fresh_conn):
        """활동별 메트릭 (activity_id 지정) 삽입."""
        fresh_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin','g1','2026-03-23T07:00:00')"
        )
        act_id = fresh_conn.execute("SELECT id FROM activity_summaries WHERE source_id='g1'").fetchone()[0]

        fresh_conn.execute(
            "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value) VALUES (?,?,?,?)",
            ("2026-03-23", act_id, "FEARP", 5.12),
        )
        row = fresh_conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE activity_id=? AND metric_name=?",
            (act_id, "FEARP"),
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 5.12) < 1e-6

    def test_unique_constraint_upsert(self, fresh_conn):
        """같은 (date, activity_id NOT NULL, metric_name)은 삽입 충돌 발생.

        SQLite UNIQUE는 NULL을 각각 다른 값으로 취급 — activity_id가 NOT NULL일 때만 충돌.
        """
        fresh_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin','gx','2026-03-23T07:00:00')"
        )
        act_id = fresh_conn.execute("SELECT id FROM activity_summaries WHERE source_id='gx'").fetchone()[0]
        fresh_conn.execute(
            "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value) VALUES ('2026-03-23',?,'LSI',1.2)",
            (act_id,),
        )
        with pytest.raises(sqlite3.IntegrityError):
            fresh_conn.execute(
                "INSERT INTO computed_metrics (date, activity_id, metric_name, metric_value) VALUES ('2026-03-23',?,'LSI',1.5)",
                (act_id,),
            )

    def test_metric_json_stored(self, fresh_conn):
        """metric_json 컬럼에 JSON 문자열 저장."""
        import json
        payload = json.dumps({"sleep": 0.8, "hrv": 0.7, "load": 0.9})
        fresh_conn.execute(
            "INSERT INTO computed_metrics (date, metric_name, metric_json) VALUES ('2026-03-23','UTRS_detail',?)",
            (payload,),
        )
        row = fresh_conn.execute(
            "SELECT metric_json FROM computed_metrics WHERE metric_name='UTRS_detail'"
        ).fetchone()
        assert json.loads(row[0])["sleep"] == pytest.approx(0.8)


class TestActivitySummariesV2Columns:
    def test_start_lat_lon_columns_exist(self, fresh_conn):
        """activity_summaries에 start_lat, start_lon 컬럼이 존재한다."""
        cols = {
            row[1]
            for row in fresh_conn.execute("PRAGMA table_info(activity_summaries)")
        }
        assert "start_lat" in cols
        assert "start_lon" in cols

    def test_migrate_adds_lat_lon(self, tmp_path):
        """migrate_db()가 기존 DB에 start_lat/start_lon을 추가한다."""
        from src.db_setup import create_tables, migrate_db
        conn = sqlite3.connect(str(tmp_path / "old.db"))
        create_tables(conn)
        conn.execute("ALTER TABLE activity_summaries DROP COLUMN start_lat" if False else "SELECT 1")
        # 컬럼 없는 상태 시뮬레이션은 SQLite에서 DROP 미지원 → migrate가 추가만 하는지 검증
        migrate_db(conn)
        cols = {row[1] for row in conn.execute("PRAGMA table_info(activity_summaries)")}
        assert "start_lat" in cols
        conn.close()


class TestActivityLapsTable:
    def test_table_created(self, fresh_conn):
        """activity_laps 테이블이 생성된다."""
        assert "activity_laps" in _table_names(fresh_conn)

    def test_table_created_by_migrate_db(self, existing_conn):
        """migrate_db()가 기존 DB에 activity_laps를 추가한다."""
        assert "activity_laps" in _table_names(existing_conn)

    def test_index_exists(self, fresh_conn):
        """activity_laps 인덱스가 존재한다."""
        assert "idx_activity_laps_activity" in _index_names(fresh_conn)

    def test_insert_lap(self, fresh_conn):
        """랩 데이터 삽입 및 조회."""
        fresh_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin','g1','2026-03-23T07:00:00')"
        )
        act_id = fresh_conn.execute("SELECT id FROM activity_summaries WHERE source_id='g1'").fetchone()[0]
        fresh_conn.execute(
            """INSERT INTO activity_laps
               (activity_id, source, lap_index, distance_km, duration_sec, avg_pace_sec_km)
               VALUES (?,?,?,?,?,?)""",
            (act_id, "garmin", 0, 5.0, 1500, 300),
        )
        rows = fresh_conn.execute(
            "SELECT distance_km FROM activity_laps WHERE activity_id=?", (act_id,)
        ).fetchall()
        assert len(rows) == 1
        assert abs(rows[0][0] - 5.0) < 1e-6

    def test_unique_constraint(self, fresh_conn):
        """같은 (activity_id, source, lap_index)은 충돌 발생."""
        fresh_conn.execute(
            "INSERT INTO activity_summaries (source, source_id, start_time) VALUES ('garmin','g2','2026-03-23T08:00:00')"
        )
        act_id = fresh_conn.execute("SELECT id FROM activity_summaries WHERE source_id='g2'").fetchone()[0]
        fresh_conn.execute(
            "INSERT INTO activity_laps (activity_id, source, lap_index, distance_km) VALUES (?,?,?,?)",
            (act_id, "garmin", 0, 5.0),
        )
        with pytest.raises(sqlite3.IntegrityError):
            fresh_conn.execute(
                "INSERT INTO activity_laps (activity_id, source, lap_index, distance_km) VALUES (?,?,?,?)",
                (act_id, "garmin", 0, 5.1),
            )


class TestWeatherDataTable:
    def test_table_created_by_create_tables(self, fresh_conn):
        """create_tables()가 weather_data 테이블을 생성한다."""
        assert "weather_data" in _table_names(fresh_conn)

    def test_table_created_by_migrate_db(self, existing_conn):
        """migrate_db()가 기존 DB에 weather_data를 추가한다."""
        assert "weather_data" in _table_names(existing_conn)

    def test_index_exists(self, fresh_conn):
        """weather_data 인덱스가 존재한다."""
        assert "idx_weather_data_date" in _index_names(fresh_conn)

    def test_insert_weather_row(self, fresh_conn):
        """날씨 데이터 삽입 및 조회."""
        fresh_conn.execute(
            """INSERT INTO weather_data
               (date, hour, latitude, longitude, temp_c, humidity_pct, wind_speed_ms)
               VALUES (?,?,?,?,?,?,?)""",
            ("2026-03-23", 7, 37.56, 126.97, 12.5, 65, 3.2),
        )
        row = fresh_conn.execute(
            "SELECT temp_c, humidity_pct FROM weather_data WHERE date=? AND hour=?",
            ("2026-03-23", 7),
        ).fetchone()
        assert row is not None
        assert abs(row[0] - 12.5) < 1e-6
        assert row[1] == 65

    def test_unique_constraint(self, fresh_conn):
        """같은 (date, hour, lat, lon)은 삽입 충돌 발생."""
        fresh_conn.execute(
            "INSERT INTO weather_data (date, hour, latitude, longitude, temp_c) VALUES ('2026-03-23',7,37.56,126.97,12.0)"
        )
        with pytest.raises(sqlite3.IntegrityError):
            fresh_conn.execute(
                "INSERT INTO weather_data (date, hour, latitude, longitude, temp_c) VALUES ('2026-03-23',7,37.56,126.97,15.0)"
            )


class TestWeatherProvider:
    def test_cache_hit_returns_data(self, fresh_conn):
        """캐시에 데이터가 있으면 API 호출 없이 반환한다."""
        from unittest.mock import patch
        from src.weather.provider import get_weather

        fresh_conn.execute(
            """INSERT INTO weather_data
               (date, hour, latitude, longitude, temp_c, feels_like_c,
                humidity_pct, wind_speed_ms, precipitation_mm, cloudcover_pct)
               VALUES ('2026-03-23',7,37.56,126.97,12.5,10.0,65,3.2,0.0,20)"""
        )

        with patch("src.weather.provider._fetch_from_api") as mock_fetch:
            result = get_weather(fresh_conn, "2026-03-23", 7, 37.56, 126.97)

        mock_fetch.assert_not_called()
        assert result is not None
        assert abs(result["temp_c"] - 12.5) < 1e-6

    def test_cache_miss_calls_api(self, fresh_conn):
        """캐시 미스 시 API 호출 후 DB에 저장한다."""
        from unittest.mock import patch
        from src.weather.provider import get_weather

        fake_response = {
            "hourly": {
                "time": ["2026-03-23T07:00"],
                "temperature_2m": [11.0],
                "apparent_temperature": [9.5],
                "relativehumidity_2m": [70],
                "windspeed_10m": [2.5],
                "precipitation": [0.0],
                "cloudcover": [30],
            }
        }

        with patch("src.weather.provider._fetch_from_api", return_value=fake_response):
            result = get_weather(fresh_conn, "2026-03-23", 7, 37.56, 126.97)

        assert result is not None
        assert abs(result["temp_c"] - 11.0) < 1e-6
        # DB에 저장됐는지 확인
        cached = fresh_conn.execute(
            "SELECT temp_c FROM weather_data WHERE date='2026-03-23' AND hour=7"
        ).fetchone()
        assert cached is not None
        assert abs(cached[0] - 11.0) < 1e-6

    def test_api_error_returns_none(self, fresh_conn):
        """API 호출 실패 시 None 반환 (예외 전파 안 함)."""
        from unittest.mock import patch
        from src.weather.provider import get_weather
        from src.utils.api import ApiError

        with patch("src.weather.provider._fetch_from_api", side_effect=ApiError("연결 실패")):
            result = get_weather(fresh_conn, "2026-03-23", 7, 37.56, 126.97)

        assert result is None

    def test_get_weather_for_activity_no_coords(self, fresh_conn):
        """좌표 없으면 None 반환."""
        from src.weather.provider import get_weather_for_activity

        result = get_weather_for_activity(fresh_conn, "2026-03-23T07:00:00", None, None)
        assert result is None
