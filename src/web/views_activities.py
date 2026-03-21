"""활동 목록 뷰 — Flask Blueprint.

/activities
  - 날짜 범위·소스·유형 필터
  - 페이지네이션 (20개/페이지)
  - 통합 활동 행 (Garmin 우선 병합)
  - 서브트리 확장/축소 (▶/▼ 토글)
  - 소스별 분리 버튼
  - 체크박스 선택 → 묶기 플로팅 툴바
"""
from __future__ import annotations

import html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, request

from src.utils.pace import seconds_to_pace
from src.services.unified_activities import (
    SOURCE_COLORS,
    UnifiedActivity,
    fetch_unified_activities,
)
from .helpers import db_path, fmt_duration, html_page

activities_bp = Blueprint("activities", __name__)

_PAGE_SIZE = 20


# ── 포맷 헬퍼 ────────────────────────────────────────────────────────────

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


def _source_badge(source: str) -> str:
    color = SOURCE_COLORS.get(source, "#888")
    label = html.escape(source)
    return (
        f"<span style='background:{color}; color:#fff; border-radius:3px; "
        f"padding:1px 5px; font-size:0.75rem; white-space:nowrap;'>{label}</span>"
    )


def _provenance_tip(source: str | None) -> str:
    """값 출처를 나타내는 컬러 이니셜 뱃지 (목록 셀 내 인라인)."""
    if not source:
        return ""
    color = SOURCE_COLORS.get(source, "#888")
    return (
        f"<sup style='color:{color}; font-size:0.65rem; font-weight:bold; "
        f"margin-left:2px;' title='{html.escape(source)} 기준'>"
        f"{html.escape(source[0].upper())}</sup>"
    )


# ── 필터 폼 ─────────────────────────────────────────────────────────────

def _render_filter_form(
    source: str, act_type: str, date_from: str, date_to: str
) -> str:
    _SOURCES = ["garmin", "strava", "intervals", "runalyze"]
    source_opts = "<option value=''>전체 소스</option>" + "".join(
        f"<option value='{s}'{' selected' if source == s else ''}>{s}</option>"
        for s in _SOURCES
    )
    type_selected = " selected" if act_type == "running" else ""
    type_opts = (
        "<option value=''>전체 유형</option>"
        f"<option value='running'{type_selected}>달리기</option>"
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
        "<a href='/activities' style='line-height:2rem; font-size:0.85rem;'>초기화</a>"
        "</form>"
        "</div>"
    )


# ── 요약 통계 ─────────────────────────────────────────────────────────────

def _render_summary(total: int, total_dist: float) -> str:
    dist_str = f"{total_dist:.1f} km" if total_dist else "—"
    return (
        f"<p class='muted'>총 <strong>{total}</strong>개 통합 활동 "
        f"| 총 거리 <strong>{dist_str}</strong></p>"
    )


# ── 활동 테이블 ──────────────────────────────────────────────────────────

_JS = """
<script>
function uaToggle(gid) {
  var sub = document.getElementById('sub-' + gid);
  var btn = document.getElementById('btn-' + gid);
  if (!sub) return;
  if (sub.style.display === 'none') {
    sub.style.display = '';
    btn.textContent = '▼';
  } else {
    sub.style.display = 'none';
    btn.textContent = '▶';
  }
}

function uaUngroup(actId, gid) {
  if (!confirm('이 활동을 그룹에서 분리하시겠습니까?')) return;
  fetch('/activities/ungroup', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({id: actId})
  }).then(function(r){ return r.json(); }).then(function(d){
    if (d.ok) { location.reload(); }
    else { alert('오류: ' + d.error); }
  });
}

function uaMergeChange() {
  var checked = document.querySelectorAll('.ua-chk:checked');
  var bar = document.getElementById('merge-bar');
  var cnt = document.getElementById('merge-cnt');
  if (checked.length >= 2) {
    bar.style.display = 'flex';
    cnt.textContent = checked.length + '개 선택됨';
  } else {
    bar.style.display = 'none';
  }
}

function uaMerge() {
  var checked = document.querySelectorAll('.ua-chk:checked');
  if (checked.length < 2) return;
  var ids = Array.from(checked).map(function(el){ return parseInt(el.value); });
  fetch('/activities/merge', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ids: ids})
  }).then(function(r){ return r.json(); }).then(function(d){
    if (d.ok) { location.reload(); }
    else { alert('오류: ' + d.error); }
  });
}

function uaMergeClear() {
  document.querySelectorAll('.ua-chk').forEach(function(el){ el.checked = false; });
  document.getElementById('merge-bar').style.display = 'none';
}
</script>
"""

_MERGE_BAR = (
    "<div id='merge-bar' style='"
    "display:none; position:fixed; bottom:1.5rem; left:50%; transform:translateX(-50%); "
    "background:#333; color:#fff; padding:0.6rem 1.2rem; border-radius:6px; "
    "gap:1rem; align-items:center; z-index:999; box-shadow:0 2px 8px rgba(0,0,0,0.4);'>"
    "<span id='merge-cnt'></span>"
    "<button onclick='uaMerge()' style='background:#0055b3; color:#fff; border:none; "
    "padding:0.3rem 0.8rem; border-radius:4px; cursor:pointer;'>묶기</button>"
    "<button onclick='uaMergeClear()' style='background:#555; color:#fff; border:none; "
    "padding:0.3rem 0.8rem; border-radius:4px; cursor:pointer;'>취소</button>"
    "</div>"
)


def _render_sub_row(act_id: int, src: str, row: dict, gid: str) -> str:
    """서브트리 소스 행 (작은 폰트)."""
    dist = _fmt_dist(row.get("distance_km"))
    dur = fmt_duration(row.get("duration_sec"))
    pace = _fmt_pace(row.get("avg_pace_sec_km"))
    avg_hr = row.get("avg_hr")
    deep_url = f"/activity/deep?id={act_id}"

    ungroup_btn = (
        f"<button onclick=\"uaUngroup({act_id}, '{html.escape(gid)}')\""
        " style='font-size:0.7rem; padding:1px 5px; cursor:pointer; "
        "border:1px solid #aaa; border-radius:3px; background:none;'>분리</button>"
    )

    return (
        "<tr style='font-size:0.78rem; color:var(--muted);'>"
        "<td></td>"  # 체크박스 열 (빈칸)
        "<td style='padding-left:1.5rem;'>"
        + _source_badge(src)
        + "</td>"
        f"<td>{html.escape(str(row.get('activity_type', '')))}</td>"
        f"<td>{html.escape(dist)}</td>"
        f"<td>{html.escape(dur)}</td>"
        f"<td>{html.escape(pace)}</td>"
        f"<td>{html.escape(str(avg_hr) if avg_hr else '—')}</td>"
        f"<td><a href='{html.escape(deep_url)}' style='font-size:0.78rem;'>심층</a></td>"
        f"<td>{ungroup_btn}</td>"
        "</tr>"
    )


def _render_activity_table(activities: list[UnifiedActivity]) -> str:
    if not activities:
        return "<p class='muted'>조건에 맞는 활동이 없습니다.</p>"

    headers = ["", "소스", "유형", "거리(km)", "시간", "페이스", "심박", "심층 분석", ""]
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    body_rows: list[str] = []

    for ua in activities:
        gid = html.escape(ua.effective_group_id)
        rep_id = ua.representative_id
        deep_url = f"/activity/deep?id={rep_id}"

        # 소스 배지들
        badges = " ".join(_source_badge(s) for s in ua.available_sources)

        # 확장 버튼
        if ua.can_expand:
            expand_btn = (
                f"<button id='btn-{gid}' onclick=\"uaToggle('{gid}')\" "
                "style='background:none; border:none; cursor:pointer; "
                "font-size:0.9rem; padding:0 4px;'>▶</button>"
            )
        else:
            expand_btn = ""

        # 단일 소스 활동의 경우 묶기 체크박스 표시
        if not ua.is_real_group:
            chk = (
                f"<input type='checkbox' class='ua-chk' value='{rep_id}' "
                "onchange='uaMergeChange()' style='cursor:pointer;'>"
            )
        else:
            chk = ""

        date_str = html.escape(ua.date)
        act_type = html.escape(str(ua.activity_type.value or ""))
        dist = html.escape(_fmt_dist(ua.distance_km.value))
        dur = html.escape(fmt_duration(ua.duration_sec.value))
        pace = html.escape(_fmt_pace(ua.avg_pace_sec_km.value))
        avg_hr = ua.avg_hr.value
        hr_str = html.escape(str(avg_hr) if avg_hr else "—")

        # 통합값 출처 이니셜 (다중 소스일 때만 표시)
        show_prov = len(ua.available_sources) > 1
        dist_tip = _provenance_tip(ua.distance_km.source) if show_prov else ""
        dur_tip = _provenance_tip(ua.duration_sec.source) if show_prov else ""
        pace_tip = _provenance_tip(ua.avg_pace_sec_km.source) if show_prov else ""
        hr_tip = _provenance_tip(ua.avg_hr.source) if show_prov else ""

        body_rows.append(
            f"<tr>"
            f"<td>{chk}</td>"
            f"<td>{expand_btn} {date_str} {badges}</td>"
            f"<td>{act_type}</td>"
            f"<td>{dist}{dist_tip}</td>"
            f"<td>{dur}{dur_tip}</td>"
            f"<td>{pace}{pace_tip}</td>"
            f"<td>{hr_str}{hr_tip}</td>"
            f"<td><a href='{html.escape(deep_url)}'>심층</a></td>"
            f"<td></td>"
            "</tr>"
        )

        # 서브트리 행 (처음에는 숨김)
        if ua.can_expand:
            sub_rows_html = ""
            for src in ua.available_sources:
                row = ua.source_rows[src]
                sub_rows_html += _render_sub_row(row["id"], src, row, ua.effective_group_id)

            body_rows.append(
                f"<tr id='sub-{gid}' style='display:none;'>"
                "<td colspan='9' style='padding:0;'>"
                "<table style='width:100%; border:none;'>"
                f"<tbody>{sub_rows_html}</tbody>"
                "</table>"
                "</td>"
                "</tr>"
            )

    return (
        f"<table><thead><tr>{head}</tr></thead>"
        f"<tbody>{''.join(body_rows)}</tbody></table>"
    )


def _render_pagination(page: int, total: int, base_qs: str) -> str:
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

    source = request.args.get("source", "").strip()
    act_type = request.args.get("type", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    if not date_from and not date_to:
        date_from = (date.today() - timedelta(days=90)).isoformat()

    try:
        with sqlite3.connect(str(dpath)) as conn:
            activities, total, stats = fetch_unified_activities(
                conn,
                source_filter=source,
                act_type_filter=act_type,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=_PAGE_SIZE,
            )
    except Exception as exc:
        import html as _html
        body = f"<div class='card'><p>조회 오류: {_html.escape(str(exc))}</p></div>"
        return html_page("활동 목록", body)

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
        _JS
        + _MERGE_BAR
        + sync_btn
        + _render_filter_form(source, act_type, date_from, date_to)
        + _render_summary(total, stats.get("total_dist_km", 0.0))
        + _render_activity_table(activities)
        + _render_pagination(page, total, base_qs)
    )
    return html_page("활동 목록", body)
