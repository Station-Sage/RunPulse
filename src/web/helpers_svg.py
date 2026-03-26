"""SVG 시각화 헬퍼 — 반원 게이지 + 레이더 차트."""
from __future__ import annotations

import html as _html
import math


def svg_semicircle_gauge(
    value: float,
    max_value: float = 100.0,
    label: str = "",
    color_stops: list[tuple[float, str]] | None = None,
    width: int = 220,
) -> str:
    """반원 SVG 게이지 (UTRS/CIRS용).

    Args:
        value: 현재 값 (0~max_value).
        max_value: 최대값.
        label: 게이지 아래 레이블.
        color_stops: [(threshold_pct, color), ...] 임계값 기반 색상. 없으면 그라데이션.
        width: SVG 너비(px).

    Returns:
        SVG HTML 문자열.
    """
    pct = max(0.0, min(1.0, value / max_value if max_value > 0 else 0.0))
    h = width // 2 + 20
    cx, cy, r = width // 2, width // 2, width // 2 - 16

    if color_stops:
        track_color = "rgba(255,255,255,0.15)"
        arc_color = "#4caf50"
        for threshold, color in sorted(color_stops):
            if pct * 100 >= threshold:
                arc_color = color
    else:
        arc_color = "#00d4ff"
        track_color = "rgba(255,255,255,0.15)"

    def polar(angle_deg: float) -> tuple[float, float]:
        """각도(도) → SVG 좌표. 상단 반원: 180°(좌) → 270°(상) → 360°(우)."""
        rad = math.radians(angle_deg)
        return cx + r * math.cos(rad), cy + r * math.sin(rad)

    # 상단 반원: 좌(180°) → 상(270°) → 우(360°)
    # needle_angle: 0%=180°(좌), 50%=270°(상), 100%=360°(우)
    needle_angle = 180.0 + pct * 180.0

    sx, sy = polar(180.0)   # 좌측 시작점
    ex, ey = polar(360.0)   # 우측 끝점
    vx, vy = polar(needle_angle)

    sw = max(1, width // 18)

    # 트랙: 좌→상→우 (반시계, sweep=0)
    track_path = f"M {sx:.1f},{sy:.1f} A {r},{r} 0 0,0 {ex:.1f},{ey:.1f}"
    # 값 arc: 좌 → needle_angle (반시계, sweep=0, 항상 short arc)
    value_path = f"M {sx:.1f},{sy:.1f} A {r},{r} 0 0,0 {vx:.1f},{vy:.1f}"

    needle_len = r - sw * 2
    tip_x = cx + needle_len * math.cos(math.radians(needle_angle))
    tip_y = cy + needle_len * math.sin(math.radians(needle_angle))

    val_disp = f"{value:.0f}"
    label_esc = _html.escape(label)

    return (
        f'<svg width="{width}" height="{h}" viewBox="0 0 {width} {h}" '
        f'style="display:block;margin:0 auto;">'
        f'<path d="{track_path}" fill="none" stroke="{track_color}" '
        f'stroke-width="{sw}" stroke-linecap="round"/>'
        f'<path d="{value_path}" fill="none" stroke="{arc_color}" '
        f'stroke-width="{sw}" stroke-linecap="round"/>'
        f'<line x1="{cx}" y1="{cy}" x2="{tip_x:.1f}" y2="{tip_y:.1f}" '
        f'stroke="#333" stroke-width="3" stroke-linecap="round"/>'
        f'<circle cx="{cx}" cy="{cy}" r="5" fill="#333"/>'
        f'<text x="{cx}" y="{cy - 4}" text-anchor="middle" '
        f'font-size="{width // 7}" font-weight="bold" fill="currentColor">{val_disp}</text>'
        f'<text x="{cx}" y="{cy + 18}" text-anchor="middle" '
        f'font-size="{width // 14}" fill="var(--muted)">{label_esc}</text>'
        f'</svg>'
    )


def svg_radar_chart(
    axes: dict[str, float],
    max_value: float = 100.0,
    compare_axes: dict[str, float] | None = None,
    width: int = 280,
) -> str:
    """순수 SVG 레이더 차트 (RMR 5축용).

    Args:
        axes: {축명: 값} 순서 있는 딕셔너리.
        max_value: 각 축 최대값.
        compare_axes: 비교용 (3개월 전 등) 데이터. None이면 생략.
        width: SVG 크기(px).

    Returns:
        SVG HTML 문자열.
    """
    n = len(axes)
    if n < 3:
        return "<p class='muted'>레이더 데이터 부족</p>"

    cx = cy = width // 2
    r = width // 2 - 30
    labels = list(axes.keys())
    values = list(axes.values())

    def point(i: int, val: float) -> tuple[float, float]:
        angle = math.radians(90 + 360 / n * i)
        ratio = max(0.0, min(1.0, val / max_value if max_value > 0 else 0.0))
        return (
            cx - r * ratio * math.cos(angle),
            cy - r * ratio * math.sin(angle),
        )

    def axis_point(i: int, ratio: float = 1.0) -> tuple[float, float]:
        angle = math.radians(90 + 360 / n * i)
        return (
            cx - r * ratio * math.cos(angle),
            cy - r * ratio * math.sin(angle),
        )

    grid_lines = []
    for level in (0.2, 0.4, 0.6, 0.8, 1.0):
        pts = " ".join(f"{axis_point(i, level)[0]:.1f},{axis_point(i, level)[1]:.1f}" for i in range(n))
        grid_lines.append(
            f'<polygon points="{pts}" fill="none" stroke="var(--card-border)" stroke-width="0.8"/>'
        )

    axis_lines = []
    for i in range(n):
        ax, ay = axis_point(i)
        axis_lines.append(
            f'<line x1="{cx}" y1="{cy}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="var(--card-border)" stroke-width="0.8"/>'
        )

    compare_polygon = ""
    if compare_axes:
        cvals = [compare_axes.get(k, 0.0) for k in labels]
        cpts = " ".join(f"{point(i, cvals[i])[0]:.1f},{point(i, cvals[i])[1]:.1f}" for i in range(n))
        compare_polygon = f'<polygon points="{cpts}" fill="rgba(255,170,0,0.15)" stroke="rgba(255,170,0,0.6)" stroke-width="1.5"/>'

    pts = " ".join(f"{point(i, values[i])[0]:.1f},{point(i, values[i])[1]:.1f}" for i in range(n))
    value_polygon = (
        f'<polygon points="{pts}" fill="rgba(0,180,255,0.2)" stroke="#00b4ff" stroke-width="2"/>'
    )

    dots = "".join(
        f'<circle cx="{point(i, values[i])[0]:.1f}" cy="{point(i, values[i])[1]:.1f}" r="4" fill="#00b4ff"/>'
        for i in range(n)
    )

    label_offset = 16
    label_els = []
    for i, lbl in enumerate(labels):
        ax, ay = axis_point(i, 1.0)
        lx = ax + (ax - cx) / r * label_offset
        ly = ay + (ay - cy) / r * label_offset
        label_els.append(
            f'<text x="{lx:.1f}" y="{ly:.1f}" text-anchor="middle" '
            f'dominant-baseline="middle" font-size="11" fill="currentColor">{_html.escape(lbl)}</text>'
        )

    inner = (
        "".join(grid_lines)
        + "".join(axis_lines)
        + compare_polygon
        + value_polygon
        + dots
        + "".join(label_els)
    )
    return (
        f'<svg width="{width}" height="{width}" viewBox="0 0 {width} {width}" '
        f'style="display:block;margin:0 auto;">{inner}</svg>'
    )
