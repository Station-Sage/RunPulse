"""Story 직전 기간 비교 기준 — 진행 중인 기간은 이전 기간을 같은 일수로 자른다(M-14)."""
from __future__ import annotations

from datetime import date, timedelta


def compare_basis(scope: str, start: str, end: str, prev_start: str, prev_end: str, today: str) -> dict:
    """{prev_end, partial, label}. 현재 기간이 오늘을 지나 끝나지 않았으면(진행 중) 이전 기간도 같은 일수까지만.

    label 은 비교 섹션 머리말 보조 문구(임시, TXT-1). 진행 중이 아니면 label=None.
    """
    s, e, ps, pe = (date.fromisoformat(x) for x in (start, end, prev_start, prev_end))
    t = date.fromisoformat(today)
    month_full_end = _month_end(s) if scope == "month" else e
    in_progress = s <= t < month_full_end if scope == "month" else s <= t < e
    if not in_progress:
        return {"prev_end": prev_end, "partial": False, "label": None}
    days = (min(e, t) - s).days + 1
    cut = min(ps + timedelta(days=days - 1), pe)
    unit = "달" if scope == "month" else "주"
    span = f"{ps.day}~{cut.day}일" if scope == "month" else f"{ps.month}/{ps.day}~{cut.month}/{cut.day}"
    return {"prev_end": cut.isoformat(), "partial": True,
            "label": f"진행 중이라 이전 {unit}도 같은 {days}일({span})만 비교해요"}


def _month_end(d: date) -> date:
    nxt = date(d.year + (d.month == 12), d.month % 12 + 1, 1)
    return nxt - timedelta(days=1)
