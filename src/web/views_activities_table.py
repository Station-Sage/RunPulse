"""활동 목록 뷰 — 활동 테이블 + 요약 + 편집 바 + JS.

views_activities.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html

from src.services.unified_activities import UnifiedActivity
from .helpers import fmt_duration
from .views_activities_helpers import (
    _fmt_dist,
    _fmt_pace,
    _label_badge,
    _make_tag_badges,
    _provenance_tip,
    _source_badge,
    _STRAVA_WORKOUT_TYPE,
    _type_icon,
)

_PAGE_SIZE = 20


# ── 통계 + 묶기 버튼 ─────────────────────────────────────────────────────

def _render_summary(total: int, total_dist: float) -> str:
    dist_str = f"{total_dist:.1f} km" if total_dist else "—"
    return (
        "<div style='display:flex; justify-content:space-between; align-items:center; "
        "margin-bottom:0.5rem; flex-wrap:wrap; gap:0.5rem;'>"
        f"<p class='muted' style='margin:0;'>총 <strong>{total}</strong>개 통합 활동 "
        f"| 총 거리 <strong>{dist_str}</strong></p>"
        "<div style='position:relative;'>"
        "<button onclick='uaGroupMenuToggle()' id='group-menu-btn' "
        "style='font-size:0.82rem; padding:0.25rem 0.7rem; cursor:pointer;'>"
        "동일 활동 묶기 ▾</button>"
        "<div id='group-menu' style='"
        "display:none; position:absolute; right:0; top:110%; "
        "background:#fff; border:1px solid #ccc; border-radius:4px; "
        "box-shadow:0 2px 8px rgba(0,0,0,0.15); z-index:100; min-width:140px;'>"
        "<button onclick='uaAutoGroup()' style='"
        "display:block; width:100%; text-align:left; padding:0.5rem 0.8rem; "
        "border:none; background:none; cursor:pointer; font-size:0.85rem;'>"
        "자동 묶기</button>"
        "<button onclick='uaEditModeOn()' style='"
        "display:block; width:100%; text-align:left; padding:0.5rem 0.8rem; "
        "border:none; background:none; cursor:pointer; font-size:0.85rem;'>"
        "직접 편집</button>"
        "</div>"
        "</div>"
        "</div>"
    )


# ── JS ───────────────────────────────────────────────────────────────────

_JS = """
<script>
var _editMode = false;

function uaGroupMenuToggle() {
  var m = document.getElementById('group-menu');
  m.style.display = m.style.display === 'none' ? 'block' : 'none';
}
document.addEventListener('click', function(e) {
  var btn = document.getElementById('group-menu-btn');
  var menu = document.getElementById('group-menu');
  if (btn && menu && !btn.contains(e.target) && !menu.contains(e.target)) {
    menu.style.display = 'none';
  }
});

function uaAutoGroup() {
  document.getElementById('group-menu').style.display = 'none';
  if (!confirm('모든 활동을 대상으로 동일 활동 자동 묶기를 실행합니까?\\n(±5분, ±3% 거리 조건)')) return;
  fetch('/activities/auto-group', {method: 'POST'})
    .then(function(r){ return r.json(); })
    .then(function(d){
      if (d.ok) {
        alert('완료: ' + d.groups_created + '개 그룹 생성, ' + d.activities_grouped + '개 활동 묶음');
        location.reload();
      } else { alert('오류: ' + d.error); }
    });
}

function uaEditModeOn() {
  document.getElementById('group-menu').style.display = 'none';
  _editMode = true;
  document.querySelectorAll('.ua-chk-wrap').forEach(function(el){ el.style.display = ''; });
  document.querySelectorAll('.ua-ungroup-btn').forEach(function(el){ el.style.display = ''; });
  document.getElementById('edit-bar').style.display = 'flex';
}

function uaEditModeOff() {
  _editMode = false;
  document.querySelectorAll('.ua-chk-wrap').forEach(function(el){
    el.style.display = 'none';
    var chk = el.querySelector('input');
    if (chk) chk.checked = false;
  });
  document.querySelectorAll('.ua-ungroup-btn').forEach(function(el){ el.style.display = 'none'; });
  document.getElementById('edit-bar').style.display = 'none';
  document.getElementById('merge-bar').style.display = 'none';
}

function uaToggle(gid) {
  var sub = document.getElementById('sub-' + gid);
  var btn = document.getElementById('btn-' + gid);
  if (!sub) return;
  var opening = sub.style.display === 'none';
  sub.style.display = opening ? '' : 'none';
  if (btn) {
    var ico = btn.querySelector('.expand-icon');
    if (ico) ico.textContent = opening ? '▼' : '▶';
    btn.style.background = opening ? 'rgba(0,85,179,0.08)' : '';
  }
}

function uaUngroup(actId) {
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
</script>
"""

_EDIT_BAR = (
    "<div id='edit-bar' style='"
    "display:none; position:fixed; top:0; left:0; right:0; "
    "background:#1a1a2e; color:#fff; padding:0.5rem 1rem; "
    "align-items:center; gap:1rem; z-index:1000; font-size:0.85rem;'>"
    "<span>직접 편집 모드</span>"
    "<span class='muted' style='color:#aaa; font-size:0.78rem;'>활동 선택 후 묶기 가능, 분리 버튼으로 그룹 해제</span>"
    "<button onclick='uaEditModeOff()' style='margin-left:auto; padding:0.25rem 0.8rem; "
    "background:#555; color:#fff; border:none; border-radius:4px; cursor:pointer;'>편집 종료</button>"
    "</div>"
)

_MERGE_BAR = (
    "<div id='merge-bar' style='"
    "display:none; position:fixed; bottom:1.5rem; left:50%; transform:translateX(-50%); "
    "background:#333; color:#fff; padding:0.6rem 1.2rem; border-radius:6px; "
    "gap:1rem; align-items:center; z-index:999; box-shadow:0 2px 8px rgba(0,0,0,0.4);'>"
    "<span id='merge-cnt'></span>"
    "<button onclick='uaMerge()' style='background:#0055b3; color:#fff; border:none; "
    "padding:0.3rem 0.8rem; border-radius:4px; cursor:pointer;'>묶기</button>"
    "</div>"
)


# ── 활동 테이블 ──────────────────────────────────────────────────────────

def _render_sub_row(act_id: int, src: str, row: dict, gid: str) -> str:
    """서브트리 소스 행."""
    dist = _fmt_dist(row.get("distance_km"))
    dur = fmt_duration(row.get("duration_sec"))
    pace = _fmt_pace(row.get("avg_pace_sec_km"))
    avg_hr = row.get("avg_hr")
    raw_name = row.get("name") or row.get("description") or ""
    name = html.escape(str(raw_name)) if raw_name else "—"
    label = row.get("workout_label")
    deep_url = f"/activity/deep?id={act_id}"

    ungroup_btn = (
        f"<button class='ua-ungroup-btn' onclick=\"uaUngroup({act_id})\" style='"
        "display:none; font-size:0.7rem; padding:1px 5px; cursor:pointer; "
        "border:1px solid #aaa; border-radius:3px; background:none; margin-left:4px;'>분리</button>"
    )

    _HIDE = {"uncategorized", "other", "default", "none", "-", ""}
    seen_sub: set[str] = set()
    badges_parts = []
    if label and label.lower().strip() not in _HIDE:
        seen_sub.add(label.lower().strip())
        badges_parts.append(_label_badge(label))
    event_type = row.get("event_type")
    if event_type and event_type.lower().strip() not in _HIDE and event_type.lower().strip() not in seen_sub:
        seen_sub.add(event_type.lower().strip())
        badges_parts.append(_label_badge(event_type))
    wt = row.get("workout_type")
    if wt and int(wt) in _STRAVA_WORKOUT_TYPE:
        disp, clr = _STRAVA_WORKOUT_TYPE[int(wt)]
        if disp.lower().strip() not in seen_sub and disp.lower().strip() not in _HIDE:
            badges_parts.append(
                f"<span style='background:{clr}; color:#fff; border-radius:3px; "
                f"padding:1px 6px; font-size:0.72rem; white-space:nowrap;'>{html.escape(disp)}</span>"
            )
    label_cell = " ".join(badges_parts)

    return (
        "<tr style='font-size:0.78rem; color:var(--muted);'>"
        "<td style='padding-left:1.5rem;'>"
        f"<a href='{html.escape(deep_url)}' style='font-size:0.78rem;'>{name}</a>"
        f"{ungroup_btn}</td>"
        f"<td></td>"
        f"<td>{html.escape(dist)}</td>"
        f"<td>{html.escape(dur)}</td>"
        f"<td>{html.escape(pace)}</td>"
        f"<td>{html.escape(str(avg_hr) if avg_hr else '—')}</td>"
        f"<td>{label_cell}</td>"
        f"<td>{_source_badge(src)}</td>"
        "</tr>"
    )


_ACTIVITY_TABLE_CSS = """
<style>
.act-table {
    border-collapse: separate; border-spacing: 0;
    border: 1px solid var(--card-border); border-radius: 8px;
    overflow: hidden; table-layout: auto; width: 100%;
}
.act-table th {
    background: var(--th-bg); border: none;
    border-bottom: 2px solid var(--card-border);
    padding: 0.4rem 0.5rem; font-size: 0.78rem; font-weight: 600;
    white-space: nowrap;
}
.act-table td {
    border: none; border-bottom: 1px solid var(--row-border);
    padding: 0.42rem 0.5rem; vertical-align: middle;
    white-space: nowrap;
}
.act-table tbody tr:last-child td { border-bottom: none; }
.act-table tbody tr:hover > td { background: var(--nav-hover); }
.act-table .col-name {
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    min-width: 100px; max-width: 1px; width: 99%;
}
@media (max-width: 640px) {
    .act-table { font-size: 0.8rem; }
    .act-table th, .act-table td { padding: 0.3rem 0.35rem; }
    .act-table .col-mob-hide { display: none; }
    .dt-tm { display: none; }
    .dt-yr { display: none; }
    .col-date { min-width: 42px !important; }
}
@media (max-width: 440px) {
    .act-table .col-pace-hide { display: none; }
}
</style>
"""


def _render_activity_table(
    activities: list[UnifiedActivity],
    sort_url_base: str = "",
    cur_sort: str = "date",
    cur_dir: str = "desc",
) -> str:
    if not activities:
        return "<p class='muted'>조건에 맞는 활동이 없습니다.</p>"

    col_defs = [
        ("활동명",  "col-name",               "",                                    None),
        ("날짜",    "col-date",               "min-width:58px;",                     "date"),
        ("거리",    "col-dist",               "min-width:52px; text-align:right;",   "distance"),
        ("시간",    "col-dur",                "min-width:58px; text-align:right;",   "duration"),
        ("페이스",  "col-pace col-pace-hide", "min-width:50px; text-align:right;",   "pace"),
        ("심박",    "col-hr col-mob-hide",    "min-width:42px; text-align:right;",   "hr"),
        ("태그",    "col-tag col-mob-hide",   "min-width:76px;",                     None),
        ("소스",    "col-src",                "min-width:58px; text-align:center;",  None),
    ]

    def _sort_th(label: str, cls: str, sty: str, skey: str | None) -> str:
        if not sort_url_base or skey is None:
            return f"<th class='{cls}' style='{sty}'>{html.escape(label)}</th>"
        if cur_sort == skey:
            next_dir = "asc" if cur_dir == "desc" else "desc"
            indicator = " ▼" if cur_dir == "desc" else " ▲"
        else:
            next_dir = "desc"
            indicator = ""
        url = f"{sort_url_base}&sort={skey}&dir={next_dir}"
        return (
            f"<th class='{cls}' style='{sty} cursor:pointer; user-select:none; white-space:nowrap;'>"
            f"<a href='{html.escape(url)}' style='text-decoration:none; color:inherit;'>"
            f"{html.escape(label)}{indicator}</a></th>"
        )

    head = "".join(_sort_th(h, cls, sty, sk) for h, cls, sty, sk in col_defs)
    body_rows: list[str] = []

    for ua in activities:
        gid = html.escape(ua.effective_group_id)
        rep_id = ua.representative_id
        deep_url = f"/activity/deep?id={rep_id}"

        src_icons = " ".join(_source_badge(s) for s in ua.available_sources)
        if ua.can_expand:
            badges = (
                f"<span id='btn-{gid}' onclick=\"uaToggle('{gid}')\" "
                "style='cursor:pointer; display:inline-flex; gap:3px; align-items:center; "
                "border-radius:4px; padding:1px 3px;' title='클릭하여 소스별 상세 보기'>"
                + src_icons
                + f"<span class='expand-icon' style='font-size:0.6rem; color:var(--muted); "
                  f"margin-left:1px;'>▶</span>"
                + "</span>"
            )
        else:
            badges = src_icons

        chk_wrap = (
            f"<span class='ua-chk-wrap' style='display:none; margin-right:4px;'>"
            f"<input type='checkbox' class='ua-chk' value='{rep_id}' "
            f"onchange='uaMergeChange()' style='cursor:pointer;'>"
            f"</span>"
        )

        name_raw = ua.description.value or ""
        name_display = html.escape(str(name_raw)) if name_raw else html.escape(str(ua.activity_type.value or "—"))
        type_ico = _type_icon(ua.activity_type.value)
        name_cell = (
            f"{chk_wrap}"
            f"{type_ico}"
            f"<a href='{html.escape(deep_url)}' style='font-weight:500;'>{name_display}</a>"
        )

        _d = ua.date
        _yr  = html.escape(_d[:5])
        _md  = html.escape(_d[5:10])
        _tm  = html.escape(_d[10:])
        date_str = (
            f"<span class='dt-yr'>{_yr}</span>"
            f"<span class='dt-md'>{_md}</span>"
            f"<span class='dt-tm'>{_tm}</span>"
        )
        dist = html.escape(_fmt_dist(ua.distance_km.value))
        dur = html.escape(fmt_duration(ua.duration_sec.value))
        pace = html.escape(_fmt_pace(ua.avg_pace_sec_km.value))
        avg_hr = ua.avg_hr.value
        hr_str = html.escape(str(avg_hr) if avg_hr else "—")

        show_prov = len(ua.available_sources) > 1
        dist_tip = _provenance_tip(ua.distance_km.source) if show_prov else ""
        dur_tip = _provenance_tip(ua.duration_sec.source) if show_prov else ""
        pace_tip = _provenance_tip(ua.avg_pace_sec_km.source) if show_prov else ""
        hr_tip = _provenance_tip(ua.avg_hr.source) if show_prov else ""

        label_cell = _make_tag_badges(ua)

        body_rows.append(
            f"<tr>"
            f"<td class='col-name'>{name_cell}</td>"
            f"<td class='col-date' style='font-size:0.82rem;'>{date_str}</td>"
            f"<td style='text-align:right;'>{dist}{dist_tip}</td>"
            f"<td style='text-align:right;'>{dur}{dur_tip}</td>"
            f"<td style='text-align:right;'>{pace}{pace_tip}</td>"
            f"<td class='col-mob-hide' style='text-align:right;'>{hr_str}{hr_tip}</td>"
            f"<td class='col-mob-hide'>{label_cell}</td>"
            f"<td style='text-align:center;'>{badges}</td>"
            "</tr>"
        )

        if ua.can_expand:
            sub_rows_html = ""
            for src in ua.available_sources:
                row = ua.source_rows[src]
                sub_rows_html += _render_sub_row(row["id"], src, row, ua.effective_group_id)

            body_rows.append(
                f"<tr id='sub-{gid}' style='display:none;'>"
                "<td colspan='8' style='padding:0; background:var(--card-bg);'>"
                "<table style='width:100%; border-collapse:collapse;'>"
                f"<tbody>{sub_rows_html}</tbody>"
                "</table>"
                "</td>"
                "</tr>"
            )

    return (
        _ACTIVITY_TABLE_CSS
        + f"<table class='act-table'><thead><tr>{head}</tr></thead>"
        + f"<tbody>{''.join(body_rows)}</tbody></table>"
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
