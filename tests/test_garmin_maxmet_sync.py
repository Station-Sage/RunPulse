import pytest

from src.sync.garmin_maxmet_sync import backfill_vo2max, sync_vo2max_range


def _item(day, p):
    return {"generic": {"calendarDate": day, "vo2MaxPreciseValue": p, "vo2MaxValue": round(p)}}


class FakeClient:
    def __init__(self, items=None, exc=None):
        self.items, self.exc, self.calls = items or [], exc, []

    def get_max_metrics_range(self, s, e):
        self.calls.append((s, e))
        if self.exc:
            raise self.exc
        return self.items


def _rows(conn):
    return conn.execute(
        "SELECT scope_id, numeric_value, is_primary FROM metric_store "
        "WHERE scope_type='daily' AND metric_name='vo2max' ORDER BY scope_id").fetchall()


def test_saves_metric_and_raw(db_conn):
    c = FakeClient([_item("2026-10-08", 53.7), _item("2026-10-09", 53.9)])
    assert sync_vo2max_range(db_conn, c, "2026-10-01", "2026-10-10") == 2
    assert _rows(db_conn) == [("2026-10-08", 53.7, 1), ("2026-10-09", 53.9, 1)]
    n = db_conn.execute("SELECT COUNT(*) FROM source_payloads WHERE entity_type='maxmet_day'").fetchone()[0]
    assert n == 2


def test_idempotent(db_conn):
    c = FakeClient([_item("2026-10-09", 53.9)])
    sync_vo2max_range(db_conn, c, "2026-10-01", "2026-10-10")
    sync_vo2max_range(db_conn, c, "2026-10-01", "2026-10-10")
    assert len(_rows(db_conn)) == 1
    assert db_conn.execute("SELECT COUNT(*) FROM source_payloads WHERE entity_type='maxmet_day'").fetchone()[0] == 1


def test_error_returns_zero(db_conn):
    assert sync_vo2max_range(db_conn, FakeClient(exc=RuntimeError("boom")), "2026-10-01", "2026-10-10") == 0


def test_backfill_splits_windows(db_conn):
    c = FakeClient([])
    r = backfill_vo2max(db_conn, c, "2024-01-01", "2026-01-01", sleep=0)
    assert len(c.calls) == 3 and c.calls[0] == ("2024-01-01", "2024-12-30")
    assert r["next_start"] is None


def test_backfill_stops_on_429(db_conn):
    c = FakeClient(exc=RuntimeError("429 Too Many Requests"))
    r = backfill_vo2max(db_conn, c, "2024-01-01", "2026-01-01", sleep=0)
    assert r == {"saved": 0, "next_start": "2024-01-01"}
    assert len(c.calls) == 1
