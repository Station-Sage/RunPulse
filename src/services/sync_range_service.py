"""기간(range) 동기화 — 요청 추정(estimate)과 시작(trigger). 증분과 달리 cooldown 가드는 쓰지 않고 기간 정책만 본다."""
from __future__ import annotations

from datetime import date, datetime

from src.services.sync_trigger_service import SkipReason, TriggerResult, _checkers


def parse_range(frm: str | None, to: str | None, today: date | None = None) -> tuple[str, str, str | None]:
    """(from, to, 오류메시지). 오류가 없으면 메시지는 None."""
    today = today or date.today()
    try:
        f, t = date.fromisoformat(frm or ""), date.fromisoformat(to or "")
    except ValueError:
        return "", "", "from/to는 YYYY-MM-DD 형식이어야 해요"
    if f > t:
        return "", "", "시작일이 종료일보다 늦어요"
    if t > today:
        return "", "", "종료일이 오늘보다 늦어요"
    return f.isoformat(), t.isoformat(), None


def _used_recently(provider: str, now: datetime) -> tuple[int, int]:
    """(최근 15분, 최근 24시간) 동안 원장에 기록된 요청 수."""
    from src.utils.sync_jobs import list_recent_jobs
    u15 = u24 = 0
    for j in list_recent_jobs(provider, limit=50):
        try:
            at = datetime.fromisoformat(j.updated_at)
        except ValueError:
            continue
        age = (now - at).total_seconds()
        if age <= 900:
            u15 += j.req_count
        if age <= 86400:
            u24 += j.req_count
    return u15, u24


def estimate(provider: str, frm: str, to: str, now: datetime | None = None) -> dict:
    """요청 수 추정(일 단위 1회 + 배치당 1회)과 남은 호출 한도, 기간 정책 판정."""
    from src.utils.sync_jobs import RATE_LIMITS, WINDOW_DAYS, windows
    from src.utils.sync_policy import check_range_guard

    now = now or datetime.now()
    days = (date.fromisoformat(to) - date.fromisoformat(frm)).days + 1
    batches = len(windows(frm, to, WINDOW_DAYS.get(provider, 14)))
    lim = RATE_LIMITS.get(provider, {"per_15min": 50, "per_day": 500})
    u15, u24 = _used_recently(provider, now)
    guard = check_range_guard(provider, days)
    return {
        "provider": provider, "days": days, "batches": batches, "requests": days + batches,
        "rate_limit": {"window_15m_left": max(0, lim["per_15min"] - u15),
                       "daily_left": max(0, lim["per_day"] - u24)},
        "allowed": guard.allowed, "message_ko": guard.message_ko,
    }


def trigger_range(config: dict, user_id: str, sources: list[str], frm: str, to: str,
                  source_path: str = "range") -> TriggerResult:
    """소스별 판정(미연결·꺼짐·실행 중·대기·기간 정책) 후 통과한 소스만 시작."""
    from src.utils.config import enabled_sources
    from src.utils.sync_jobs import get_active_job
    from src.utils.sync_gates import wait_sec
    from src.utils.sync_state import is_running
    from src.web.bg_sync import _start_or_existing

    checkers, on = _checkers(), enabled_sources(config)
    runs: list[dict] = []
    skipped: list[SkipReason] = []
    days = (date.fromisoformat(to) - date.fromisoformat(frm)).days + 1
    from src.utils.sync_policy import check_range_guard
    for src in sources:
        st = checkers[src](config)
        if not st["ok"]:
            skipped.append(SkipReason(src, "not_connected", f"미연결 ({st['status']})"))
        elif src not in on:
            skipped.append(SkipReason(src, "disabled", "동기화 대상에서 꺼져 있어요"))
        elif is_running(src, user_id):
            job = get_active_job(src)
            skipped.append(SkipReason(src, "running", "이미 동기화 중이에요", job_id=job.id if job else None))
        elif not (guard := check_range_guard(src, days)).allowed:
            skipped.append(SkipReason(src, "range_too_large", guard.message_ko or "기간이 너무 길어요"))
        elif wait := wait_sec(src, user_id):
            skipped.append(SkipReason(src, "rate_limited", "요청 제한 대기 중이에요", wait))
        else:
            try:
                job_id, created = _start_or_existing(src, frm, to, config, user_id, source_path)
            except Exception:
                skipped.append(SkipReason(src, "start_failed", "동기화를 시작하지 못했어요"))
                continue
            if created:
                runs.append({"id": job_id, "provider": src, "state": "queued", "from": frm, "to": to})
            else:
                skipped.append(SkipReason(src, "running", "이미 동기화 중이에요", job_id=job_id or None))
    return TriggerResult(runs=runs, skipped=skipped)
