"""활동 상세 — 그룹5: 폼/바이오메카닉스.

"폼이 좋은가?" — RMR 5축 레이더, GCT, 수직진동, 수직비율, 보폭, 케이던스.
서비스 탭에서 메인으로 승격.
"""
from __future__ import annotations

from .helpers import metric_row
from .helpers_svg import svg_radar_chart
from .views_activity_cards_common import (
    fmt_float1,
    fmt_int,
    group_header,
    no_data_msg,
    source_badge,
)


def _rmr_radar(day_metric_jsons: dict) -> str:
    """RMR 5축 레이더 차트."""
    rmr = day_metric_jsons.get("RMR")
    if not rmr or not isinstance(rmr, dict):
        return ""
    axes = rmr.get("axes")
    overall = rmr.get("overall")
    if not axes:
        return ""

    # 등급 배지
    if overall is not None:
        ov = float(overall)
        if ov >= 80:
            grade, color = "A", "var(--green)"
        elif ov >= 60:
            grade, color = "B", "var(--cyan)"
        elif ov >= 40:
            grade, color = "C", "var(--orange)"
        else:
            grade, color = "D", "var(--red)"
        grade_badge = (
            f"<div style='text-align:center;margin-top:4px;'>"
            f"<span style='font-size:1.2rem;font-weight:700;color:{color};'>{grade}</span>"
            f" <span style='font-size:0.78rem;color:var(--muted);'>({ov:.0f}점)</span></div>"
        )
    else:
        grade_badge = ""

    chart = svg_radar_chart(axes, max_value=100, width=200)
    return (
        "<div style='text-align:center;margin-bottom:0.5rem;'>"
        f"<div style='font-size:0.78rem;color:var(--muted);font-weight:600;margin-bottom:4px;'>RMR 러너 성숙도</div>"
        f"{chart}{grade_badge}</div>"
    )


def _bio_row(label: str, val, unit: str, src: str = "G") -> str:
    if val is None:
        return ""
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:0.35rem 0;border-bottom:1px solid var(--row-border);'>"
        f"<span style='font-size:0.82rem;color:var(--muted);'>{label}{source_badge(src)}</span>"
        f"<span style='font-size:0.88rem;font-weight:600;'>{val}{unit}</span></div>"
    )


def render_group5_biomechanics(
    day_metric_jsons: dict,
    garmin: dict | None = None,
    act: dict | None = None,
) -> str:
    """그룹5 — 폼/바이오메카닉스 카드.

    RMR 레이더 + 바이오 메트릭 (GCT, 수직진동, 수직비율, 보폭, 케이던스).
    """
    g = garmin or {}
    a = act or {}

    rmr = _rmr_radar(day_metric_jsons)
    gct = g.get("avg_ground_contact_time")
    vert_osc = g.get("avg_vertical_oscillation")
    vert_ratio = g.get("avg_vertical_ratio")
    stride = g.get("avg_stride_length")
    cadence = a.get("avg_cadence") or g.get("avg_run_cadence")

    has_bio = any(v is not None for v in (gct, vert_osc, vert_ratio, stride, cadence))
    if not rmr and not has_bio:
        return no_data_msg("폼/바이오메카닉스", "Garmin 바이오 데이터 또는 RMR 수집 중입니다")

    bio_rows = (
        _bio_row("GCT (접지 시간)", fmt_int(gct), " ms")
        + _bio_row("수직 진동", fmt_float1(vert_osc), " cm")
        + _bio_row("수직 비율", fmt_float1(vert_ratio), "%")
        + _bio_row("보폭", fmt_float1(stride), " cm")
        + _bio_row("케이던스", fmt_int(cadence), " spm")
    )

    return (
        "<div class='card'>"
        + group_header("폼/바이오메카닉스", "폼이 좋은가?")
        + rmr
        + bio_rows
        + "</div>"
    )
