"""시각 직렬화·현지화 단일 출처 (TZ-1~, patterns/timezone-display.md).

- instant(updated_at 등 DB UTC 무표기) → `to_iso_instant` 로 오프셋 포함 ISO.
- 활동 시작 시각(wall-clock) → `to_local_wallclock` 으로 접미사 없는 현지 벽시계.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

KST_OFFSET_SEC = 9 * 3600


def _parse(text: str) -> datetime | None:
    try:
        return datetime.fromisoformat(text.strip().replace(" ", "T").replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def to_iso_instant(db_ts: str | None) -> str | None:
    """DB 시각 → 오프셋 포함 ISO 8601. 접미사 없으면 UTC 로 간주, 있으면 존중. 파싱 불가·빈 값은 None."""
    if not db_ts:
        return None
    dt = _parse(db_ts)
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat(timespec="seconds")


def _strip_suffix(text: str) -> str:
    """현지 시각에 붙은 가짜 Z·오프셋 접미사 제거(원문 형식 유지)."""
    t = text.strip()
    if t.endswith(("Z", "z")):
        return t[:-1]
    dt = _parse(t)
    if dt is not None and dt.tzinfo is not None and len(t) > 6 and t[-6] in "+-" and t[-3] == ":":
        return t[:-6]
    return t


def to_local_wallclock(
    local: str | None, utc: str | None = None, offset_sec: int | None = None,
) -> str | None:
    """활동 시작의 현지 벽시계(접미사 없음). 우선순위: 소스 현지 시각 → utc+offset → utc+KST(+9)."""
    if local and _parse(local) is not None:
        return _strip_suffix(local)
    if not utc:
        return None
    dt = _parse(utc)
    if dt is None:
        return None
    if dt.tzinfo is not None:
        dt = dt.astimezone(timezone.utc).replace(tzinfo=None)
    off = KST_OFFSET_SEC if offset_sec is None else int(offset_sec)
    return (dt + timedelta(seconds=off)).isoformat(timespec="seconds")
