"""MCP 서버 — DB 결정, 읽기 전용, stdio 프레임, 프로토콜 응답."""
import io
import json
import sqlite3

import pytest

from src import mcp_server
from src.ai.tool_guide import USAGE_GUIDE
from src.ai.tools import TOOL_DECLARATIONS
from src.db_setup import create_tables


@pytest.fixture
def db_path(tmp_path):
    path = tmp_path / "running.db"
    conn = sqlite3.connect(path)
    create_tables(conn)
    conn.commit()
    conn.close()
    return path


class TestResolveDbPath:
    def test_requires_user_id(self, monkeypatch):
        monkeypatch.delenv("RUNPULSE_USER_ID", raising=False)
        with pytest.raises(RuntimeError, match="RUNPULSE_USER_ID"):
            mcp_server.resolve_db_path()

    def test_blank_user_id_is_rejected(self):
        with pytest.raises(RuntimeError):
            mcp_server.resolve_db_path("   ")

    def test_path_traversal_is_rejected(self):
        with pytest.raises(RuntimeError, match="잘못된"):
            mcp_server.resolve_db_path("../default")

    def test_unknown_user_raises_and_creates_no_directory(self):
        from src.db_setup import get_db_path
        uid = "no-such-user-for-mcp-test"
        with pytest.raises(FileNotFoundError):
            mcp_server.resolve_db_path(uid)
        assert not get_db_path(uid, create=False).parent.exists()

    def test_env_var_is_used(self, monkeypatch, tmp_path):
        from src import db_setup
        monkeypatch.setattr(db_setup, "_PROJECT_ROOT", tmp_path)
        (tmp_path / "data" / "users" / "u1").mkdir(parents=True)
        (tmp_path / "data" / "users" / "u1" / "running.db").touch()
        monkeypatch.setenv("RUNPULSE_USER_ID", "u1")
        assert mcp_server.resolve_db_path().parent.name == "u1"


class TestReadOnly:
    def test_connection_rejects_writes(self, db_path):
        conn = mcp_server._get_conn(db_path)
        with pytest.raises(sqlite3.OperationalError):
            conn.execute("INSERT INTO daily_wellness (date) VALUES ('2026-09-21')")
        conn.close()


class TestFraming:
    def test_write_is_single_line_with_no_padding(self, capsys):
        mcp_server._write_message({"jsonrpc": "2.0", "id": 1, "result": {"text": "줄1\n줄2"}})
        out = capsys.readouterr().out
        assert out.endswith("\n") and out.count("\n") == 1     # 내용 속 개행은 이스케이프됨
        assert json.loads(out)["result"]["text"] == "줄1\n줄2"
        assert ", " not in out and ": " not in out

    def test_read_skips_blank_lines_and_returns_none_at_eof(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO('\n{"id":1,"method":"ping"}\n'))
        assert mcp_server._read_message() == {"id": 1, "method": "ping"}
        assert mcp_server._read_message() is None


class TestProtocol:
    def _req(self, method, id_=1, **params):
        msg = {"jsonrpc": "2.0", "method": method}
        if id_ is not None:
            msg["id"] = id_
        if params:
            msg["params"] = params
        return msg

    def test_initialize_carries_usage_guide(self, db_path):
        resp = mcp_server.handle_request(self._req("initialize"), db_path)
        assert resp["result"]["instructions"] == USAGE_GUIDE
        assert resp["result"]["capabilities"] == {"tools": {}}

    def test_tools_list_matches_declarations(self, db_path):
        resp = mcp_server.handle_request(self._req("tools/list"), db_path)
        tools = resp["result"]["tools"]
        assert [t["name"] for t in tools] == [d["name"] for d in TOOL_DECLARATIONS]
        assert all("inputSchema" in t for t in tools)

    def test_notification_gets_no_response(self, db_path):
        assert mcp_server.handle_request(self._req("notifications/initialized", id_=None), db_path) is None

    def test_ping(self, db_path):
        assert mcp_server.handle_request(self._req("ping"), db_path)["result"] == {}

    def test_unknown_method_is_error(self, db_path):
        resp = mcp_server.handle_request(self._req("resources/list"), db_path)
        assert resp["error"]["code"] == -32601

    def test_tool_call_success(self, db_path):
        resp = mcp_server.handle_request(
            self._req("tools/call", name="get_training_summary",
                      arguments={"start_date": "2026-09-01", "end_date": "2026-09-07"}), db_path)
        assert resp["result"]["isError"] is False
        assert json.loads(resp["result"]["content"][0]["text"])["totals"]["runs"] == 0

    def test_unknown_tool_flags_is_error(self, db_path):
        resp = mcp_server.handle_request(self._req("tools/call", name="nope", arguments={}), db_path)
        assert resp["result"]["isError"] is True

    def test_missing_arguments_key_is_tolerated(self, db_path):
        resp = mcp_server.handle_request(self._req("tools/call", name="get_runner_profile"), db_path)
        assert "content" in resp["result"]

    def test_missing_db_is_reported_as_tool_error_not_crash(self, tmp_path):
        resp = mcp_server.handle_request(
            self._req("tools/call", name="get_runner_profile", arguments={}), tmp_path / "x.db")
        assert resp["result"]["isError"] is True
