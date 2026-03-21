"""활동 목록 뷰 — Flask Blueprint.

/activities
  - 날짜 범위·소스·유형 필터
  - 페이지네이션 (20개/페이지)
  - 각 활동에서 /activity/deep 심층 링크
  - 상단 요약 통계 (총 활동 수, 총 거리)
"""
from __future__ import annotations

import html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, request

from src.utils.pace import seconds_to_pace
from .helpers import db_path, fmt_duration, html_page, make_table, safe_str

activities_bp = Blueprint("activities", __name__)

_PAGE_SIZE = 20
_SOURCES = ["garmin", "strava", "intervals", "runalyze"]
_TYPES = ["running", "run", "virtualrun", "treadmill", "highintensityintervaltraining"]


# ── 쿼리 헬퍼 ────────────────────────────────────────────────────────────

def _to_int(value, default: int) -> int:
    try:
        return max(1, int(value))
    except Exception:
        return default


def _build_where(
    source: str,
    act_type: str,
    date_from: str,
    date_to: str,
) -> tuple[str, list]:
    """WHERE 절 및 파라미터 리스트 생성."""
    conditions = []
    params: list = []

    if source and source in _SOURCES:
        conditions.append("source = ?")
        params.append(source)

    if act_type == "running":
        placeholders = ",".join("?" * len(_TYPES))
        conditions.append(f"activity_type IN ({placeholders})")
        params.extend(_TYPES)

    if date_from:
        conditions.append("start_time >= ?")
        params.append(date_from)

    if date_to:
        # date_to 당일 포함: "YYYY-MM-DDT99" 까지
        conditions.append("start_time <= ?")
        params.append(date_to + "T99")

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return where, params


def _fmt_pace(avg_pace_sec_km) -> str:
    if avg_pace_sec_km is None:
        return "—"
    try:
        return seconds_to_pace(int(avg_pace_sec_km))
    except Exception:
        return str(avg_pace_sec_km)


def _fmt_dist(value) -> str:
    if value is None:
        return "—"
    try:
        return f"{float(value):.2f}"
    except Exception:
        return str(value)


# ── 렌더링 헬퍼 ─────────────────────────────────────────────────────────

def _render_filter_form(
    source: str, act_type: str, date_from: str, date_to: str, page: int
) -> str:
    """필터 폼 카드."""
    source_opts = "<option value=''>전체 소스</option>" + "".join(
        f"<option value='{s}'{' selected' if source == s else ''}>{s}</option>"
        for s in _SOURCES
    )
    type_opts = (
        "<option value=''>전체 유형</option>"
        f"<option value='running'{'selected' if act_type == 'running' else ''}>달리기</option>"
    )
    return (
        "<div class='card'>"
        "<form method='get' action='/activities' "
        "style='display:flex; gap:0.8rem; align-items:flex-end; flex-wrap:wrap;'>"
        "<label style='display:flex; flex-direction:column; font-size:0.85rem;'>소스"
        f"<select name='source'>{source_opts}</select></label>"
        "<label style='display:flex; flex-direction:column; font-size:0.85rem;'>유형"
        f"<select name='type'>{type_opts}</select></label>"
        "<label style='display:flex; flex-direction:column; font-size:0.85rem;'>시작일"
        f"<input type='date' name='from' value='{html.escape(date_from)}'></label>"
        "<label style='display:flex; flex-direction:column; font-size:0.85rem;'>종료일"
        f"<input type='date' name='to' value='{html.escape(date_to)}'></label>"
        "<button type='submit' style='height:2rem;'>조회</button>"
        f"<a href='/activities' style='line-height:2rem; font-size:0.85rem;'>초기화</a>"
        "</form>"
        "</div>"
    )


def _render_summary(total: int, total_dist) -> str:
    """요약 통계 한 줄."""
    dist_str = f"{float(total_dist):.1f} km" if total_dist else "—"
    return (
        f"<p class='muted'>총 <strong>{total}</strong>개 활동 "
        f"| 총 거리 <strong>{dist_str}</strong></p>"
    )


def _render_activity_table(rows: list[tuple]) -> str:
    """활동 목록 테이블 (심층 링크 포함)."""
    if not rows:
        return "<p class='muted'>조건에 맞는 활동이 없습니다.</p>"

    headers = ["날짜", "소스", "유형", "거리(km)", "시간", "페이스", "심박", "심층 분석"]
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows = []
    for row in rows:
        act_id, source, act_type, start_time, dist_km, dur_sec, avg_pace, avg_hr = row
        deep_url = f"/activity/deep?id={act_id}"
        date_str = str(start_time)[:10] if start_time else "—"
        cols = (
            f"<td>{html.escape(date_str)}</td>"
            f"<td>{html.escape(str(source))}</td>"
            f"<td>{html.escape(str(act_type))}</td>"
            f"<td>{html.escape(_fmt_dist(dist_km))}</td>"
            f"<td>{html.escape(fmt_duration(dur_sec))}</td>"
            f"<td>{html.escape(_fmt_pace(avg_pace))}</td>"
            f"<td>{html.escape(str(avg_hr) if avg_hr else '—')}</td>"
            f"<td><a href='{html.escape(deep_url)}'>심층</a></td>"
        )
        body_rows.append(f"<tr>{cols}</tr>")

    return (
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def _render_pagination(page: int, total: int, base_qs: str) -> str:
    """페이지 네비게이션."""
    total_pages = max(1, (total + _PAGE_SIZE - 1) // _PAGE_SIZE)
    if total_pages <= 1:
        return ""

    parts = []
    if page > 1:
        parts.append(f"<a href='/activities?{base_qs}&page={page - 1}'>&laquo; 이전</a>")
    parts.append(f"<span class='muted'> {page} / {total_pages} </span>")
    if page < total_pages:
        parts.append(f"<a href='/activities?{base_qs}&page={page + 1}'>다음 &raquo;</a>")

    return "<div style='margin:1rem 0; display:flex; gap:1rem;'>" + "".join(parts) + "</div>"


# ── 라우트 ────────────────────────────────────────────────────────────────

@activities_bp.get("/activities")
def activities_list():
    """활동 목록 페이지."""
    dpath = db_path()
    if not dpath.exists():
        body = "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return html_page("활동 목록", body)

    # 필터 파라미터
    source = request.args.get("source", "").strip()
    act_type = request.args.get("type", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    page = _to_int(request.args.get("page", "1"), 1)
    offset = (page - 1) * _PAGE_SIZE

    # 기본 날짜 범위: 최근 90일
    if not date_from and not date_to:
        default_from = (date.today() - timedelta(days=90)).isoformat()
        date_from = default_from

    where, params = _build_where(source, act_type, date_from, date_to)

    try:
        with sqlite3.connect(str(dpath)) as conn:
            # 전체 카운트 + 총 거리
            count_row = conn.execute(
                f"SELECT COUNT(*), SUM(distance_km) FROM activity_summaries {where}",
                params,
            ).fetchone()
            total = int(count_row[0]) if count_row else 0
            total_dist = count_row[1] if count_row else None

            # 페이지 데이터
            rows = conn.execute(
                f"""
                SELECT id, source, activity_type, start_time,
                       distance_km, duration_sec, avg_pace_sec_km, avg_hr
                FROM activity_summaries
                {where}
                ORDER BY start_time DESC
                LIMIT ? OFFSET ?
                """,
                [*params, _PAGE_SIZE, offset],
            ).fetchall()

    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return html_page("활동 목록", body)

    # 쿼리스트링 재조립 (페이지 네비용)
    qs_parts = []
    if source:
        qs_parts.append(f"source={html.escape(source)}")
    if act_type:
        qs_parts.append(f"type={html.escape(act_type)}")
    if date_from:
        qs_parts.append(f"from={html.escape(date_from)}")
    if date_to:
        qs_parts.append(f"to={html.escape(date_to)}")
    base_qs = "&".join(qs_parts)

    from .sync_ui import sync_card_html
    from .helpers import last_sync_info
    from src.utils.sync_state import get_all_states
    sync_btn = sync_card_html(
        last_sync=last_sync_info(["garmin", "strava", "intervals", "runalyze"]),
        sync_states=get_all_states(),
    )

    body = (
        sync_btn
        + _render_filter_form(source, act_type, date_from, date_to, page)
        + _render_summary(total, total_dist)
        + _render_activity_table(rows)
        + _render_pagination(page, total, base_qs)
    )
    return html_page("활동 목록", body)
