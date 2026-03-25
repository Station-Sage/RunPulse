"""활동 상세 — 그룹1: 오늘의 상태 (Daily Status Strip).

"오늘 뛸 수 있나?" — UTRS, CIRS, ACWR, RTTI, Training Readiness 를
가로 스트립으로 한눈에 보여준다.
"""
from __future__ import annotations

from .helpers_svg import svg_semicircle_gauge
from .views_activity_cards_common import group_header


# ── 미니 게이지 ─────────────────────────────────────────────────────────

def _mini_gauge(value: float | None, max_val: float, label: str,
                color_fn, width: int = 100) -> str:
    """소형 반원 게이지 + 해석 한 줄."""
    if value is None:
        return (
            f"<div style='flex:1;min-width:90px;text-align:center;'>"
            f"<div style='font-size:0.72rem;color:var(--muted);margin-bottom:2px;'>{label}</div>"
            f"<div style='font-size:0.82rem;color:var(--muted);'>—</div></div>"
        )
    v = float(value)
    color, interp = color_fn(v)
    stops = [(0, "var(--muted)"), (1, color)]
    gauge = svg_semicircle_gauge(v, max_val, "", stops, width)
    return (
        f"<div style='flex:1;min-width:90px;text-align:center;'>"
        f"<div style='font-size:0.72rem;color:var(--muted);margin-bottom:2px;font-weight:600;'>{label}</div>"
        f"{gauge}"
        f"<div style='font-size:0.68rem;color:{color};margin-top:-4px;'>{interp}</div>"
        f"</div>"
    )


def _utrs_color(v: float) -> tuple[str, str]:
    if v >= 70:
        return "var(--green)", "컨디션 최적"
    if v >= 50:
        return "var(--cyan)", "보통"
    if v >= 30:
        return "var(--orange)", "피로 누적"
    return "var(--red)", "휴식 필요"


def _cirs_color(v: float) -> tuple[str, str]:
    """CIRS는 낮을수록 좋음."""
    if v < 30:
        return "var(--green)", "안전"
    if v < 50:
        return "var(--cyan)", "낮은 위험"
    if v < 75:
        return "var(--orange)", "주의"
    return "var(--red)", "경고"


def _rtti_color(v: float) -> tuple[str, str]:
    if v <= 80:
        return "var(--cyan)", "여유 있음"
    if v <= 100:
        return "var(--green)", "적정"
    return "var(--red)", "과부하"


def _readiness_color(v: float) -> tuple[str, str]:
    if v >= 70:
        return "var(--green)", "준비 완료"
    if v >= 40:
        return "var(--orange)", "보통"
    return "var(--red)", "부족"


# ── ACWR 배지 (비율이므로 게이지 대신 텍스트 배지) ──────────────────────

def _acwr_badge(value: float | None) -> str:
    if value is None:
        return (
            "<div style='flex:1;min-width:90px;text-align:center;'>"
            "<div style='font-size:0.72rem;color:var(--muted);margin-bottom:2px;font-weight:600;'>ACWR</div>"
            "<div style='font-size:0.82rem;color:var(--muted);'>—</div></div>"
        )
    v = float(value)
    if v < 0.8:
        color, interp = "var(--cyan)", "부하 부족"
    elif v <= 1.3:
        color, interp = "var(--green)", "적절"
    elif v <= 1.5:
        color, interp = "var(--orange)", "주의"
    else:
        color, interp = "var(--red)", "과부하"
    return (
        "<div style='flex:1;min-width:90px;text-align:center;'>"
        "<div style='font-size:0.72rem;color:var(--muted);margin-bottom:2px;font-weight:600;'>ACWR</div>"
        f"<div style='font-size:1.6rem;font-weight:700;color:{color};line-height:1.2;'>{v:.2f}</div>"
        f"<div style='font-size:0.68rem;color:{color};'>{interp}</div>"
        "<div style='font-size:0.62rem;color:var(--muted);margin-top:2px;'>0.8~1.3 적정</div>"
        "</div>"
    )


# ── 메인 렌더 ───────────────────────────────────────────────────────────

def render_group1_daily_status(
    day_metrics: dict,
    day_metric_jsons: dict,
    garmin_detail: dict | None = None,
) -> str:
    """그룹1 — 일일 상태 가로 스트립.

    UTRS, CIRS, ACWR, RTTI, Training Readiness 5개 미니 게이지.
    """
    utrs = day_metrics.get("UTRS")
    cirs = day_metrics.get("CIRS")
    acwr = day_metrics.get("ACWR")
    rtti = day_metrics.get("RTTI")
    gd = garmin_detail or {}
    readiness = gd.get("training_readiness_score")

    # 모두 None이면 수집 중 안내
    if all(v is None for v in (utrs, cirs, acwr, rtti, readiness)):
        return (
            "<div class='card'>"
            + group_header("오늘의 상태", "오늘 뛸 수 있나?")
            + "<p class='muted' style='margin:0.3rem 0;'>데이터 수집 중입니다</p></div>"
        )

    panels = [
        _mini_gauge(utrs, 100, "UTRS", _utrs_color),
        _mini_gauge(cirs, 100, "CIRS", _cirs_color),
        _acwr_badge(acwr),
        _mini_gauge(rtti, 150, "RTTI", _rtti_color),
        _mini_gauge(readiness, 100, "Readiness", _readiness_color),
    ]

    return (
        "<div class='card'>"
        + group_header("오늘의 상태", "오늘 뛸 수 있나?")
        + "<div style='display:flex;gap:0.3rem;overflow-x:auto;padding:0.3rem 0;"
        "-webkit-overflow-scrolling:touch;'>"
        + "".join(panels)
        + "</div></div>"
    )
