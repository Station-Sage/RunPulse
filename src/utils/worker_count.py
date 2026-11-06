"""웹 프로세스 워커 수 추정 — gunicorn `--workers`/`-w`, `GUNICORN_CMD_ARGS`, `WEB_CONCURRENCY`. 메모리 상태 기능의 단일 워커 전제 점검용."""
from __future__ import annotations

import logging
import os
import shlex
import sys
from collections.abc import Mapping, Sequence

log = logging.getLogger(__name__)


def _from_args(args: Sequence[str]) -> int | None:
    found = None
    for i, a in enumerate(args):
        val = None
        if a in ("--workers", "-w") and i + 1 < len(args):
            val = args[i + 1]
        elif a.startswith("--workers="):
            val = a.split("=", 1)[1]
        elif a.startswith("-w") and a[2:].isdigit():
            val = a[2:]
        if val is not None and val.strip().isdigit():
            found = int(val)
    return found


def detect_worker_count(env: Mapping[str, str] | None = None, argv: Sequence[str] | None = None) -> int:
    """명령행 > GUNICORN_CMD_ARGS > WEB_CONCURRENCY 순. 알 수 없으면 1."""
    env = os.environ if env is None else env
    argv = sys.argv if argv is None else argv
    n = _from_args(list(argv))
    if n is None:
        try:
            n = _from_args(shlex.split(env.get("GUNICORN_CMD_ARGS", "")))
        except ValueError:
            n = None
    if n is None:
        raw = (env.get("WEB_CONCURRENCY") or "").strip()
        n = int(raw) if raw.isdigit() else None
    return n if n and n > 0 else 1


def check_single_worker(env: Mapping[str, str] | None = None, argv: Sequence[str] | None = None) -> bool:
    """워커가 1개면 True. 여러 개면 경고 로그 후 Garmin MFA 를 비활성(MFA_UNAVAILABLE)으로 돌린다."""
    from src.services import garmin_mfa_store

    n = detect_worker_count(env, argv)
    single = n <= 1
    garmin_mfa_store.set_multi_worker(not single)
    if not single:
        log.warning("[startup] 웹 워커 %d개 감지 — Garmin MFA 대기 상태는 단일 워커 전제라 비활성화합니다", n)
    return single
