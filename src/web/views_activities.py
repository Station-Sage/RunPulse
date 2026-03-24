"""활동 목록 뷰 — Flask Blueprint.

/activities
  - 날짜 범위·소스·유형 필터
  - 페이지네이션 (20개/페이지)
  - 통합 활동 행 (Garmin 우선 병합)
  - 서브트리 확장/축소 (▶/▼ 토글)
  - 동일 활동 묶기: 자동 묶기 / 직접 편집 모드 (체크박스 + 분리)
  - 컬럼: 활동명 | 날짜/시간 | 거리 | 시간 | 페이스 | 심박 | 태그 | 소스
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
from .helpers import bottom_nav, db_path, fmt_duration, html_page

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


# 활동 유형 → 이모지 아이콘
_ACT_TYPE_ICONS: dict[str, str] = {
    "running":           "🏃",
    "run":               "🏃",
    "treadmill":         "🏃",
    "treadmill_running": "🏃",
    "track_running":     "🏃",
    "trail_running":     "🏃",
    "virtualrun":        "🏃",
    "swimming":          "🏊",
    "open_water_swimming": "🏊",
    "strength":          "🏋️",
    "hiit":              "🏋️",
    "highintensityintervaltraining": "🏋️",
    "workout":           "🏋️",
    "elliptical":        "🏋️",
    "yoga":              "🧘",
    "hiking":            "🥾",
    "walking":           "🚶",
}

_ACT_TYPE_FILTERS = [
    ("",         "전체"),
    ("running",  "🏃 달리기"),
    ("swimming", "🏊 수영"),
    ("strength", "🏋️ 헬스"),
    ("hiking",   "🥾 하이킹"),
]


def _type_icon(activity_type: str | None) -> str:
    """활동 유형 이모지 아이콘 span."""
    icon = _ACT_TYPE_ICONS.get((activity_type or "").lower(), "🏅")
    return (
        f"<span style='font-size:1em; margin-right:4px; "
        f"vertical-align:middle;' title='{html.escape(activity_type or '')}'>"
        f"{icon}</span>"
    )


_SOURCE_ICONS: dict[str, str] = {
    "garmin": (
        # Garmin: 파란 방패 모양 SVG
        "<svg width='18' height='18' viewBox='0 0 24 24' title='Garmin' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<path d='M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6L12 2z' "
        "fill='#0055b3'/>"
        "<text x='12' y='16' text-anchor='middle' fill='white' "
        "font-size='9' font-family='Arial' font-weight='bold'>G</text>"
        "</svg>"
    ),
    "strava": (
        # Strava: 주황 S
        "<svg width='18' height='18' viewBox='0 0 24 24' title='Strava' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<circle cx='12' cy='12' r='11' fill='#FC4C02'/>"
        "<text x='12' y='17' text-anchor='middle' fill='white' "
        "font-size='13' font-family='Arial' font-weight='bold'>S</text>"
        "</svg>"
    ),
    "intervals": (
        # intervals.icu: 초록 i
        "<svg width='18' height='18' viewBox='0 0 24 24' title='intervals.icu' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<circle cx='12' cy='12' r='11' fill='#00884e'/>"
        "<text x='12' y='17' text-anchor='middle' fill='white' "
        "font-size='13' font-family='Arial' font-weight='bold'>i</text>"
        "</svg>"
    ),
    "runalyze": (
        # Runalyze: 보라 R
        "<svg width='18' height='18' viewBox='0 0 24 24' title='Runalyze' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<circle cx='12' cy='12' r='11' fill='#7b2d8b'/>"
        "<text x='12' y='17' text-anchor='middle' fill='white' "
        "font-size='11' font-family='Arial' font-weight='bold'>R</text>"
        "</svg>"
    ),
}


def _source_badge(source: str) -> str:
    icon = _SOURCE_ICONS.get(source)
    if icon:
        return f"<span title='{html.escape(source)}'>{icon}</span>"
    # 알 수 없는 소스: 텍스트 폴백
    color = SOURCE_COLORS.get(source, "#888")
    return (
        f"<span style='background:{color}; color:#fff; border-radius:50%; "
        f"width:18px; height:18px; display:inline-flex; align-items:center; "
        f"justify-content:center; font-size:0.65rem; font-weight:bold; "
        f"vertical-align:middle;' title='{html.escape(source)}'>"
        f"{html.escape(source[0].upper())}</span>"
    )


def _provenance_tip(source: str | None) -> str:
    if not source:
        return ""
    icon = _SOURCE_ICONS.get(source)
    if icon:
        return (
            f"<span style='vertical-align:super; font-size:0.7em; margin-left:2px;' "
            f"title='{html.escape(source)} 기준'>{icon}</span>"
        )
    color = SOURCE_COLORS.get(source, "#888")
    return (
        f"<sup style='color:{color}; font-size:0.65rem; font-weight:bold; "
        f"margin-left:2px;' title='{html.escape(source)} 기준'>"
        f"{html.escape(source[0].upper())}</sup>"
    )


# Garmin trainingEffectLabel + intervals.icu tags + event_type → 표시명 + 색상
_LABEL_MAP: list[tuple[str, str, str]] = [
    # (키워드(소문자 포함), 표시명, 색상)
    ("a_race",             "A레이스",     "#c0392b"),
    ("b_race",             "B레이스",     "#e74c3c"),
    ("c_race",             "C레이스",     "#e67e22"),
    ("vo2max",             "VO2 Max",    "#2980b9"),
    ("vo2",                "VO2 Max",    "#2980b9"),
    ("lactate_threshold",  "역치",        "#8e44ad"),
    ("threshold",          "역치",        "#8e44ad"),
    ("tempo",              "템포",        "#c0392b"),
    ("anaerobic",          "무산소",      "#6c3483"),
    ("aerobic_base",       "유산소 기초", "#27ae60"),
    ("base",               "기초",        "#1e8449"),
    ("recovery",           "회복",        "#7f8c8d"),
    ("리커버리",            "회복",        "#7f8c8d"),
    ("interval",           "인터벌",      "#d35400"),
    ("longrun",            "장거리",      "#e67e22"),
    ("long_run",           "장거리",      "#e67e22"),
    ("long",               "장거리",      "#e67e22"),
    ("easyrun",            "이지런",      "#27ae60"),
    ("easy_run",           "이지런",      "#27ae60"),
    ("easy",               "이지런",      "#27ae60"),
    ("race",               "레이스",      "#e74c3c"),
    ("overreaching",       "과부하",      "#c0392b"),
]

# Strava workout_type 정수 → (표시명, 색상)
_STRAVA_WORKOUT_TYPE: dict[int, tuple[str, str]] = {
    1: ("레이스",  "#e74c3c"),
    2: ("장거리",  "#e67e22"),
    3: ("훈련",    "#d35400"),
}


def _label_badge(label: str) -> str:
    """단일 label 문자열 → 뱃지 HTML."""
    normalized = label.lower().strip()
    display = label  # fallback: 원본값
    color = "#888"
    for key, disp, clr in _LABEL_MAP:
        if key in normalized:
            display = disp
            color = clr
            break
    return (
        f"<span style='background:{color}; color:#fff; border-radius:3px; "
        f"padding:1px 6px; font-size:0.72rem; white-space:nowrap;' "
        f"title='{html.escape(label)}'>"
        f"{html.escape(display)}</span>"
    )


def _make_tag_badges(ua) -> str:
    """workout_label + event_type + Strava workout_type → 뱃지 HTML 모음.

    중복 의미 뱃지(예: workout_label="race" + event_type="race")는 하나만 표시.
    """
    badges = []
    seen: set[str] = set()

    def _add(label: str) -> None:
        if not label:
            return
        normalized = label.lower().strip()
        if normalized in seen:
            return
        seen.add(normalized)
        badges.append(_label_badge(label))

    # 1. workout_label (Garmin trainingEffectLabel / Intervals tags)
    _add(ua.workout_label.value or "")

    # 2. event_type (Garmin eventType / Intervals category)
    _add(ua.event_type.value or "")

    # 3. Strava workout_type 정수 → 레이블 변환
    strava_row = ua.source_rows.get("strava", {})
    wt = strava_row.get("workout_type")
    if wt and int(wt) in _STRAVA_WORKOUT_TYPE:
        disp, clr = _STRAVA_WORKOUT_TYPE[int(wt)]
        # 이미 같은 의미 뱃지가 없을 때만 추가
        if disp not in {b for b in seen}:
            badges.append(
                f"<span style='background:{clr}; color:#fff; border-radius:3px; "
                f"padding:1px 6px; font-size:0.72rem; white-space:nowrap;' "
                f"title='Strava workout_type={wt}'>{html.escape(disp)}</span>"
            )

    return " ".join(badges)


# ── 기간 빠른 선택 JS ─────────────────────────────────────────────────────

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

    # 운동 유형 pill 버튼
    type_pills = "".join(
        f"<button type='button' onclick=\"setTypeFilter('{val}')\" "
        f"style='{_pill_base}{_pill_active if act_type == val else ''}'>{label}</button>"
        for val, label in _ACT_TYPE_FILTERS
    )

    # 기간 빠른 선택 pill 버튼
    date_pills = "".join(
        f"<button type='button' data-preset='{key}' onclick=\"setDatePreset('{key}')\" "
        f"style='{_pill_base}'>{label}</button>"
        for key, label in _DATE_PRESETS
    )

    # 거리/시간/페이스 프리셋 (JS로 여러 필드 세팅 후 submit)
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

    # active preset 강조 JS + 커스텀 필터 JS
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
        # dist/pace 프리셋 active 표시
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
        # 검색 + 소스 + 날짜 범위
        + "<div style='display:flex; gap:0.7rem; align-items:flex-end; flex-wrap:wrap; margin-bottom:0.55rem;'>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem; flex:1; min-width:120px;'>활동명 검색"
        + f"<input type='search' name='q' value='{html.escape(q)}' placeholder='검색어…' style='{_inp} width:100%; box-sizing:border-box;'></label>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem;'>소스"
        + f"<select name='source' style='font-size:0.85rem;'>{source_opts}</select></label>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem;'>시작일"
        + f"<input type='date' id='filter-from' name='from' value='{html.escape(date_from)}' style='font-size:0.85rem;'></label>"
        + "<label style='display:flex; flex-direction:column; font-size:0.82rem;'>종료일"
        + f"<input type='date' id='filter-to' name='to' value='{html.escape(date_to)}' style='font-size:0.85rem;'></label>"
        + "<button type='submit' style='height:2rem; font-size:0.85rem; padding:0 0.8rem;'>조회</button>"
        + "<a href='/activities' style='line-height:2rem; font-size:0.82rem; color:var(--muted);'>초기화</a>"
        + "</div>"
        # 거리/시간/페이스 범위 필터
        + "<details style='margin-bottom:0.45rem;'>"
        + "<summary style='font-size:0.8rem; color:var(--muted); cursor:pointer; user-select:none; list-style:none; display:inline-flex; align-items:center; gap:4px;'>"
        + ("▼ " if any([min_dist, max_dist, min_pace_raw, max_pace_raw, min_dur_raw, max_dur_raw]) else "▶ ")
        + "범위 필터</summary>"
        + "<div style='display:flex; gap:0.6rem; flex-wrap:wrap; align-items:flex-end; padding:0.5rem 0 0.3rem;'>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최소 거리(km)<input id='f-min-dist' type='number' name='min_dist' min='0' step='0.1' value='{html.escape(min_dist_v)}' style='{_inp} width:70px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최대 거리(km)<input id='f-max-dist' type='number' name='max_dist' min='0' step='0.1' value='{html.escape(max_dist_v)}' style='{_inp} width:70px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최소 페이스(M:SS)<input id='f-min-pace' type='text' name='min_pace' placeholder='5:00' value='{html.escape(min_pace_raw)}' style='{_inp} width:60px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최대 페이스(M:SS)<input id='f-max-pace' type='text' name='max_pace' placeholder='4:30' value='{html.escape(max_pace_raw)}' style='{_inp} width:60px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최소 시간(분)<input type='number' name='min_dur' min='0' value='{html.escape(min_dur_raw)}' style='{_inp} width:60px;'></label>"
        + f"<label style='display:flex; flex-direction:column; font-size:0.78rem;'>최대 시간(분)<input type='number' name='max_dur' min='0' value='{html.escape(max_dur_raw)}' style='{_inp} width:60px;'></label>"
        + "</div>"
        + "</details>"
        # 운동 유형 pills
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.35rem;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>유형</span>"
        + type_pills
        + "</div>"
        # 기간 pills
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.35rem;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>기간</span>"
        + date_pills
        + "</div>"
        # 거리 프리셋 pills
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap; margin-bottom:0.35rem;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>거리</span>"
        + dist_preset_pills
        + "</div>"
        # 페이스 프리셋 pills (러닝에만 의미있음)
        + "<div style='display:flex; gap:0.35rem; flex-wrap:wrap;'>"
        + f"<span style='font-size:0.78rem; color:var(--muted); line-height:1.8rem; margin-right:2px;'>페이스</span>"
        + pace_preset_pills
        + "</div>"
        + "</form>"
        + "</div>"
    )


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
    name = html.escape(str(row.get("description") or "—"))
    label = row.get("workout_label")
    deep_url = f"/activity/deep?id={act_id}"

    ungroup_btn = (
        f"<button class='ua-ungroup-btn' onclick=\"uaUngroup({act_id})\" style='"
        "display:none; font-size:0.7rem; padding:1px 5px; cursor:pointer; "
        "border:1px solid #aaa; border-radius:3px; background:none; margin-left:4px;'>분리</button>"
    )

    badges_parts = []
    if label:
        badges_parts.append(_label_badge(label))
    event_type = row.get("event_type")
    if event_type and event_type.lower() != (label or "").lower():
        badges_parts.append(_label_badge(event_type))
    wt = row.get("workout_type")
    if wt and int(wt) in _STRAVA_WORKOUT_TYPE:
        disp, clr = _STRAVA_WORKOUT_TYPE[int(wt)]
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
        f"<td></td>"  # 날짜 (빈칸)
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
/* 활동명: 남은 공간 모두 차지, 긴 텍스트 말줄임 */
.act-table .col-name {
    white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
    min-width: 100px; max-width: 1px; width: 99%;
}
/* 날짜 점진적 축약 */
.dt-yr { }           /* 연도 "2026-" */
.dt-md { }           /* 월일 "03-08" */
.dt-tm { }           /* 시간 " 15:16" */
/* 640px 이하: 시간 숨김, 태그·심박 컬럼 숨김 */
@media (max-width: 640px) {
    .act-table { font-size: 0.8rem; }
    .act-table th, .act-table td { padding: 0.3rem 0.35rem; }
    .act-table .col-mob-hide { display: none; }
    .dt-tm { display: none; }
}
/* 440px 이하: 연도도 숨김, 페이스 숨김 */
@media (max-width: 440px) {
    .act-table .col-pace-hide { display: none; }
    .dt-yr { display: none; }
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

    # 정렬 가능한 컬럼: (헤더명, css_class, style, sort_key or None)
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
        # 같은 컬럼 클릭 시 방향 반전
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

        # 소스 배지 + 확장 토글 (그룹화된 활동)
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

        # 체크박스 (항상 렌더링하되 편집 모드 아닐 때 숨김)
        chk_wrap = (
            f"<span class='ua-chk-wrap' style='display:none; margin-right:4px;'>"
            f"<input type='checkbox' class='ua-chk' value='{rep_id}' "
            f"onchange='uaMergeChange()' style='cursor:pointer;'>"
            f"</span>"
        )

        # 활동명
        name_raw = ua.description.value or ""
        name_display = html.escape(str(name_raw)) if name_raw else html.escape(str(ua.activity_type.value or "—"))
        type_ico = _type_icon(ua.activity_type.value)
        name_cell = (
            f"{chk_wrap}"
            f"{type_ico}"
            f"<a href='{html.escape(deep_url)}' style='font-weight:500;'>{name_display}</a>"
        )

        # 날짜 점진적 축약: "2026-03-08 15:16" → 3 span으로 분리
        _d = ua.date  # "YYYY-MM-DD HH:MM"
        _yr  = html.escape(_d[:5])    # "2026-"
        _md  = html.escape(_d[5:10])  # "03-08"
        _tm  = html.escape(_d[10:])   # " 15:16"
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

        # 출처 이니셜 (다중 소스)
        show_prov = len(ua.available_sources) > 1
        dist_tip = _provenance_tip(ua.distance_km.source) if show_prov else ""
        dur_tip = _provenance_tip(ua.duration_sec.source) if show_prov else ""
        pace_tip = _provenance_tip(ua.avg_pace_sec_km.source) if show_prov else ""
        hr_tip = _provenance_tip(ua.avg_hr.source) if show_prov else ""

        # 태그 (workout_label + event_type + Strava workout_type 통합)
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

        # 서브트리 행 (처음에는 숨김)
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


# ── 라우트 ────────────────────────────────────────────────────────────────

@activities_bp.get("/activities")
def activities_list():
    """활동 목록 페이지."""
    dpath = db_path()
    if not dpath.exists():
        body = "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return html_page("활동 목록", body, active_tab="activities")

    source = request.args.get("source", "").strip()
    act_type = request.args.get("type", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    q = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "date").strip()
    sort_dir = request.args.get("dir", "desc").strip()
    if sort_by not in ("date", "distance", "duration", "pace", "hr"):
        sort_by = "date"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    def _parse_float(key: str) -> float | None:
        v = request.args.get(key, "").strip()
        try:
            return float(v) if v else None
        except ValueError:
            return None

    def _parse_int(key: str) -> int | None:
        v = request.args.get(key, "").strip()
        try:
            return int(v) if v else None
        except ValueError:
            return None

    min_dist = _parse_float("min_dist")
    max_dist = _parse_float("max_dist")
    min_pace_raw = request.args.get("min_pace", "").strip()  # "M:SS" 형식
    max_pace_raw = request.args.get("max_pace", "").strip()
    min_dur_raw = request.args.get("min_dur", "").strip()    # 분 단위
    max_dur_raw = request.args.get("max_dur", "").strip()

    def _pace_to_sec(v: str) -> int | None:
        """'M:SS' → 초/km."""
        if not v:
            return None
        parts = v.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else None
        except (ValueError, IndexError):
            return None

    min_pace = _pace_to_sec(min_pace_raw)
    max_pace = _pace_to_sec(max_pace_raw)
    min_dur = int(float(min_dur_raw) * 60) if min_dur_raw else None
    max_dur = int(float(max_dur_raw) * 60) if max_dur_raw else None

    # 파라미터 자체가 없을 때(첫 방문)만 기본 90일 적용
    # "전체" 버튼은 from=&to= 로 제출하므로 파라미터는 존재함 → 기본값 미적용
    _has_date_param = "from" in request.args or "to" in request.args
    if not _has_date_param:
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
                sort_by=sort_by,
                sort_dir=sort_dir,
                q=q,
                min_dist=min_dist,
                max_dist=max_dist,
                min_pace=min_pace,
                max_pace=max_pace,
                min_dur=min_dur,
                max_dur=max_dur,
            )
    except Exception as exc:
        import html as _html
        body = f"<div class='card'><p>조회 오류: {_html.escape(str(exc))}</p></div>"
        return html_page("활동 목록", body, active_tab="activities")

    # base_qs: 필터 파라미터 (페이지네이션, 정렬 링크에 공통 사용)
    qs_parts = []
    if source:
        qs_parts.append(f"source={html.escape(source)}")
    if act_type:
        qs_parts.append(f"type={html.escape(act_type)}")
    # from/to는 명시적으로 제출된 경우 항상 포함 (빈 값 포함) — 정렬 시 날짜 유지
    if _has_date_param or date_from:
        qs_parts.append(f"from={html.escape(date_from)}")
    if _has_date_param or date_to:
        qs_parts.append(f"to={html.escape(date_to)}")
    if q:
        qs_parts.append(f"q={html.escape(q)}")
    if min_dist is not None:
        qs_parts.append(f"min_dist={min_dist}")
    if max_dist is not None:
        qs_parts.append(f"max_dist={max_dist}")
    if min_pace_raw:
        qs_parts.append(f"min_pace={html.escape(min_pace_raw)}")
    if max_pace_raw:
        qs_parts.append(f"max_pace={html.escape(max_pace_raw)}")
    if min_dur_raw:
        qs_parts.append(f"min_dur={html.escape(min_dur_raw)}")
    if max_dur_raw:
        qs_parts.append(f"max_dur={html.escape(max_dur_raw)}")
    base_qs = "&".join(qs_parts)
    # 정렬 링크용 베이스 (sort/dir 없이 모든 필터 포함)
    sort_base = "/activities?" + base_qs

    from .sync_ui import sync_card_html
    from .helpers import last_sync_info, connected_services
    from src.utils.sync_state import get_all_states
    sync_btn = sync_card_html(
        last_sync=last_sync_info(["garmin", "strava", "intervals", "runalyze"]),
        sync_states=get_all_states(),
        connected=connected_services(),
    )

    body = (
        _JS
        + _EDIT_BAR
        + _MERGE_BAR
        + sync_btn
        + _render_filter_form(source, act_type, date_from, date_to, q,
                             min_dist, max_dist, min_pace_raw, max_pace_raw, min_dur_raw, max_dur_raw)
        + _render_summary(total, stats.get("total_dist_km", 0.0))
        + _render_activity_table(activities, sort_url_base=sort_base, cur_sort=sort_by, cur_dir=sort_dir)
        + _render_pagination(page, total, base_qs)
    )
    return html_page("활동 목록", body, active_tab="activities")
