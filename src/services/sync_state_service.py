"""동기화 상태 계약(SyncState) — 40-v2-unimplemented design §7.3 `GET /api/v1/data/sync-state`.

"마지막 동기화"가 세 저장소(`sync_jobs.updated_at`, `source_payloads.fetched_at`)에서
서로 달랐다(UX 리뷰 40 F-DATA-01). 작업 원장(`sync_jobs.db`)을 기준으로 소스별 시도·성공·새 데이터 시각과
오류를 하나의 계약으로 만든다. 셸·Today·Library·Data가 이 계약만 읽는다.

시각은 모두 오프셋 포함 ISO(+09:00 등 서버 로컬)로 낸다 — `source_payloads.fetched_at`은 SQLite UTC(표기 없음)라 변환한다.
"""
from __future__ import annotations

import sqlite3
from datetime import date, datetime

from src.services.activity_counts import activity_counts
from src.sync.sync_errors import MESSAGES_KO, classify_text
from src.utils.config import enabled_sources
from src.utils.sync_jobs import SyncJob, list_recent_jobs
from src.utils.sync_ledger_query import STALE_SEC
from src.utils.timefmt import to_iso_instant

SOURCES = ("garmin", "strava", "intervals", "runalyze")
STALE_HOURS = 12
_RECENT = 20

_CREDENTIAL_KEYS = {"garmin": "email", "strava": "refresh_token", "intervals": "api_key", "runalyze": "token"}

# 과거 행(error_code 없음)용 폴백: 상태·오류 문구 → code
_ERROR_RULES = [
    ("auth_required", None, "auth_expired"),
    ("rate_limited", None, "rate_limited"),
    (None, "403", "subscription_required"),
    (None, "401", "auth_expired"),
    (None, "429", "rate_limited"),
]
_STATE_GROUP = {"auth_expired": "auth", "subscription_required": "access"}


def is_connected(config: dict, provider: str) -> bool:
    """자격 증명이 저장돼 있으면 연결로 본다(카드의 연결 축과 같은 기준)."""
    key = _CREDENTIAL_KEYS.get(provider)
    return bool(key and config.get(provider, {}).get(key))


def _error_dict(code: str, job: SyncJob) -> dict:
    # D-04: 원시 예외 문자열(호스트·URL·athlete id)은 응답에 싣지 않는다 — 코드와 한국어 문구만
    msg, action = MESSAGES_KO.get(code, MESSAGES_KO["unknown"])
    return {"code": code, "message_ko": msg, "action": action, "http_status": job.http_status,
            "source_path": job.source_path, "at": _local_iso(job.updated_at)}


def _local_iso(naive_local: str | None) -> str | None:
    """원장 시각(서버 로컬, 표기 없음) → 오프셋 포함 ISO."""
    if not naive_local:
        return None
    try:
        return datetime.fromisoformat(naive_local).astimezone().isoformat(timespec="seconds")
    except ValueError:
        return None


def classify_error(job: SyncJob | None) -> dict | None:
    """원장 행의 실패를 코드로 분류. 진행 중·재시작으로 멈춘(stopped)·정상 완료 작업은 오류가 아니다
    (단 완료로 기록됐어도 오류 문구에 4xx가 남았으면 오류로 본다)."""
    if job is None:
        return None
    text = job.last_error or ""
    if job.status in ("running", "pending", "paused", "stopped", "cancelled"):
        return None
    if job.status == "completed" and not any(code in text for code in ("401", "403")):
        return None
    if job.error_code:
        return _error_dict(job.error_code, job)
    for status, needle, code in _ERROR_RULES:
        if (status and job.status == status) or (needle and needle in text):
            return _error_dict(code, job)
    return _error_dict(classify_text(text), job)


def _fresh(job: SyncJob, now: datetime) -> bool:
    """하트비트가 STALE_SEC 이내인 작업만 실행 중으로 본다(죽은 행 무시)."""
    try:
        upd = datetime.fromisoformat(job.updated_at)
        ref = now.replace(tzinfo=None) if upd.tzinfo is None else now
        return (ref - upd).total_seconds() <= STALE_SEC
    except ValueError:
        return False


def _source_state(provider: str, config: dict, on: set[str], jobs: list[SyncJob],
                  last_new_data_at: str | None, now: datetime) -> dict:
    connected = is_connected(config, provider)
    latest = jobs[0] if jobs else None
    success = next((j for j in jobs if j.status == "completed"), None)
    if success is None and len(jobs) >= _RECENT:  # D-06: 최근 창이 실패로 가득해도 마지막 성공은 찾는다
        success = next(iter(list_recent_jobs(provider, limit=1, status="completed")), None)
    running = next((j for j in jobs if j.status in ("running", "pending") and _fresh(j, now)), None)
    error = classify_error(latest)

    last_success_at = _local_iso(success.updated_at) if success else None
    if not connected:
        state = "not_connected"
    elif provider not in on:
        state = "disabled"
    elif running:
        state = "running"
    elif error:
        state = f"error-{_STATE_GROUP.get(error['code'], 'upstream')}"
    elif last_success_at is None:
        state = "never"
    elif (now - datetime.fromisoformat(last_success_at)).total_seconds() > STALE_HOURS * 3600:
        state = "idle-stale"
    else:
        state = "idle-ok"
    return {
        "provider": provider,
        "connection": "connected" if connected else "not_connected",
        "enabled": provider in on,
        "state": state,
        "last_attempt_at": _local_iso(latest.created_at) if latest else None,
        "last_success_at": last_success_at,
        "last_new_data_at": last_new_data_at,
        "last_error": error,
        "running": ({"job_id": running.id, "progress_pct": round(running.progress_pct)} if running else None),
    }


def _relative_ko(iso: str | None, now: datetime, attempted: bool = False) -> str:
    if not iso:  # D-06: 시도는 있었는데 성공이 없으면 '기록 없음'이 아니라 '성공 없음'
        return "성공한 동기화 없음" if attempted else "동기화 기록 없음"
    mins = int((now - datetime.fromisoformat(iso)).total_seconds() // 60)
    if mins < 1:
        return "방금 동기화"
    if mins < 60:
        return f"{mins}분 전 동기화"
    if mins < 60 * 24:
        return f"{mins // 60}시간 전 동기화"
    return f"{mins // (60 * 24)}일 전 동기화"


def get_sync_state(conn: sqlite3.Connection, config: dict, now: datetime | None = None) -> dict:
    """SyncState 계약 — 소스별 상태 + 전체 요약 + 데이터 기준일 + 결손 경고."""
    now = now or datetime.now().astimezone()
    on = set(enabled_sources(config))
    fetched = dict(conn.execute(
        "SELECT source, MAX(fetched_at) FROM source_payloads GROUP BY source").fetchall())
    latest_data_date = conn.execute(
        "SELECT MAX(d) FROM (SELECT MAX(substr(start_time, 1, 10)) AS d FROM activity_summaries"
        " UNION ALL SELECT MAX(date) FROM daily_wellness)").fetchone()[0]

    sources = [
        _source_state(p, config, on, list_recent_jobs(p, limit=_RECENT),
                      to_iso_instant(fetched.get(p)), now)
        for p in SOURCES
    ]
    active = [s for s in sources if s["enabled"] and s["connection"] == "connected"]
    successes = [s["last_success_at"] for s in active if s["last_success_at"]]
    last_success = max(successes) if successes else None
    if any(s["state"] == "running" for s in active):
        level = "running"
    elif any(s["state"].startswith("error-") for s in active):
        level = "error"
    elif not last_success or any(s["state"] in ("idle-stale", "never") for s in active):
        level = "stale"
    else:
        level = "ok"

    caveats = []
    today = now.date()
    for s in active:
        if s["state"].startswith("error-") or s["state"] == "idle-stale":
            base = s["last_new_data_at"] or s["last_success_at"]
            days = (today - date.fromisoformat(base[:10])).days if base else None
            if days and days >= 1:
                caveats.append({"code": "source_missing", "provider": s["provider"], "days": days})

    return {
        "as_of": now.isoformat(timespec="seconds"),
        "latest_data_date": latest_data_date,
        "overall": {"level": level, "label_ko": _relative_ko(
            last_success, now, any(s["last_attempt_at"] for s in active)), "last_success_at": last_success},
        "connected_count": sum(1 for s in sources if s["connection"] == "connected"),
        "activity_count": activity_counts(conn)["canonical_running"],
        "first_sync_running": any(s["state"] == "running" for s in active) and not last_success,
        "sources": sources,
        "caveats": caveats,
        "open_errors": sum(1 for s in active if s["state"].startswith("error-")),
    }
