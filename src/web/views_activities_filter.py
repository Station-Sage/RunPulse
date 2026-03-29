"""활동 목록 뷰 — 필터 폼 + 날짜 프리셋 JS.

views_activities.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html

from .views_activities_helpers import _ACT_TYPE_FILTERS


_DATE_PRESET_JS = """
<script>
function _isoDate(d) {
  return d.toISOString().slice(0, 10);
}
function _today() { return new Date(); }

var _datePresets = (function() {
  var t = _today();
  var y = t.getFullYear(), m = t.getMonth(), d = t.getDate();
  var dow = t.getDay(); // 0=일
  var monday = new Date(t); monday.setDate(d - (dow === 0 ? 6 : dow - 1));

  function daysAgo(n) { var r = new Date(t); r.setDate(d - n); return r; }
  function monthsAgo(n) { var r = new Date(t); r.setMonth(m - n); return r; }

  return {
    'week':   [_isoDate(monday), _isoDate(t)],
    'month':  [y + '-' + String(m+1).padStart(2,'0') + '-01', _isoDate(t)],
    '3m':     [_isoDate(monthsAgo(3)), _isoDate(t)],
    '6m':     [_isoDate(monthsAgo(6)), _isoDate(t)],
    'year':   [y + '-01-01', _isoDate(t)],
    '1y':     [_isoDate(monthsAgo(12)), _isoDate(t)],
    'all':    ['', ''],
  };
})();

function setDatePreset(key) {
  var p = _datePresets[key];
  document.getElementById('filter-from').value = p[0];
  document.getElementById('filter-to').value = p[1];
  document.getElementById('filter-form').submit();
}

function _detectActivePreset(from, to) {
  if (!from && !to) return 'all';
  for (var key in _datePresets) {
    var p = _datePresets[key];
    if (p[0] === from && (p[1] === to || (!p[1] && !to))) return key;
  }
  return null;
}
</script>
"""

_DATE_PRESETS = [
    ("week", "이번 주"),
    ("month", "이번 달"),
    ("3m", "최근 3개월"),
    ("6m", "최근 6개월"),
    ("year", "올해"),
    ("1y", "최근 1년"),
    ("all", "전체"),
]


def _render_filter_form(
    source: str,
    act_type: str,
    date_from: str,
    date_to: str,
    q: str = "",
    min_dist: float | None = None,
    max_dist: float | None = None,
    min_pace_raw: str = "",
    max_pace_raw: str = "",
    min_dur_raw: str = "",
    max_dur_raw: str = "",
) -> str:
    _SOURCES = ["garmin", "strava", "intervals", "runalyze"]
    source_opts = "<option value=''>전체 소스</option>" + "".join(
        f"<option value='{s}'{' selected' if source == s else ''}>{s}</option>"
        for s in _SOURCES
    )

    _pill_base = (
        "cursor:pointer; border:1px solid #ccc; border-radius:12px; "
        "padding:0.2rem 0.75rem; font-size:0.8rem; background:none; "
        "transition:background 0.15s, color 0.15s;"
    )
    _pill_active = "background:#0055b3; color:#fff; border-color:#0055b3;"

    type_pills = "".join(
        f"<button type='button' onclick=\"setTypeFilter('{val}')\" "
        f"style='{_pill_base}{_pill_active if act_type == val else ''}'>{label}</button>"
        for val, label in _ACT_TYPE_FILTERS
    )

    date_pills = "".join(
        f"<button type='button' data-preset='{key}' onclick=\"setDatePreset('{key}')\" "
        f"style='{_pill_base}'>{label}</button>"
        for key, label in _DATE_PRESETS
    )

    _DIST_PRESETS = [
        ("단거리 (≤5km)",   "max_dist=5"),
        ("5~10km",          "min_dist=5&max_dist=10"),
        ("하프+ (≥21km)",   "min_dist=21"),
        ("풀마+ (≥42km)",   "min_dist=42"),
    ]
    _PACE_PRESETS = [
        ("빠름 (≤4:30)",  "max_pace=4%3A30"),
        ("5분대",          "min_pace=4%3A30&max_pace=6%3A00"),
        ("여유 (≥6:00)",  "min_pace=6%3A00"),
    ]

    dist_preset_pills = "".join(
        f"<button type='button' data-dist-preset='{html.escape(qs)}' "
        f"onclick=\"setDistPreset('{html.escape(qs)}')\" "
        f"style='{_pill_base}'>{label}</button>"
        for label, qs in _DIST_PRESETS
    )
    pace_preset_pills = "".join(
        f"<button type='button' data-pace-preset='{html.escape(qs)}' "
        f"onclick=\"setPacePreset('{html.escape(qs)}')\" "
        f"style='{_pill_base}'>{label}</button>"
        for label, qs in _PACE_PRESETS
    )

    min_dist_v = str(min_dist) if min_dist is not None else ""
    max_dist_v = str(max_dist) if max_dist is not None else ""

    filter_js = (
        "<script>"
        "function setTypeFilter(val){"
        "  document.getElementById('type-hidden').value=val;"
        "  document.getElementById('filter-form').submit();}"
        "function setDistPreset(qs){"
        "  var params=new URLSearchParams(qs);"
        "  document.getElementById('f-min-dist').value=params.get('min_dist')||'';"
        "  document.getElementById('f-max-dist').value=params.get('max_dist')||'';"
        "  document.getElementById('filter-form').submit();}"
        "function setPacePreset(qs){"
        "  var params=new URLSearchParams(decodeURIComponent(qs));"
        "  document.getElementById('f-min-pace').value=params.get('min_pace')||'';"
        "  document.getElementById('f-max-pace').value=params.get('max_pace')||'';"
        "  document.getElementById('filter-form').submit();}"
        f"(function(){{"
        f"  var active=_detectActivePreset('{date_from}','{date_to}');"
        "  if(active){"
        "    var btn=document.querySelector('[data-preset=\"'+active+'\"]');"
        f"    if(btn){{btn.style.cssText+=';{_pill_active}';}}}}"
        f"  var dPreset='{html.escape(f'max_dist={max_dist_v}' if max_dist and not min_dist else (f'min_dist={min_dist_v}&max_dist={max_dist_v}' if min_dist and max_dist else (f'min_dist={min_dist_v}' if min_dist else '')))}'; "
        "  if(dPreset){var db=document.querySelector('[data-dist-preset=\"'+dPreset+'\"]');if(db)db.style.cssText+=';background:#0055b3;color:#fff;border-color:#0055b3;';}"
        "})();"
        "</script>"
    )

    _inp = "padding:0.25rem 0.4rem; border-radius:4px; border:1px solid #ccc; font-size:0.82rem; background:var(--card-bg); color:var(--fg);"

    return (
        _DATE_PRESET_JS
        + filter_js
        + "<div class='card' style='padding:0.8rem 1rem;'>"
        + "<form id='filter-form' method='get' action='/activities'>"
        + f"<input type='hidden' id='type-hidden' name='type' value='{html.escape(act_type)}'>"
        + "<div style='display:flex; gap:0.5rem; align-items:center; flex-wrap:wrap;'>"
        + f"<input type='search' name='q' value='{html.escape(q)}' placeholder='활동 검색…' "
        + f"style='{_inp} flex:1; min-width:140px; box-sizing:border-box;'>"
        + "<button type='submit' style='height:2rem; font-size:0.85rem; padding:0 0.8rem;'>조회</button>"
        + "<a href='/activities' style='font-size:0.82rem; color:var(--muted);'>초기화</a>"
        + "</div>"
        + "<details style='margin-top:0.5rem;'>"
        + "<summary style='font-size:0.8rem; color:var(--muted); cursor:pointer; list-style:none;'>"
        + "🔍 상세 필터</summary>"
        + "<div style='padding-top:0.5rem;'>"
        + "<div style='display:flex; gap:0.7rem; align-items:flex-end; flex-wrap:wrap; margin-bottom:0.55rem;'>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem;'>소스"
        + f"<select name='source' style='font-size:0.85rem;'>{source_opts}</select></label>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem;'>시작일"
        + f"<input type='date' id='filter-from' name='from' value='{html.escape(date_from)}' style='font-size:0.85rem;'></label>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem;'>종료일"
        + f"<input type='date' id='filter-to' name='to' value='{html.escape(date_to)}' style='font-size:0.85rem;'></label>"
        + "</div>"
        + "<div style='display:flex; gap:0.6rem; flex-wrap:wrap; align-items:flex-end; margin-bottom:0.5rem;'>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최소 거리(km)<input id='f-min-dist' type='number' name='min_dist' min='0' step='0.1' value='{html.escape(min_dist_v)}' style='{_inp} width:70px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최대 거리(km)<input id='f-max-dist' type='number' name='max_dist' min='0' step='0.1' value='{html.escape(max_dist_v)}' style='{_inp} width:70px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최소 페이스(M:SS)<input id='f-min-pace' type='text' name='min_pace' placeholder='5:00' value='{html.escape(min_pace_raw)}' style='{_inp} width:60px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최대 페이스(M:SS)<input id='f-max-pace' type='text' name='max_pace' placeholder='4:30' value='{html.escape(max_pace_raw)}' style='{_inp} width:60px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최소 시간(분)<input type='number' name='min_dur' min='0' value='{html.escape(min_dur_raw)}' style='{_inp} width:60px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최대 시간(분)<input type='number' name='max_dur' min='0' value='{html.escape(max_dur_raw)}' style='{_inp} width:60px;'></label>"
        + "</div>"
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.35rem;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>유형</span>"
        + type_pills
        + "</div>"
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.35rem;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>기간</span>"
        + date_pills
        + "</div>"
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.35rem;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>거리</span>"
        + dist_preset_pills
        + "</div>"
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>페이스</span>"
        + pace_preset_pills
        + "</div>"
        + "</div>"
        + "</details>"
        + "</form>"
        + "</div>"
    )
