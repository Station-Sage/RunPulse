"""활동 상세 — 공통 헬퍼·포매터·독립 카드 함수."""
from __future__ import annotations

import html
import json

from .helpers import (
    db_path,
    fmt_duration,
    fmt_pace,
    make_table,
    metric_row,
    safe_str,
)


# ── 포매터 ──────────────────────────────────────────────────────────────

def fmt_int(v, unit: str = "") -> str:
    if v is None:
        return "—"
    return f"{int(round(float(v)))}{unit}"


def fmt_float1(v, unit: str = "") -> str:
    if v is None:
        return "—"
    return f"{float(v):.1f}{unit}"


def fmt_min_sec(sec) -> str:
    """초 → 분'초\" 형식."""
    if sec is None:
        return "—"
    sec = float(sec)
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}'{s:02d}\""


def fmt_val(val, fmt: str) -> str:
    """메트릭 값을 지정 포맷으로 변환."""
    v = float(val)
    if fmt == "pace":
        return f"{fmt_pace(val)}/km"
    if fmt == "f0":
        return f"{v:.0f}"
    if fmt == "f1%":
        return f"{v:.1f}%"
    if fmt == "f4":
        return f"{v:.4f}"
    if fmt == "f2":
        return f"{v:.2f}"
    return f"{v:.1f}"


# ── 메트릭 메타 정보 ────────────────────────────────────────────────────
# {key: (tooltip_desc, interpret_fn)}  interpret_fn(value) → (text, color)

METRIC_META: dict[str, tuple[str, object]] = {
    "FEARP":          ("환경 보정 페이스 — 기온·습도·경사·고도를 표준 조건(15°C, 50%, 평지, 0m)으로 환산한 등가 페이스.",
                       lambda v: ("표준 조건 기준 빠름" if v < 270 else "표준 조건 기준 보통" if v < 360 else "표준 조건 기준 느림", "var(--green)" if v < 270 else "var(--orange)" if v < 360 else "var(--red)")),
    "GAP":            ("경사 보정 페이스 (Grade-Adjusted Pace) — 오르막·내리막 효과를 제거한 평지 등가 페이스.", None),
    "NGP":            ("정규화 경사 페이스 (Normalized Graded Pace) — 강도 변화를 4차 멱승으로 가중 평균한 실효 페이스.", None),
    "RelativeEffort": ("상대 노력도 — 심박존별 시간에 Strava 가중치를 적용한 운동 강도 점수.",
                       lambda v: ("가벼운 운동" if v < 50 else "적당한 강도" if v < 100 else "높은 강도" if v < 200 else "매우 높은 강도", "var(--green)" if v < 50 else "var(--cyan)" if v < 100 else "var(--orange)" if v < 200 else "var(--red)")),
    "AerobicDecoupling": ("유산소 분리 — 후반 PA:HR 대비 전반 PA:HR 저하율. 낮을수록 심폐 효율 유지.",
                           lambda v: ("심폐 안정적" if v < 5 else "약간 분리" if v < 10 else "유산소 드리프트 큼", "var(--green)" if v < 5 else "var(--orange)" if v < 10 else "var(--red)")),
    "EF":             ("효율 계수 — 페이스÷심박수 비율. 높을수록 같은 심박에서 더 빠름.", None),
    "TRIMP":          ("훈련 충격 점수 — 심박존별 운동 시간에 지수 가중치를 적용한 훈련 부하 지수.",
                       lambda v: ("가벼운 부하" if v < 50 else "중간 부하" if v < 100 else "고부하" if v < 150 else "매우 고부하", "var(--green)" if v < 50 else "var(--cyan)" if v < 100 else "var(--orange)" if v < 150 else "var(--red)")),
    "WLEI":           ("날씨 가중 노력 지수 — TRIMP × 날씨 보정계수. TRIMP과 같으면 날씨 영향 없음, 높으면 날씨로 인한 추가 부담.",
                       lambda v: ("경미한 부하" if v < 80 else "보통 부하" if v < 200 else "고부하" if v < 350 else "매우 고부하", "var(--green)" if v < 80 else "var(--cyan)" if v < 200 else "var(--orange)" if v < 350 else "var(--red)")),
    "DI":             ("내구성 지수 — 90분+ 세션에서 후반 효율 / 전반 효율. 1.0 이상이면 끝까지 유지.",
                       lambda v: ("내구성 우수" if v >= 1.0 else "내구성 보통" if v >= 0.9 else "내구성 저하", "var(--green)" if v >= 1.0 else "var(--orange)" if v >= 0.9 else "var(--red)")),
    "LSI":            ("부하 스파이크 지수 — 오늘 TRIMP / 21일 평균. 1.5 초과 시 과부하.",
                       lambda v: ("정상 범위" if v < 1.3 else "주의 — 과부하 경향" if v < 1.5 else "위험 — 급격한 과부하", "var(--green)" if v < 1.3 else "var(--orange)" if v < 1.5 else "var(--red)")),
    "Monotony":       ("훈련 단조로움 — 7일 TRIMP 평균÷표준편차. 낮을수록 변화 있는 훈련.",
                       lambda v: ("다양한 훈련" if v < 1.5 else "약간 단조로움" if v < 2.0 else "매우 단조로운 훈련", "var(--green)" if v < 1.5 else "var(--orange)" if v < 2.0 else "var(--red)")),
    "ACWR":           ("급성/만성 부하 비율 — 7일÷28일 부하. 0.8~1.3이 안전 구간.",
                       lambda v: ("부하 부족" if v < 0.8 else "적절한 훈련량" if v <= 1.3 else "과부하 위험", "var(--cyan)" if v < 0.8 else "var(--green)" if v <= 1.3 else "var(--red)")),
    "ADTI":           ("유산소 분리 추세 — 8주 Decoupling 회귀 기울기. 음수면 개선.",
                       lambda v: ("유산소 개선 추세" if v < 0 else "유산소 정체" if v < 0.5 else "유산소 저하 추세", "var(--green)" if v < 0 else "var(--cyan)" if v < 0.5 else "var(--orange)")),
    "MarathonShape":  ("레이스 준비도 — 볼륨+최장거리+장거리빈도+일관성+페이스품질 5요소 (0~100%).",
                       lambda v: ("레이스 준비 미흡" if v < 40 else "기본 준비됨" if v < 70 else "레이스 준비 완료", "var(--red)" if v < 40 else "var(--orange)" if v < 70 else "var(--green)")),
    "RTTI":           ("러닝 내성 훈련 지수 — Garmin 권장 최대 부하 대비 실제 훈련 부하 비율.",
                       lambda v: ("훈련 여유 있음" if v < 80 else "권장 범위 내" if v <= 100 else "권장 한계 초과", "var(--cyan)" if v < 80 else "var(--green)" if v <= 100 else "var(--red)")),
    "TPDI":           ("실내/야외 퍼포먼스 격차 — 실외 vs 실내 평균 FEARP 차이.",
                       lambda v: ("격차 없음" if abs(v) < 5 else "약간 격차" if abs(v) < 15 else "큰 격차", "var(--green)" if abs(v) < 5 else "var(--orange)" if abs(v) < 15 else "var(--red)")),
}


# ── 메트릭 위젯 ─────────────────────────────────────────────────────────

def metric_tooltip_icon(key: str) -> str:
    """메트릭 설명 툴팁 아이콘 HTML."""
    meta = METRIC_META.get(key)
    if not meta:
        return ""
    desc = html.escape(meta[0])
    return f" <span style='cursor:help;color:var(--muted);font-size:0.75rem;' title='{desc}'>ⓘ</span>"


# AI 배치 해석 캐시 (활동 페이지 진입 시 한 번 생성)
_ai_metric_cache: dict[str, str] = {}


def set_ai_metric_cache(cache: dict[str, str]) -> None:
    """AI 메트릭 배치 해석 캐시 설정."""
    global _ai_metric_cache
    _ai_metric_cache = cache


def clear_ai_metric_cache() -> None:
    """AI 메트릭 캐시 초기화."""
    global _ai_metric_cache
    _ai_metric_cache = {}


def metric_interp_badge(key: str, value: float) -> str:
    """현재 수치 해설 뱃지 HTML — AI 캐시 우선, 규칙 기반 fallback."""
    # AI 배치 해석이 있으면 우선 사용
    ai_text = _ai_metric_cache.get(key)
    if ai_text:
        return (f" <span style='font-size:0.72rem;color:var(--cyan);margin-left:6px;'>"
                f"{ai_text}</span>")

    # 규칙 기반
    meta = METRIC_META.get(key)
    if not meta or meta[1] is None:
        return ""
    try:
        text, color = meta[1](value)
        return f" <span style='font-size:0.72rem;color:{color};margin-left:6px;'>{text}</span>"
    except Exception:
        return ""


def gauge_bar(value: float | None, max_val: float, color: str, label: str, unit: str = "") -> str:
    """수평 게이지 바 HTML (0 ~ max_val 스케일)."""
    if value is None:
        return (
            "<div style='margin-bottom:0.75rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;"
            f"margin-bottom:3px;'><span style='color:var(--muted);'>{label}</span>"
            "<span style='color:var(--muted);'>—</span></div>"
            "<div style='background:var(--row-border);border-radius:4px;height:8px;'></div>"
            "</div>"
        )
    pct = min(100.0, max(0.0, float(value) / max_val * 100))
    val_str = f"{float(value):.0f}{unit}"
    return (
        "<div style='margin-bottom:0.75rem;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;"
        f"margin-bottom:3px;'><span style='color:var(--muted);'>{label}</span>"
        f"<span style='font-weight:600;color:{color};'>{val_str}</span></div>"
        f"<div style='background:var(--row-border);border-radius:4px;height:8px;overflow:hidden;'>"
        f"<div style='height:100%;width:{pct:.1f}%;background:{color};border-radius:4px;"
        f"transition:width 0.5s;'></div></div>"
        "</div>"
    )


def rp_row(key: str, val, fmt: str) -> str:
    """RunPulse 메트릭 행 (라벨+툴팁 | 값+해석 뱃지)."""
    if val is None:
        return ""
    v = float(val)
    val_str = fmt_val(val, fmt)
    badge = metric_interp_badge(key, v)
    icon = metric_tooltip_icon(key)
    label_html = f"{key}{icon}"
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:0.4rem 0;border-bottom:1px solid var(--row-border);'>"
        f"<span style='font-size:0.85rem;color:var(--muted);'>{label_html}</span>"
        f"<span style='font-size:0.9rem;font-weight:600;'>{val_str}{badge}</span>"
        "</div>"
    )


def source_badge(source: str) -> str:
    """소스 배지 HTML (G/S/I/R/RP)."""
    colors = {"G": "#0055b3", "S": "#FC4C02", "I": "#00884e", "R": "#7b2d8b", "RP": "var(--cyan)"}
    color = colors.get(source, "var(--muted)")
    return f"<span style='font-size:0.65rem;color:{color};border:1px solid {color};border-radius:3px;padding:0 3px;margin-left:4px;'>{source}</span>"


def no_data_msg(title: str, msg: str = "데이터 수집 중입니다") -> str:
    """데이터 없음 안내 카드."""
    return f"<div class='card'><h2>{title}</h2><p class='muted' style='margin:0;'>{msg}</p></div>"


def group_header(title: str, subtitle: str = "") -> str:
    """그룹 섹션 헤더."""
    sub = f"<span style='font-size:0.75rem;color:var(--muted);margin-left:8px;'>{subtitle}</span>" if subtitle else ""
    return (
        f"<div style='margin:1.2rem 0 0.3rem;padding:0.3rem 0;border-bottom:1px solid var(--row-border);'>"
        f"<span style='font-size:0.9rem;font-weight:700;color:var(--cyan);'>{title}</span>{sub}</div>"
    )


# ── 독립 카드 ───────────────────────────────────────────────────────────

def render_activity_summary(act: dict) -> str:
    """활동 기본 정보 카드."""
    dist = act.get("distance_km")
    dist_str = f"{float(dist):.2f} km" if dist is not None else "—"
    return (
        "<div class='card'><h2>활동 요약</h2>"
        + metric_row("날짜", act.get("date"))
        + metric_row("유형", act.get("type"))
        + metric_row("거리", dist_str)
        + metric_row("시간", fmt_duration(act.get("duration_sec")))
        + metric_row("평균 페이스", safe_str(act.get("avg_pace")))
        + metric_row("평균 심박", fmt_int(act.get("avg_hr"), " bpm"))
        + metric_row("최대 심박", fmt_int(act.get("max_hr"), " bpm"))
        + metric_row("평균 케이던스", fmt_int(act.get("avg_cadence"), " spm"))
        + metric_row("고도 상승", fmt_int(act.get("elevation_gain"), " m"))
        + metric_row("칼로리", fmt_int(act.get("calories"), " kcal"))
        + "</div>"
    )


def render_activity_nav(prev_row: tuple | None, next_row: tuple | None) -> str:
    """이전/다음 활동 네비 바."""
    parts = []
    if prev_row:
        parts.append(f"<a href='/activity/deep?id={prev_row[0]}'>← {html.escape(str(prev_row[1])[:10])}</a>")
    else:
        parts.append("<span class='muted'>← (없음)</span>")
    parts.append("<a href='/activities'>목록으로</a>")
    if next_row:
        parts.append(f"<a href='/activity/deep?id={next_row[0]}'>{html.escape(str(next_row[1])[:10])} →</a>")
    else:
        parts.append("<span class='muted'>(없음) →</span>")
    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "margin:0.5rem 0;flex-wrap:wrap;gap:0.5rem;'>"
        + " ".join(parts) + "</div>"
    )


def render_horizontal_scroll(act: dict, metrics: dict) -> str:
    """핵심 메트릭 수평 스크롤 바."""
    dist = act.get("distance_km")
    dist_str = f"{float(dist):.2f} km" if dist is not None else "—"
    pace_str = act.get("avg_pace") or "—"
    items = [
        ("🏃", "거리", dist_str),
        ("⏱", "시간", fmt_duration(act.get("duration_sec"))),
        ("⚡", "페이스", f"{pace_str}/km" if pace_str != "—" else "—"),
        ("❤️", "심박수", fmt_int(act.get("avg_hr"), " bpm")),
        ("📈", "고도↑", fmt_int(act.get("elevation_gain"), " m")),
        ("🔥", "칼로리", fmt_int(act.get("calories"), " kcal")),
    ]
    fearp = metrics.get("FEARP")
    gap = metrics.get("GAP")
    if fearp is not None:
        items.append(("🌡", "FEARP", f"{fmt_pace(fearp)}/km"))
    if gap is not None:
        items.append(("⛰", "GAP", f"{fmt_pace(gap)}/km"))
    chips = "".join(
        f"<div style='display:inline-flex;flex-direction:column;align-items:center;"
        f"min-width:76px;padding:0.55rem 0.7rem;background:rgba(255,255,255,0.06);"
        f"border-radius:12px;margin:0 4px;'>"
        f"<span style='font-size:1.3rem;line-height:1;'>{icon}</span>"
        f"<span style='font-size:0.68rem;color:var(--muted);margin-top:3px;'>{lbl}</span>"
        f"<span style='font-size:0.88rem;font-weight:600;margin-top:2px;'>{v}</span></div>"
        for icon, lbl, v in items
    )
    return (
        "<div style='overflow-x:auto;white-space:nowrap;padding:0.5rem 0 0.8rem;"
        "-webkit-overflow-scrolling:touch;'>" + chips + "</div>"
    )


def render_classification_badge(act: dict) -> str:
    """활동 유형 자동 분류 뱃지."""
    duration = act.get("duration_sec") or 0
    avg_hr = act.get("avg_hr") or 0
    if duration >= 90 * 60:
        cls, icon, desc = "장거리런", "&#127959;", "90분+ 장거리 훈련"
    elif avg_hr >= 175:
        cls, icon, desc = "인터벌/경기", "&#9889;", "고강도 — 인터벌 또는 레이스 수준"
    elif avg_hr >= 160:
        cls, icon, desc = "템포런", "&#128293;", "유산소 역치 훈련"
    elif avg_hr and avg_hr < 135:
        cls, icon, desc = "회복런", "&#128564;", "가벼운 회복 조깅"
    elif avg_hr:
        cls, icon, desc = "유산소런", "&#127939;", "기본 유산소 훈련"
    else:
        return ""
    return (
        f"<div style='padding:0.3rem 0;'>"
        f"<span style='background:rgba(0,212,255,0.12);color:var(--cyan);"
        f"border-radius:16px;padding:0.28rem 0.8rem;font-size:0.8rem;'>"
        f"{icon} {cls} — {desc}</span></div>"
    )


def render_splits(splits: list) -> str:
    """페이스 스플릿 테이블 카드."""
    if not splits:
        return ""
    rows = [
        (
            f"{item.get('km')} (부분)" if item.get("partial") else item.get("km"),
            item.get("pace") or "—",
            item.get("avg_hr") or "—",
        )
        for item in splits
    ]
    return "<div class='card'><h2>페이스 스플릿 (km)</h2>" + make_table(["km", "페이스", "평균 심박"], rows) + "</div>"


# render_map_placeholder → views_activity_map.py 로 분리
