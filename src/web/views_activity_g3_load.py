"""활동 상세 — 그룹3: 부하/노력.

"얼마나 힘들었나?" — TRIMP+WLEI 메인, RelativeEffort/Training Load/
Suffer Score/Training Effect 서브행 (소스 배지).
"""
from __future__ import annotations

from .views_activity_cards_common import (
    fmt_float1,
    fmt_int,
    group_header,
    metric_interp_badge,
    metric_tooltip_icon,
    no_data_msg,
    source_badge,
)


def _main_row(label: str, val, unit: str, key: str, badge_src: str = "RP") -> str:
    """메인 메트릭 행 (큰 글씨 + 해석 뱃지)."""
    if val is None:
        return ""
    v = float(val)
    badge = metric_interp_badge(key, v)
    icon = metric_tooltip_icon(key)
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:0.5rem 0;border-bottom:1px solid var(--row-border);'>"
        f"<span style='font-size:0.9rem;color:var(--fg);font-weight:600;'>{label}{icon}{source_badge(badge_src)}</span>"
        f"<span style='font-size:1.1rem;font-weight:700;'>{v:.1f}{unit}{badge}</span>"
        "</div>"
    )


def _sub_row(label: str, val, unit: str, src: str) -> str:
    """서브 메트릭 행 (작은 글씨 + 소스 배지)."""
    if val is None:
        return ""
    v = float(val)
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:0.3rem 0;border-bottom:1px solid var(--row-border);'>"
        f"<span style='font-size:0.8rem;color:var(--muted);'>{label}{source_badge(src)}</span>"
        f"<span style='font-size:0.85rem;'>{v:.1f}{unit}</span>"
        "</div>"
    )


def _wlei_detail(act_metric_jsons: dict) -> str:
    """WLEI 날씨 보정 비율 상세."""
    mj = act_metric_jsons.get("WLEI") or {}
    temp_stress = mj.get("temp_stress")
    hum_stress = mj.get("humidity_stress")
    if temp_stress is None and hum_stress is None:
        return ""
    parts = []
    if temp_stress is not None:
        parts.append(f"기온 ×{float(temp_stress):.2f}")
    if hum_stress is not None:
        parts.append(f"습도 ×{float(hum_stress):.2f}")
    return (
        f"<div style='font-size:0.72rem;color:var(--muted);padding:0.2rem 0;'>"
        f"날씨 보정: {' / '.join(parts)}</div>"
    )


def render_group3_load(
    act_metrics: dict,
    act_metric_jsons: dict,
    service_metrics: dict | None = None,
    garmin: dict | None = None,
    strava: dict | None = None,
) -> str:
    """그룹3 — 부하/노력 카드."""
    trimp = act_metrics.get("TRIMP")
    wlei = act_metrics.get("WLEI")
    rel_effort = act_metrics.get("RelativeEffort")
    g = garmin or {}
    s = strava or {}
    svc = service_metrics or {}

    # Garmin Training Load
    training_load = g.get("training_load")
    # Strava Suffer Score
    suffer = s.get("suffer_score")
    # Garmin Training Effect
    ate = g.get("training_effect_aerobic")
    ante = g.get("training_effect_anaerobic")

    if all(v is None for v in (trimp, wlei, rel_effort, training_load, suffer, ate)):
        return no_data_msg("부하/노력", "TRIMP·WLEI 데이터 수집 중입니다")

    parts = [
        "<div class='card'>",
        group_header("부하/노력", "얼마나 힘들었나?"),
        _main_row("TRIMP", trimp, "", "TRIMP"),
        _main_row("WLEI", wlei, "", "WLEI"),
        _wlei_detail(act_metric_jsons),
    ]

    # 서브 행
    sub_rows = [
        _sub_row("Relative Effort", rel_effort, "", "RP"),
        _sub_row("Training Load", training_load, "", "G"),
        _sub_row("Suffer Score", suffer, "", "S"),
    ]
    if ate is not None:
        sub_rows.append(_sub_row("ATE (유산소)", ate, "", "G"))
    if ante is not None:
        sub_rows.append(_sub_row("AnTE (무산소)", ante, "", "G"))

    active_subs = [r for r in sub_rows if r]
    if active_subs:
        parts.append(
            "<p style='font-size:0.72rem;color:var(--muted);margin:0.5rem 0 0.2rem;font-weight:600;'>서비스 메트릭</p>"
        )
        parts.extend(active_subs)

    return "".join(p for p in parts if p) + "</div>"
