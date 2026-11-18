"""ai_worker.cli_runner — argv·stream-json 파싱·쿼터 감지·서브프로세스 마감/취소."""
import json
import stat
import sys

from src.ai_worker import cli_runner as cr

_OK = [
    {"type": "system", "subtype": "init", "session_id": "S1", "model": "claude-haiku-5-5"},
    {"type": "stream_event", "event": {"type": "content_block_delta", "index": 0,
                                        "delta": {"type": "text_delta", "text": "파"}}},
    {"type": "stream_event", "event": {"type": "content_block_delta", "index": 0,
                                        "delta": {"type": "text_delta", "text": "란색"}}},
    {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "x"}]}},
    {"type": "rate_limit_event", "rate_limit_info": {"status": "allowed"}},
    {"type": "result", "subtype": "success", "is_error": False, "result": "파란색", "session_id": "S1",
     "usage": {"input_tokens": 2, "cache_creation_input_tokens": 3, "cache_read_input_tokens": 3545,
               "output_tokens": 5}},
]


def _feed_all(events):
    r = cr.RunResult()
    for e in events:
        cr.feed(r, e)
    return r


def test_feed_success():
    r = _feed_all(_OK)
    assert (r.text, r.session_id, r.is_error, r.got_result) == ("파란색", "S1", False, True)
    assert (r.tokens_in, r.tokens_out, r.cache_read, r.tool_calls) == (5, 5, 3545, 1)
    assert r.partial_text == "파란색" and not r.quota


def test_feed_quota_via_rate_limit_event():
    r = _feed_all([{"type": "rate_limit_event", "rate_limit_info": {"status": "rejected", "resetsAt": 1800000000}}])
    assert r.quota and r.quota_reset_at.startswith("2027-")


def test_feed_quota_via_error_result():
    r = _feed_all([{"type": "result", "subtype": "error_during_execution", "is_error": True,
                    "result": "Claude AI usage limit reached", "usage": {}}])
    assert r.is_error and r.quota


def test_feed_non_quota_error():
    r = _feed_all([{"type": "result", "subtype": "error_max_turns", "is_error": True, "result": "x", "usage": {}}])
    assert r.is_error and not r.quota and r.error_reason == "error_max_turns"


def test_parse_line_ignores_noise():
    assert cr.parse_line("no stdin data received in 3s") is None
    assert cr.parse_line("{bad") is None
    assert cr.parse_line('{"type":"result"}') == {"type": "result"}


def test_build_argv_isolation_and_sessions():
    a = cr.build_argv(model="sonnet", system_prompt_file="/c.txt", mcp_config="/g.json",
                      allowed_tools=["mcp__runpulse__a", "mcp__runpulse__b"])
    assert a[:4] == ["claude", "-p", "--model", "sonnet"]
    for f in ("--strict-mcp-config", "--no-session-persistence", "--disable-slash-commands"):
        assert f in a
    assert a[a.index("--allowedTools") + 1] == "mcp__runpulse__a,mcp__runpulse__b"
    assert a[a.index("--tools") + 1] == "" and a[a.index("--setting-sources") + 1] == ""
    p = cr.build_argv(model="sonnet", session_id="abc", persist=True)
    assert "--session-id" in p and "--no-session-persistence" not in p
    assert "--resume" in cr.build_argv(model="sonnet", session_id="abc", persist=True, resume=True)
    assert "--mcp-config" not in cr.build_argv(model="haiku")


def test_build_mcp_config_pins_uid():
    c = cr.build_mcp_config(user_id="u@x", pythonpath="/p")
    s = c["mcpServers"]["runpulse"]
    assert s["env"]["RUNPULSE_USER_ID"] == "u@x" and s["args"] == ["-m", "src.mcp_server"]


def _fake(tmp_path, body):
    p = tmp_path / "fake.py"
    p.write_text("import sys,json,time\nsys.stdin.read()\n" + body)
    return [sys.executable, str(p)]


def test_run_collects_result(tmp_path):
    lines = "\n".join(json.dumps(e) for e in _OK)
    argv = _fake(tmp_path, f"print('warn')\nfor l in {lines!r}.split(chr(10)): print(l, flush=True)\n")
    r = cr.run(argv, prompt="hi", cwd=str(tmp_path), env=None, deadline_sec=10)
    assert r.text == "파란색" and not r.is_error


def test_run_deadline_kills(tmp_path):
    r = cr.run(_fake(tmp_path, "time.sleep(30)\n"), prompt="", cwd=str(tmp_path), env=None, deadline_sec=1)
    assert r.is_error and r.error_reason == "deadline"


def test_run_cancel(tmp_path):
    r = cr.run(_fake(tmp_path, "time.sleep(30)\n"), prompt="", cwd=str(tmp_path), env=None, deadline_sec=20,
               should_cancel=lambda: True)
    assert r.error_reason == "cancelled"


def test_run_no_result(tmp_path):
    r = cr.run(_fake(tmp_path, "print('x')\n"), prompt="", cwd=str(tmp_path), env=None, deadline_sec=5)
    assert r.is_error and r.error_reason.startswith("no_result")
