"""U18b — 스트림 meta 저장 경로(stream_meta_store) 테스트."""
import sqlite3

import pytest

from src.db_schema_v30 import ensure_v30
from src.db_setup import create_tables
from src.sync.extractors.stream_time import StreamRows, stream_meta
from src.sync.stream_meta_store import store_streams


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    create_tables(c)
    c.execute("INSERT INTO activity_summaries (id, source, source_id, activity_type, start_time, elapsed_time_sec)"
              " VALUES (1, 'garmin', 'g1', 'running', '2026-01-01T00:00:00', 100)")
    return c


def _rows(times, basis="measured", key="sumElapsedDuration", n=None):
    rows = StreamRows({"source": "garmin", "elapsed_sec": t, "heart_rate": 100 + i} for i, t in enumerate(times))
    rows.meta = stream_meta(rows, basis, key, n or len(times))
    return rows


def test_ensure_v30_idempotent(conn):
    ensure_v30(conn)
    ensure_v30(conn)
    assert conn.execute("SELECT COUNT(*) FROM activity_stream_meta").fetchone()[0] == 0


def test_upsert_overwrites(conn):
    store_streams(conn, 1, _rows([0, 2, 4]))
    store_streams(conn, 1, _rows([0, 5, 10, 15]))
    got = conn.execute("SELECT stored_count, span_sec, time_basis FROM activity_stream_meta").fetchall()
    assert got == [(4, 15.0, "measured")]


def test_stored_count_reflects_duplicate_seconds(conn):
    n = store_streams(conn, 1, _rows([0, 1, 1, 2]))
    row = conn.execute("SELECT sample_count, stored_count FROM activity_stream_meta").fetchone()
    assert n == 3 and row == (4, 3)


def test_scaled_uses_summary_time(conn):
    n = store_streams(conn, 1, _rows([None] * 5, basis="scaled", key=None))
    ts = [r[0] for r in conn.execute("SELECT elapsed_sec FROM activity_streams ORDER BY elapsed_sec")]
    meta = conn.execute("SELECT time_basis, span_sec FROM activity_stream_meta").fetchone()
    assert n == 5 and ts == [0, 25, 50, 75, 100] and meta == ("scaled", 100.0)


def test_scaled_without_summary_skips(conn):
    assert store_streams(conn, 999, _rows([None] * 3, basis="scaled", key=None)) == 0
    assert conn.execute("SELECT COUNT(*) FROM activity_streams").fetchone()[0] == 0
    assert conn.execute("SELECT COUNT(*) FROM activity_stream_meta").fetchone()[0] == 0


def test_plain_list_and_missing_table_fall_back(conn):
    conn.execute("DROP TABLE activity_stream_meta")
    assert store_streams(conn, 1, _rows([0, 1, 2])) == 3          # meta 테이블 없어도 저장은 성공
    plain = [{"source": "garmin", "elapsed_sec": 7}]
    assert store_streams(conn, 1, plain) == 1
