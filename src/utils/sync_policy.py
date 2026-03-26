"""동기화 정책 — 서비스별 rate limit / cooldown / 기간 제한 정책 정의 및 검사."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class SyncPolicy:
    """서비스별 동기화 정책."""

    service_ko: str                      # 한글 서비스명
    min_incremental_interval_sec: int    # 증분 동기화 최소 간격 (초)
    recommended_max_days: int            # 기간 동기화 권장 최대 일수
    hard_max_days: int                   # 기간 동기화 절대 최대 일수 (초과 시 차단)
    per_request_sleep_sec: float         # 요청 간 sleep (초) — sync 함수에서 사용
    near_limit_threshold: float = 0.80  # usage/limit 비율 임계치 (이상 = 고비용 호출 축소)
    allow_partial_success: bool = True   # 부분 성공 허용 여부


@dataclass
class SyncGuardResult:
    """동기화 허용 여부 검사 결과."""

    allowed: bool
    adjusted_days: Optional[int] = None    # 자동 축소된 일수 (None = 원본 유지)
    retry_after_sec: Optional[int] = None  # 재시도까지 남은 초
    message_ko: Optional[str] = None       # 사용자 노출 한글 메시지
    reason: Optional[str] = None           # ok | cooldown | range_too_large | range_auto_reduced | running


# ── 서비스별 정책 ────────────────────────────────────────────────────────
POLICIES: dict[str, SyncPolicy] = {
    "garmin": SyncPolicy(
        service_ko="Garmin",
        min_incremental_interval_sec=300,    # 5분 — 반복 로그인 차단 방지
        recommended_max_days=30,
        hard_max_days=90,
        per_request_sleep_sec=0.8,           # Garmin Connect 과부하 방지 (1.5→0.8)
    ),
    "strava": SyncPolicy(
        service_ko="Strava",
        min_incremental_interval_sec=120,    # 2분 — 15분 창 200 req 제한 고려
        recommended_max_days=60,
        hard_max_days=180,
        per_request_sleep_sec=0.5,
    ),
    "intervals": SyncPolicy(
        service_ko="Intervals.icu",
        min_incremental_interval_sec=180,    # 3분
        recommended_max_days=90,
        hard_max_days=365,
        per_request_sleep_sec=0.3,
    ),
    "runalyze": SyncPolicy(
        service_ko="Runalyze",
        min_incremental_interval_sec=600,    # 10분 — free 계정 읽기 제한 고려
        recommended_max_days=30,
        hard_max_days=90,
        per_request_sleep_sec=1.0,
    ),
}


# ── 증분 동기화 검사 ─────────────────────────────────────────────────────
def check_incremental_guard(
    service: str,
    last_sync_at: Optional[datetime],
    now: Optional[datetime] = None,
) -> SyncGuardResult:
    """증분 동기화 cooldown 검사.

    Args:
        service: 서비스 키 (garmin / strava / intervals / runalyze).
        last_sync_at: 마지막 동기화 완료 시각. None 이면 제한 없음.
        now: 현재 시각 (None 이면 datetime.now() 사용).

    Returns:
        SyncGuardResult.
    """
    if service not in POLICIES:
        return SyncGuardResult(allowed=True, reason="ok")
    policy = POLICIES[service]
    if last_sync_at is None:
        return SyncGuardResult(allowed=True, reason="ok")
    if now is None:
        now = datetime.now()

    elapsed = (now - last_sync_at).total_seconds()
    if elapsed < policy.min_incremental_interval_sec:
        remain = int(policy.min_incremental_interval_sec - elapsed)
        return SyncGuardResult(
            allowed=False,
            retry_after_sec=remain,
            reason="cooldown",
            message_ko=(
                f"{policy.service_ko} 동기화가 최근에 실행되었습니다. "
                f"{_fmt_duration(remain)} 후 다시 시도하세요."
            ),
        )
    return SyncGuardResult(allowed=True, reason="ok")


# ── 기간 동기화 검사 ─────────────────────────────────────────────────────
def check_range_guard(service: str, days: int) -> SyncGuardResult:
    """기간 동기화 범위 검사.

    Args:
        service: 서비스 키.
        days: 요청 일수.

    Returns:
        SyncGuardResult.
    """
    if service not in POLICIES:
        return SyncGuardResult(allowed=True, reason="ok")
    policy = POLICIES[service]

    if days > policy.hard_max_days:
        return SyncGuardResult(
            allowed=False,
            adjusted_days=policy.recommended_max_days,
            reason="range_too_large",
            message_ko=(
                f"{policy.service_ko} 기간 동기화 범위({days}일)가 너무 큽니다. "
                f"최대 {policy.hard_max_days}일까지 허용되며, "
                f"권장 범위는 {policy.recommended_max_days}일입니다."
            ),
        )

    if days > policy.recommended_max_days:
        return SyncGuardResult(
            allowed=True,
            adjusted_days=days,
            reason="range_auto_reduced",
            message_ko=(
                f"{policy.service_ko} 요청 범위({days}일)가 권장치({policy.recommended_max_days}일)를 초과합니다. "
                f"API 부하가 높을 수 있으며 일부 데이터가 생략될 수 있습니다."
            ),
        )

    return SyncGuardResult(allowed=True, reason="ok")


# ── rate limit 근접 여부 ──────────────────────────────────────────────────
def should_reduce_expensive_calls(service: str, rate_state: dict) -> bool:
    """rate_state 기반으로 고비용 API 호출(detail/stream) 축소 여부 판단.

    Args:
        service: 서비스 키.
        rate_state: {"usage": int, "limit": int} — 현재 사용량/한도.

    Returns:
        True 이면 고비용 호출 생략 권고.
    """
    if service not in POLICIES:
        return False
    policy = POLICIES[service]
    usage = rate_state.get("usage", 0)
    limit = rate_state.get("limit", 0)
    if limit <= 0:
        return False
    return (usage / limit) >= policy.near_limit_threshold


# ── 내부 유틸 ────────────────────────────────────────────────────────────
def _fmt_duration(seconds: int) -> str:
    """초를 한글 시간 문자열로 변환."""
    if seconds < 60:
        return f"{seconds}초"
    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}분"
    hours, rem = divmod(minutes, 60)
    return f"{hours}시간 {rem}분" if rem else f"{hours}시간"
