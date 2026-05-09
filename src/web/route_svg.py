"""GPS 경로 SVG 썸네일 생성 — activity_streams에서 latlng 데이터를 SVG polyline으로 변환.

API 호출 없이 자체 렌더링. 동기화 시 또는 요청 시 생성.
"""
from __future__ import annotations

import html as _html
import sqlite3
from typing import Any


def render_route_svg(
    conn: sqlite3.Connection,
    activity_id: int,
    width: int = 80,
    height: int = 50,
    color: str = "#00d4ff",
    bg: str = "transparent",
) -> str:
    """활동의 GPS 경로를 SVG 미니맵으로 렌더링.

    Args:
        conn: DB 연결.
        activity_id: 활동 ID.
        width: SVG 너비 (px).
        height: SVG 높이 (px).
        color: 경로 선 색상.
        bg: 배경색.

    Returns:
        SVG HTML 문자열. 데이터 없으면 빈 문자열.
    """
    coords = _load_latlng(conn, activity_id)
    if not coords or len(coords) < 2:
        return ""
    return _coords_to_svg(coords, width, height, color, bg)


def _load_latlng(conn: sqlite3.Connection, activity_id: int) -> list[tuple[float, float]]:
    """activity_streams에서 latlng 좌표 로드. 그룹 내 다른 소스도 탐색."""
    # 1. 직접 조회
    rows = conn.execute(
        "SELECT latitude, longitude FROM activity_streams "
        "WHERE activity_id=? AND latitude IS NOT NULL AND longitude IS NOT NULL "
        "ORDER BY elapsed_sec",
        (activity_id,),
    ).fetchall()
    # 2. 없으면 같은 그룹의 다른 활동에서 탐색
    if not rows:
        group_row = conn.execute(
            "SELECT matched_group_id FROM activity_summaries WHERE id=?",
            (activity_id,),
        ).fetchone()
        if group_row and group_row[0]:
            rows = conn.execute(
                "SELECT s.latitude, s.longitude FROM activity_streams s "
                "JOIN activity_summaries a ON a.id=s.activity_id "
                "WHERE a.matched_group_id=? AND s.latitude IS NOT NULL AND s.longitude IS NOT NULL "
                "ORDER BY s.elapsed_sec",
                (group_row[0],),
            ).fetchall()
    return [(float(r[0]), float(r[1])) for r in rows] if rows else []


def _coords_to_svg(
    coords: list[tuple[float, float]],
    width: int,
    height: int,
    color: str,
    bg: str,
) -> str:
    """좌표 목록을 SVG polyline으로 변환."""
    # 다운샘플링 (최대 100포인트)
    if len(coords) > 100:
        step = len(coords) // 100
        coords = coords[::step]

    lats = [c[0] for c in coords]
    lngs = [c[1] for c in coords]
    min_lat, max_lat = min(lats), max(lats)
    min_lng, max_lng = min(lngs), max(lngs)

    # 패딩
    pad = 4
    draw_w = width - pad * 2
    draw_h = height - pad * 2

    lat_range = max_lat - min_lat or 0.001
    lng_range = max_lng - min_lng or 0.001

    # 종횡비 보정
    aspect = lng_range / lat_range
    if aspect > draw_w / draw_h:
        # 가로가 넓으면 세로 축소
        scale = draw_w / lng_range
    else:
        scale = draw_h / lat_range

    points = []
    for lat, lng in coords:
        x = pad + (lng - min_lng) * scale
        y = pad + (max_lat - lat) * scale  # Y 반전 (위도 증가 = 위쪽)
        points.append(f"{x:.1f},{y:.1f}")

    # 실제 SVG 크기 계산
    actual_w = (max_lng - min_lng) * scale + pad * 2
    actual_h = (max_lat - min_lat) * scale + pad * 2

    polyline = " ".join(points)
    return (
        f'<svg width="{width}" height="{height}" '
        f'viewBox="0 0 {actual_w:.0f} {actual_h:.0f}" '
        f'style="display:block;border-radius:8px;background:{bg};" '
        f'preserveAspectRatio="xMidYMid meet">'
        f'<polyline points="{polyline}" fill="none" stroke="{color}" '
        f'stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>'
        f'</svg>'
    )
