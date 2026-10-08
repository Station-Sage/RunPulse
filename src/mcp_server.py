"""RunPulse MCP 서버 — Claude Desktop/CLI 등 MCP 클라이언트에서 러닝 데이터 조회 (stdio, 읽기 전용).

사용법:
  RUNPULSE_USER_ID=<user_id> python3 -m src.mcp_server   # 프로젝트 루트에서 실행

Claude Code/Desktop 설정 예:
  {"mcpServers": {"runpulse": {
      "command": "python3", "args": ["-m", "src.mcp_server"], "cwd": "/path/to/RunPulse",
      "env": {"RUNPULSE_USER_ID": "<user_id>"}}}}

- RUNPULSE_USER_ID 필수. 미지정 시 시작하지 않는다 (과거에는 활동 0건인 default DB를
  조용히 열어 빈 결과만 돌려줬다).
- DB는 읽기 전용(mode=ro)으로 연다.
- 프레임: MCP stdio 사양대로 줄바꿈으로 구분된 JSON 한 줄 = 메시지 하나.
- 도구 목록은 TOOL_DECLARATIONS, 호출 규칙은 tool_guide.USAGE_GUIDE (initialize instructions).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import sys
from pathlib import Path

from src.utils.log_config import setup_logging
setup_logging(stderr=True)  # stdout은 MCP JSON-RPC 프로토콜 전용
log = logging.getLogger("runpulse-mcp")


def resolve_db_path(user_id: str | None = None) -> Path:
    """RUNPULSE_USER_ID(또는 인자)로 유저 DB 경로를 결정. 없으면 명확한 오류."""
    from src.db_setup import get_db_path

    uid = (user_id if user_id is not None else os.environ.get("RUNPULSE_USER_ID", "")).strip()
    if not uid:
        raise RuntimeError("RUNPULSE_USER_ID 환경변수가 필요합니다 (data/users/ 아래 유저 ID).")
    if Path(uid).name != uid:
        raise RuntimeError(f"잘못된 RUNPULSE_USER_ID: {uid!r}")
    path = get_db_path(uid, create=False)
    if not path.exists():
        raise FileNotFoundError(f"DB not found: {path}")
    return path


def _get_conn(db_path: Path) -> sqlite3.Connection:
    """읽기 전용 연결. 도구는 조회만 하므로 쓰기 시도는 즉시 실패해야 한다."""
    from src.mcp_remote.safe_conn import connect_readonly

    return connect_readonly(db_path)


def _read_message() -> dict | None:
    """stdin에서 JSON-RPC 메시지 한 줄 읽기. EOF면 None."""
    while True:
        line = sys.stdin.readline()
        if not line:
            return None
        if line.strip():
            return json.loads(line)


def _write_message(msg: dict) -> None:
    """stdout으로 JSON-RPC 메시지 한 줄 쓰기 (메시지 내부 개행 금지)."""
    sys.stdout.write(json.dumps(msg, ensure_ascii=False, separators=(",", ":")) + "\n")
    sys.stdout.flush()


def handle_request(msg: dict, db_path: Path) -> dict | None:
    """메시지 하나 처리. 알림(notification)이면 None."""
    from src.mcp_remote.protocol import handle_message

    return handle_message(msg, lambda: _get_conn(db_path))


def main() -> None:
    """MCP 서버 메인 루프 (stdio)."""
    try:
        db_path = resolve_db_path()
    except (RuntimeError, FileNotFoundError) as exc:
        log.error("%s", exc)
        sys.exit(2)
    log.info("RunPulse MCP 서버 시작 (DB: %s, read-only)", db_path)

    while True:
        try:
            msg = _read_message()
        except (KeyboardInterrupt, json.JSONDecodeError) as exc:
            if isinstance(exc, KeyboardInterrupt):
                break
            log.warning("잘못된 JSON 무시: %s", exc)
            continue
        if msg is None:
            break
        log.info("← %s (id=%s)", msg.get("method", ""), msg.get("id"))
        resp = handle_request(msg, db_path)
        if resp is not None:
            _write_message(resp)


if __name__ == "__main__":
    main()
