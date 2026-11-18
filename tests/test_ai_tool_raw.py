"""원본 payload 도구·tool_cli 테스트."""
import json
import sqlite3

from src.ai import tool_cli
from src.ai.tools import execute_tool
from src.mcp_remote import policy


def _db(tmp_path):
    p = tmp_path / "r.db"
    c = sqlite3.connect(p)
    c.execute("CREATE TABLE source_payloads (id INTEGER PRIMARY KEY, source TEXT, entity_type TEXT, entity_id TEXT,"
              " entity_date TEXT, activity_id INTEGER, payload TEXT, fetched_at TEXT)")
    big = {"summaryDTO": {"hr": [1, 2, 3], "x": "y" * 9000}}
    c.execute("INSERT INTO source_payloads VALUES (1,'garmin','activity_detail','a1','2026-11-01',5,?,'t')", (json.dumps(big),))
    c.execute("INSERT INTO source_payloads VALUES (2,'garmin','wellness_day','w1','2026-11-02',NULL,'{\"a\":1}','t')")
    c.commit()
    return p, c


def test_list_filters(tmp_path):
    _, c = _db(tmp_path)
    out = json.loads(execute_tool(c, "list_raw_payloads", {"entity_type": "activity_detail"}))
    assert [r[0] for r in out["rows"]] == [1]
    assert len(json.loads(execute_tool(c, "list_raw_payloads", {}))["rows"]) == 2


def test_get_truncates_and_path(tmp_path):
    _, c = _db(tmp_path)
    out = json.loads(execute_tool(c, "get_raw_payload", {"id": 1}))
    assert out["truncated"] and "shape" in out
    out = json.loads(execute_tool(c, "get_raw_payload", {"id": 1, "path": "summaryDTO.hr.1"}))
    assert out["data"] == 2
    bad = json.loads(execute_tool(c, "get_raw_payload", {"id": 1, "path": "nope"}))
    assert "error" in bad and "shape" in bad
    assert "error" in json.loads(execute_tool(c, "get_raw_payload", {"id": 99}))


def test_local_only_policy():
    assert {"list_raw_payloads", "get_raw_payload"} <= policy.LOCAL_ONLY_TOOLS
    assert not (policy.LOCAL_ONLY_TOOLS & policy.REMOTE_TOOLS)
    assert policy.unclassified_tools() == set()


def test_tool_cli(tmp_path, capsys):
    p, _ = _db(tmp_path)
    assert tool_cli.main(["get_raw_payload", '{"id":2}', "--db", str(p)]) == 0
    assert json.loads(capsys.readouterr().out)["data"] == {"a": 1}
    assert tool_cli.main(["get_raw_payload", "{bad", "--db", str(p)]) == 2


def test_local_declarations_match_dispatch_and_stay_out_of_chat():
    from src.ai.tool_declarations import LOCAL_TOOL_DECLARATIONS, TOOL_DECLARATIONS
    from src.ai.tools import _DISPATCH
    local = {d["name"] for d in LOCAL_TOOL_DECLARATIONS}
    assert local == policy.LOCAL_ONLY_TOOLS <= set(_DISPATCH)
    assert not local & {d["name"] for d in TOOL_DECLARATIONS}
