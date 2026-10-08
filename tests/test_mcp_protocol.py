"""mcp_remote.protocol / safe_conn / policy — 허용 집합, 버전 협상, 일반화 오류, 읽기 전용 보장."""
import json
import sqlite3
import time

import pytest

from src.db_setup import create_tables
from src.mcp_remote import policy, protocol
from src.mcp_remote.safe_conn import connect_readonly


@pytest.fixture
def db_path(tmp_path):
    p = tmp_path / "running.db"
    c = sqlite3.connect(p)
    create_tables(c)
    c.commit()
    c.close()
    return p


def _call(name, connect, **kw):
    return protocol.handle_message(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": {}}},
        connect, **kw)


def test_version_negotiation():
    assert protocol.negotiate_version("2025-03-26") == "2025-03-26"
    assert protocol.negotiate_version("1999-01-01") == protocol.SUPPORTED_VERSIONS[0]
    assert protocol.negotiate_version(None) == protocol.SUPPORTED_VERSIONS[0]


def test_initialize_echoes_supported_version():
    r = protocol.handle_message({"id": 1, "method": "initialize",
                                 "params": {"protocolVersion": "2024-11-05"}}, lambda: None)
    assert r["result"]["protocolVersion"] == "2024-11-05"
    assert r["result"]["capabilities"] == {"tools": {}}


def test_tools_list_filtered_by_allowed():
    r = protocol.handle_message({"id": 1, "method": "tools/list"}, lambda: None,
                                allowed={"get_weather"})
    assert [t["name"] for t in r["result"]["tools"]] == ["get_weather"]


def test_disallowed_tool_looks_unknown_and_never_connects():
    def boom():
        raise AssertionError("connect called")
    r = _call("get_wellness", boom, allowed={"get_weather"})
    assert r["result"]["isError"] is True
    assert "알 수 없는 도구" in r["result"]["content"][0]["text"]


def test_generic_errors_hide_exception_text(tmp_path):
    secret = tmp_path / "secret@example.com" / "x.db"
    r = _call("get_weather", lambda: connect_readonly(secret), generic_errors=True)
    text = r["result"]["content"][0]["text"]
    assert r["result"]["isError"] is True and "secret" not in text
    assert json.loads(text) == {"error": "도구 실행 실패"}


def test_unknown_method_and_notification():
    assert protocol.handle_message({"id": 3, "method": "resources/list"}, lambda: None)["error"]["code"] == -32601
    assert protocol.handle_message({"method": "notifications/initialized"}, lambda: None) is None


def test_safe_conn_allows_select_blocks_writes(db_path):
    conn = connect_readonly(db_path)
    assert conn.execute("SELECT COUNT(*) FROM daily_wellness").fetchone()[0] == 0
    assert conn.execute("PRAGMA table_info(daily_wellness)").fetchall()
    for sql in ("INSERT INTO daily_wellness (date) VALUES ('2026-09-21')",
                "CREATE TABLE t(x)", "DROP TABLE daily_wellness",
                "PRAGMA query_only=OFF", "PRAGMA journal_mode=DELETE"):
        with pytest.raises(sqlite3.Error):
            conn.execute(sql)
    conn.close()


def test_safe_conn_blocks_attach(db_path, tmp_path):
    conn = connect_readonly(db_path)
    with pytest.raises(sqlite3.Error):
        conn.execute(f"ATTACH DATABASE '{tmp_path / 'o.db'}' AS o")
    conn.close()


def test_safe_conn_time_limit(db_path):
    conn = connect_readonly(db_path, time_limit_s=0.2)
    t0 = time.monotonic()
    with pytest.raises(sqlite3.OperationalError):
        conn.execute("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x+1 FROM c) "
                     "SELECT COUNT(*) FROM c").fetchone()
    assert time.monotonic() - t0 < 3
    conn.close()


def test_every_tool_is_classified():
    assert policy.unclassified_tools() == set()
    assert not (policy.REMOTE_TOOLS & policy.REMOTE_DENIED)
