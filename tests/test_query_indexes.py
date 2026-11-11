"""S4-88 — 실계정 응답시간 병목 쿼리가 인덱스를 타는지(동기화 상태·프로필 최신 값)."""
from __future__ import annotations


def _plan(conn, sql, args=()):
    return " ".join(str(r[-1]) for r in conn.execute("EXPLAIN QUERY PLAN " + sql, args).fetchall())


def test_sync_state_payload_max_uses_covering_index(db_conn):
    plan = _plan(db_conn, "SELECT source, MAX(fetched_at) FROM source_payloads GROUP BY source")
    assert "COVERING INDEX idx_sp_source_fetched" in plan


def test_profile_latest_metric_uses_name_scope_index(db_conn):
    plan = _plan(db_conn, "SELECT numeric_value, scope_id FROM metric_store WHERE metric_name=? AND scope_type='daily'"
                          " AND numeric_value IS NOT NULL AND is_primary=1 ORDER BY scope_id DESC LIMIT 1", ("max_hr",))
    assert "idx_ms_name_scope" in plan
