"""원장 정리(유지보수) — 재시작·stale 로 남은 running/pending 행을 stopped 로 닫는다."""
from __future__ import annotations

from datetime import datetime, timedelta

from src.utils.sync_jobs import _conn


def cleanup_stale_running_jobs() -> int:
    """프로세스 재시작 시 남아있는 'running'/'pending' 작업을 'stopped'로 정리.

    Returns:
        정리된 작업 수.
    """
    now = datetime.now().isoformat(timespec="seconds")
    with _conn() as conn:
        cur = conn.execute(
            "UPDATE sync_jobs SET status='stopped', updated_at=?, last_error='프로세스 재시작으로 중단됨' "
            "WHERE status IN ('running', 'pending')",
            (now,),
        )
        return cur.rowcount


def cleanup_stale_running_jobs_all_users(older_than_sec: int = 600) -> int:
    """모든 사용자 원장의 오래 갱신 없는 running/pending 작업을 'stopped'로 정리.

    import 시점엔 사용자 컨텍스트가 없어 default 원장만 정리되던 문제를 보완한다.
    다른 워커가 진행 중인 작업을 건드리지 않도록 older_than_sec 이상 갱신 없는 행만 닫는다.
    """
    from src.db_setup import _PROJECT_ROOT

    users_dir = _PROJECT_ROOT / "data" / "users"
    if not users_dir.is_dir():
        return 0
    cutoff = (datetime.now() - timedelta(seconds=older_than_sec)).isoformat(timespec="seconds")
    now = datetime.now().isoformat(timespec="seconds")
    total = 0
    for d in sorted(users_dir.iterdir()):
        if not (d / "sync_jobs.db").exists():
            continue
        try:
            with _conn(d.name) as conn:
                cur = conn.execute(
                    "UPDATE sync_jobs SET status='stopped', updated_at=?, last_error='프로세스 재시작으로 중단됨' "
                    "WHERE status IN ('running', 'pending') AND updated_at < ?",
                    (now, cutoff),
                )
                total += cur.rowcount
        except Exception:
            continue
    return total
