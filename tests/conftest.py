"""pytest 공통 fixture."""

import sqlite3
import pytest

from src.db_setup import create_tables, migrate_db


@pytest.fixture
def db_conn():
    """인메모리 SQLite DB에 테이블 생성 + 마이그레이션 후 연결 반환."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    migrate_db(conn)
    yield conn
    conn.close()


@pytest.fixture
def sample_config():
    """테스트용 설정 딕셔너리."""
    return {
        "garmin": {"email": "test@test.com", "password": "testpass"},
        "strava": {
            "client_id": "12345",
            "client_secret": "secret",
            "refresh_token": "rt_test",
            "access_token": "at_test",
            "expires_at": 9999999999,
        },
        "intervals": {"athlete_id": "i12345", "api_key": "apikey_test"},
        "runalyze": {"token": "token_test"},
        "user": {
            "max_hr": 190,
            "threshold_pace_sec_km": 300,
            "rest_hr": 50,
            "weight_kg": 70,
        },
    }
