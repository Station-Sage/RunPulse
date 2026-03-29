"""활동 목록 뷰 — 포맷 헬퍼 + 아이콘/배지.

views_activities.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

import html

from src.utils.pace import seconds_to_pace
from src.services.unified_activities import SOURCE_COLORS, UnifiedActivity


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
        "<svg width='18' height='18' viewBox='0 0 24 24' title='Garmin' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<path d='M12 2L4 6v6c0 5.25 3.5 10.15 8 11.35C16.5 22.15 20 17.25 20 12V6L12 2z' "
        "fill='#0055b3'/>"
        "<text x='12' y='16' text-anchor='middle' fill='white' "
        "font-size='9' font-family='Arial' font-weight='bold'>G</text>"
        "</svg>"
    ),
    "strava": (
        "<svg width='18' height='18' viewBox='0 0 24 24' title='Strava' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<circle cx='12' cy='12' r='11' fill='#FC4C02'/>"
        "<text x='12' y='17' text-anchor='middle' fill='white' "
        "font-size='13' font-family='Arial' font-weight='bold'>S</text>"
        "</svg>"
    ),
    "intervals": (
        "<svg width='18' height='18' viewBox='0 0 24 24' title='intervals.icu' "
        "style='vertical-align:middle;' xmlns='http://www.w3.org/2000/svg'>"
        "<circle cx='12' cy='12' r='11' fill='#00884e'/>"
        "<text x='12' y='17' text-anchor='middle' fill='white' "
        "font-size='13' font-family='Arial' font-weight='bold'>i</text>"
        "</svg>"
    ),
    "runalyze": (
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
    display = label
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


def _make_tag_badges(ua: UnifiedActivity) -> str:
    """RP 자동 분류 태그 + 소스 태그 통합 뱃지."""
    from src.metrics.workout_classifier import TAG_COLORS, TAG_LABELS

    badges = []
    seen: set[str] = set()

    _HIDE_TAGS = {"uncategorized", "other", "default", "none", "-", ""}
    _SYNONYMS: dict[str, str] = {
        "race": "레이스", "레이스": "race",
        "long run": "장거리", "장거리": "long run", "longrun": "장거리",
        "easy run": "이지런", "이지런": "easy run", "easyrun": "이지런",
        "interval": "인터벌", "인터벌": "interval",
        "tempo": "템포", "템포": "tempo",
        "recovery": "회복", "회복": "recovery",
        "threshold": "역치", "역치": "threshold",
    }

    def _add(label: str) -> None:
        if not label:
            return
        normalized = label.lower().strip()
        if normalized in seen or normalized in _HIDE_TAGS:
            return
        seen.add(normalized)
        syn = _SYNONYMS.get(normalized)
        if syn:
            seen.add(syn.lower())
        badges.append(_label_badge(label))

    # 0. RP 자동 분류 태그 (최우선)
    rp_type = ua.source_rows.get("_rp_workout_type")
    if rp_type:
        wtype = rp_type.get("type", "")
        label_ko = TAG_LABELS.get(wtype, wtype)
        color = TAG_COLORS.get(wtype, "#888")
        effect = rp_type.get("effect", "")
        if label_ko:
            badges.append(
                f"<span style='background:{color}; color:#fff; border-radius:3px; "
                f"padding:1px 6px; font-size:0.72rem; white-space:nowrap;' "
                f"title='RP 분류: {html.escape(effect)}'>{html.escape(label_ko)}</span>"
            )
            seen.add(label_ko.lower())
            seen.add(wtype.lower())
            syn = _SYNONYMS.get(wtype.lower())
            if syn:
                seen.add(syn.lower())
            syn2 = _SYNONYMS.get(label_ko.lower())
            if syn2:
                seen.add(syn2.lower())

    # 1. workout_label (Garmin trainingEffectLabel / Intervals tags)
    _add(ua.workout_label.value or "")

    # 2. event_type (Garmin eventType / Intervals category)
    _add(ua.event_type.value or "")

    # 3. Strava workout_type 정수 → 레이블 변환
    strava_row = ua.source_rows.get("strava", {})
    wt = strava_row.get("workout_type")
    if wt and int(wt) in _STRAVA_WORKOUT_TYPE:
        disp, clr = _STRAVA_WORKOUT_TYPE[int(wt)]
        if disp.lower().strip() not in seen and disp.lower().strip() not in _HIDE_TAGS:
            seen.add(disp.lower().strip())
            badges.append(
                f"<span style='background:{clr}; color:#fff; border-radius:3px; "
                f"padding:1px 6px; font-size:0.72rem; white-space:nowrap;' "
                f"title='Strava workout_type={wt}'>{html.escape(disp)}</span>"
            )

    return " ".join(badges)
