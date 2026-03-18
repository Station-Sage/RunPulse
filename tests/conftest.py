"""pytest 공통 fixture."""

import sqlite3
import pytest

from src.db_setup import create_tables


@pytest.fixture
def db_conn():
    """인메모리 SQLite DB에 테이블 생성 후 연결 반환."""
    conn = sqlite3.connect(":memory:")
    create_tables(conn)
    yield conn
    conn.close()
