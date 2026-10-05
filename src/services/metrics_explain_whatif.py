"""분해 v2 what-if(B-5) — "오늘 쉬면 내일 아침 값" 추정. 순수 함수 + 얇은 조립.

TSB: 오늘 부하 0으로 PMC를 하루 더 진행(CTL α=1/42, ATL α=1/7).
UTRS: TSB 항목만 추정치로 바꾸고 나머지 항목은 오늘 값 그대로(가중치 재정규화).
"""
from __future__ import annotations

from datetime import datetime

from src.metrics.bands import grade
from src.metrics.utrs import UTRSCalculator

_CTL_ALPHA = 1.0 / 42
_ATL_ALPHA = 1.0 / 7
_ASSUMPTION = "오늘 부하 0, 다른 입력은 오늘과 같다고 가정"


def tomorrow_tsb_if_rest(ctl: float, atl: float) -> float:
    """오늘 쉬었을 때 내일 아침 TSB (부하 0으로 PMC 1스텝)."""
    return ctl * (1 - _CTL_ALPHA) - atl * (1 - _ATL_ALPHA)


def utrs_with_tsb(terms: list[dict], new_tsb: float) -> float | None:
    """UTRS 항목(terms)에서 TSB 항목만 new_tsb로 교체한 점수. TSB 항목이 없으면 None."""
    weights = UTRSCalculator.WEIGHTS
    key_of = {"utrs_tsb": "tsb", "utrs_body_battery": "body_battery", "utrs_sleep": "sleep",
              "utrs_hrv": "hrv", "utrs_stress": "stress"}
    parts = []
    has_tsb = False
    for t in terms:
        key = key_of.get(t.get("slug"))
        if key is None or t.get("normalized") is None:
            continue
        if key == "tsb":
            has_tsb = True
            parts.append((weights[key], UTRSCalculator.tsb_component(new_tsb)))
        else:
            parts.append((weights[key], t["normalized"]))
    total = sum(w for w, _ in parts)
    if not has_tsb or total == 0:
        return None
    return sum(w * v for w, v in parts) / total


def build_what_if(slug: str, scope_id: str, *, ctl: float | None, atl: float | None,
                  terms: list[dict], today: str | None = None) -> list[dict]:
    """what_if 항목 리스트. 오늘이 아니거나 입력이 부족하면 빈 리스트."""
    today = today or datetime.now().strftime("%Y-%m-%d")
    if scope_id != today or ctl is None or atl is None:
        return []
    tsb_est = tomorrow_tsb_if_rest(ctl, atl)
    if slug == "tsb":
        value, band_slug = tsb_est, "tsb"
    elif slug == "utrs":
        value = utrs_with_tsb(terms, tsb_est)
        if value is None:
            return []
        band_slug = "utrs"
    else:
        return []
    band = grade(band_slug, value)
    return [{
        "key": "rest_today", "label": "오늘 휴식하면", "target": "내일 아침",
        "value_est": round(value), "status": band["status"] if band else None,
        "assumption": _ASSUMPTION,
    }]
