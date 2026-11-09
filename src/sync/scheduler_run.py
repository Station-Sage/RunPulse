"""스케줄러 사용자 작업·기본 의존 — run_user(게이트·busy·서비스 토큰·완료 대기·원장 판정)와 multi 모드 기동(T5·T6).

run_user 는 사용자 1명 동기화를 끝까지(또는 20분 타임아웃까지) 점유한다. 결과 판정은 원장 job 상태로 한다.
"""
from __future__ import annotations

import logging
import random
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from typing import Callable

from src.sync import scheduler_policy as P
from src.sync.scheduler import MultiUserScheduler, RunResult, SchedCfg

log = logging.getLogger("runpulse.sched")

_instance: MultiUserScheduler | None = None
_instance_lock = threading.Lock()


# ── 기본 의존 ─────────────────────────────────────────────────
def default_users() -> list[str]:
    """registry 모드면 accounts.status='active', 아니면 data/users 디렉터리. non-default 가 있으면 default 제외."""
    from src.auth import auth_mode
    from src.utils.user_context import InvalidUserId, list_user_ids, validate_uid
    if auth_mode() == "registry":
        from src.auth import registry
        conn = registry.connect()
        try:
            rows = conn.execute("SELECT uid FROM accounts WHERE status='active' ORDER BY uid").fetchall()
        finally:
            conn.close()
        uids = []
        for (uid,) in rows:
            try:
                uids.append(validate_uid(uid))
            except InvalidUserId:
                continue
    else:
        uids = list_user_ids() or ["default"]
    non_default = [u for u in uids if u != "default"]
    return non_default or uids


def ledger_last_auto_run(uid: str) -> datetime | None:
    from src.utils.sync_ledger_query import last_auto_run
    return last_auto_run(uid)


def config_interval(uid: str) -> int:
    from src.utils.config import load_config
    return P.auto_cfg(load_config(user_id=uid))[1]


def suspend_source(uid: str, service: str) -> None:
    from src.utils import sync_gates
    sync_gates.block(service, P.AUTH_SUSPEND_SEC, reason="auth_suspended", user_id=uid)


def release_user() -> None:
    from src.utils.user_context import clear_current_user
    clear_current_user()


# ── 사용자 작업 ───────────────────────────────────────────────
def run_user(uid: str, *, clock: Callable[[], datetime] = datetime.now,
             timeout: float = P.RUN_TIMEOUT_SEC, start_sync=None, wait=None) -> RunResult:
    """사용자 1명 자동 동기화. 예외는 호출자(_execute)가 fail 로 기록한다."""
    from src.sync.auto_sync import _connected_sources
    from src.sync.bg_sync_wait import acquire_services, release_services, wait_user
    from src.utils.config import load_config
    from src.utils.sync_gates import wait_sec
    from src.utils.sync_jobs import get_job
    from src.utils.sync_ledger_query import is_busy
    from src.utils.user_context import set_current_user
    if start_sync is None:
        from src.sync.bg_sync import start_basic_sync as start_sync
    wait = wait or wait_user

    set_current_user(uid)
    config = load_config(user_id=uid)
    enabled, interval, days = P.auto_cfg(config)
    if not enabled:
        return RunResult("skipped_disabled", interval)
    sources = _connected_sources(config)
    if not sources:
        return RunResult("skipped_no_source", interval)
    now = clock()
    gated = {s: w for s in sources if (w := wait_sec(s, uid)) and w > 0}
    open_ = [s for s in sources if s not in gated]
    if not open_:
        return RunResult("skipped_gated", interval, sources,
                         retry_at=now + timedelta(seconds=min(gated.values())))
    if any(is_busy(s, uid) for s in sources):
        return RunResult("skipped_busy", interval, sources)
    tokens = acquire_services(open_)
    if tokens is None:
        return RunResult("skipped_slot", interval, open_)
    try:
        today = now.date() if isinstance(now, datetime) else date.today()
        from_date = (today - timedelta(days=days)).isoformat()
        jobs = start_sync(open_, {s: from_date for s in open_}, today.isoformat(), config, uid,
                          source_path="auto")
        job_ids = [j for j in jobs.values() if j]
        if not job_ids:
            return RunResult("skipped_no_source", interval, open_)
        done = wait(uid, job_ids, timeout)
        statuses = {}
        for svc, jid in jobs.items():
            job = get_job(jid) if jid else None
            statuses[svc] = job.status if job else None
        if not done.done:
            return RunResult("timeout", interval, open_, job_ids, statuses, detail=",".join(done.pending))
        return RunResult(P.classify(statuses), interval, open_, job_ids, statuses)
    finally:
        release_services(tokens)


# ── multi 모드 기동 ───────────────────────────────────────────
def build_default() -> MultiUserScheduler:
    from src.ops.store import default_store
    return MultiUserScheduler(
        clock=datetime.now, wait=None,
        executor=ThreadPoolExecutor(max_workers=P.MAX_CONCURRENT_USERS, thread_name_prefix="sched-user"),
        rng=random.Random(), users=default_users, trigger=run_user, store=default_store(),
        cfg=SchedCfg(pinned=P.pinned_uids()))


def start_multi() -> MultiUserScheduler:
    """프로세스 단일 스케줄러 기동(이미 있으면 그대로)."""
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = build_default()
        _instance.start()
        return _instance


def instance() -> MultiUserScheduler | None:
    return _instance


def poke(uid: str) -> bool:
    """multi 스케줄러가 있으면 poke. 없으면 False."""
    inst = _instance
    if inst is None:
        return False
    inst.poke(uid)
    return True
