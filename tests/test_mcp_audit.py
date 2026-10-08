"""mcp_remote.audit — 기록·절단·IP 해시·보존 정리·조회."""
from __future__ import annotations

import pytest

from src.mcp_remote import audit
from src.mcp_remote import token_index as ti


@pytest.fixture(autouse=True)
def idx(monkeypatch, tmp_path):
    monkeypatch.setattr(ti, "index_path", lambda: tmp_path / "mcp_tokens.db")
    monkeypatch.setattr(audit, "_last_purge_day", "9999")  # 자동 정리 비활성


def test_record_and_query_with_truncation_and_ip_hash():
    audit.record(token_id="t1", user_id="a", method="tools/call", tool="get_wellness",
                 args={"q": "x" * 2000}, status="ok", latency_ms=5, resp_bytes=10, ip="1.2.3.4")
    (r,) = audit.query("a")
    assert r["tool"] == "get_wellness" and len(r["args_json"]) == audit.ARGS_MAX
    assert r["ip_hash"] == audit.ip_hash("1.2.3.4") and "1.2.3.4" not in str(r)
    assert audit.query("b") == []


def test_purge_removes_only_old_rows():
    audit.record(token_id="t", user_id="a", method="m", tool=None, args=None, status="ok")
    audit.record(token_id="t", user_id="a", method="old", tool=None, args=None, status="ok")
    c = ti.connect()
    c.execute("UPDATE mcp_audit SET ts=datetime('now','-91 days') WHERE method='old'")
    c.commit()
    c.close()
    assert audit.purge() == 1
    assert [r["method"] for r in audit.query()] == ["m"]
