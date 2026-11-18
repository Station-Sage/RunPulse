"""Claude CLI 실행기 — argv 조립, stream-json 파싱, 쿼터 감지, 서브프로세스 구동 (flask 의존 없음)."""
from __future__ import annotations

import json
import re
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Callable

QUOTA_PAUSE_FALLBACK_SEC = 15 * 60
_QUOTA_WORDS = re.compile(r"usage limit|rate limit|limit reached|quota|too many requests|overloaded_quota", re.I)


def build_argv(*, model: str, system_prompt_file: str | None = None, mcp_config: str | None = None,
               allowed_tools: list[str] | None = None, session_id: str | None = None,
               resume: bool = False, persist: bool = False, streaming_input: bool = False,
               partial: bool = False, claude_bin: str = "claude") -> list[str]:
    """격리 플래그를 고정한 `claude -p` argv. 프롬프트는 stdin 으로 전달한다."""
    argv = [claude_bin, "-p", "--model", model]
    if system_prompt_file:
        argv += ["--system-prompt-file", system_prompt_file]
    argv += ["--tools", "", "--setting-sources", "", "--disable-slash-commands"]
    if mcp_config:
        argv += ["--strict-mcp-config", "--mcp-config", mcp_config]
        if allowed_tools:
            argv += ["--allowedTools", ",".join(allowed_tools)]
    else:
        argv += ["--strict-mcp-config"]
    argv += ["--output-format", "stream-json", "--verbose"]
    if streaming_input:
        argv += ["--input-format", "stream-json"]
    if partial:
        argv += ["--include-partial-messages"]
    if persist and session_id:
        argv += ["--resume", session_id] if resume else ["--session-id", session_id]
    else:
        argv += ["--no-session-persistence"]
    return argv


def build_mcp_config(*, user_id: str, pythonpath: str, python_bin: str = "/usr/bin/python3",
                     path_env: str = "/usr/bin:/bin", home: str = "") -> dict:
    """runpulse MCP 서버 한 개만 담은 설정. 사용자 id 는 환경변수로 고정된다."""
    return {"mcpServers": {"runpulse": {
        "command": python_bin, "args": ["-m", "src.mcp_server"],
        "env": {"PYTHONPATH": pythonpath, "RUNPULSE_USER_ID": user_id, "PATH": path_env, "HOME": home},
    }}}


@dataclass
class RunResult:
    text: str = ""
    session_id: str | None = None
    is_error: bool = False
    error_reason: str | None = None
    quota: bool = False
    quota_reset_at: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cache_read: int = 0
    tool_calls: int = 0
    partial_text: str = ""
    got_result: bool = False
    events: int = 0
    extra: dict = field(default_factory=dict)


def parse_line(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("{"):
        return None
    try:
        d = json.loads(line)
    except ValueError:
        return None
    return d if isinstance(d, dict) else None


def _reset_iso(resets_at) -> str | None:
    if isinstance(resets_at, (int, float)) and resets_at > 0:
        return datetime.fromtimestamp(resets_at, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    return None


def fallback_pause_until(now: datetime | None = None) -> str:
    n = now or datetime.now(timezone.utc)
    return (n + timedelta(seconds=QUOTA_PAUSE_FALLBACK_SEC)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def feed(res: RunResult, ev: dict) -> None:
    """이벤트 하나를 누적 결과에 반영한다."""
    res.events += 1
    t = ev.get("type")
    if t == "system" and ev.get("subtype") == "init":
        res.session_id = ev.get("session_id") or res.session_id
    elif t == "stream_event":
        e = ev.get("event") or {}
        d = e.get("delta") or {}
        if e.get("type") == "content_block_delta" and d.get("type") == "text_delta":
            res.partial_text += d.get("text", "")
    elif t == "assistant":
        for b in (ev.get("message") or {}).get("content") or []:
            if isinstance(b, dict) and b.get("type") == "tool_use":
                res.tool_calls += 1
    elif t == "rate_limit_event":
        info = ev.get("rate_limit_info") or {}
        if info.get("status") not in (None, "allowed", "allowed_warning"):
            res.quota = True
            res.quota_reset_at = _reset_iso(info.get("resetsAt"))
    elif t == "result":
        res.got_result = True
        res.session_id = ev.get("session_id") or res.session_id
        u = ev.get("usage") or {}
        res.tokens_in = int(u.get("input_tokens", 0)) + int(u.get("cache_creation_input_tokens", 0))
        res.tokens_out = int(u.get("output_tokens", 0))
        res.cache_read = int(u.get("cache_read_input_tokens", 0))
        res.text = ev.get("result") or res.partial_text
        if ev.get("is_error") or ev.get("subtype") not in (None, "success"):
            res.is_error = True
            res.error_reason = str(ev.get("subtype") or "cli_error")
            if _QUOTA_WORDS.search(res.text or "") or ev.get("api_error_status") == 429:
                res.quota = True


def run(argv: list[str], *, prompt: str, cwd: str, env: dict | None, deadline_sec: float,
        should_cancel: Callable[[], bool] | None = None,
        on_progress: Callable[[RunResult], None] | None = None,
        progress_every_sec: float = 1.0) -> RunResult:
    """CLI 를 실행해 stream-json 을 소비한다. 마감·취소 시 프로세스를 종료한다."""
    res = RunResult()
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            cwd=cwd, env=env, text=True, bufsize=1)
    try:
        proc.stdin.write(prompt)
        proc.stdin.close()
    except OSError:
        pass
    start = last = time.monotonic()
    import selectors
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    reason = None
    while True:
        now = time.monotonic()
        if now - start > deadline_sec:
            reason = "deadline"
        elif should_cancel and should_cancel():
            reason = "cancelled"
        if reason:
            proc.kill()
            break
        if sel.select(timeout=0.5):
            line = proc.stdout.readline()
            if not line:
                break
            ev = parse_line(line)
            if ev:
                feed(res, ev)
                if on_progress and now - last >= progress_every_sec:
                    last = now
                    on_progress(res)
        elif proc.poll() is not None:
            break
    sel.close()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    if reason:
        res.is_error, res.error_reason = True, reason
    elif not res.got_result:
        res.is_error, res.error_reason = True, f"no_result_rc{proc.returncode}"
    return res
