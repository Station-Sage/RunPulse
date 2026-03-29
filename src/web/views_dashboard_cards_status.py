"""대시보드 상태 카드 — 오늘의 상태 스트립 + 주간 요약."""
from __future__ import annotations

from datetime import date as _date

from .helpers import (
    METRIC_DESCRIPTIONS,
    fmt_duration,
    no_data_card,
    svg_semicircle_gauge,
    tooltip,
)

_UTRS_COLORS = [(0, "#e53935"), (40, "#fb8c00"), (60, "#43a047"), (80, "#00acc1")]
_CIRS_COLORS = [(0, "#43a047"), (20, "#fb8c00"), (50, "#ef6c00"), (75, "#e53935")]


def _mini_gauge(label: str, value: float | None, max_val: float,
                colors: list, grade: str = "") -> str:
    """60px 미니 반원 게이지 + 툴팁."""
    desc = METRIC_DESCRIPTIONS.get(label, "")
    tip_label = tooltip(label, desc) if desc else label
    if value is None:
        return (f"<div style='text-align:center;min-width:80px;opacity:0.4;'>"
                f"<div style='font-size:0.7rem;color:var(--muted);'>{tip_label}</div>"
                f"<div style='font-size:1.1rem;font-weight:700;'>—</div></div>")
    gauge = svg_semicircle_gauge(value, max_val, grade, colors, width=70)
    return (f"<div style='text-align:center;min-width:80px;'>"
            f"<div style='font-size:0.7rem;color:var(--muted);margin-bottom:2px;'>{tip_label}</div>"
            f"{gauge}</div>")


def _mini_icon_val(icon: str, label: str, value, unit: str = "", color: str = "var(--cyan)") -> str:
    """아이콘 + 값 미니 표시."""
    val_str = f"{value}" if value is not None else "—"
    opacity = "1" if value is not None else "0.4"
    return (f"<div style='text-align:center;min-width:60px;opacity:{opacity};'>"
            f"<div style='font-size:1.1rem;'>{icon}</div>"
            f"<div style='font-size:0.95rem;font-weight:700;color:{color};'>{val_str}{unit}</div>"
            f"<div style='font-size:0.65rem;color:var(--muted);'>{label}</div></div>")


def render_daily_status_strip(utrs_val: float | None, utrs_json: dict,
                              cirs_val: float | None, cirs_json: dict,
                              acwr: float | None, rtti: float | None,
                              wellness: dict,
                              metric_date: str | None = None) -> str:
    """섹션 1: 오늘의 상태 한 줄 스트립."""
    utrs_grade = {"rest": "휴식", "light": "경량", "moderate": "보통", "optimal": "최적"}.get(
        (utrs_json or {}).get("grade", ""), "")
    cirs_grade = {"safe": "안전", "caution": "주의", "warning": "경고", "danger": "위험"}.get(
        (cirs_json or {}).get("grade", ""), "")

    if acwr is None:
        acwr_clr = "var(--muted)"
    elif acwr > 1.5:
        acwr_clr = "var(--red)"
    elif acwr > 1.3:
        acwr_clr = "var(--orange)"
    else:
        acwr_clr = "var(--green)"
    acwr_str = f"{acwr:.2f}" if acwr is not None else "—"

    bb = wellness.get("body_battery")
    sleep = wellness.get("sleep_score")
    hrv = wellness.get("hrv")

    acwr_tip = tooltip("ACWR", METRIC_DESCRIPTIONS.get("ACWR", ""))
    parts = [
        _mini_gauge("UTRS", utrs_val, 100, _UTRS_COLORS, utrs_grade),
        _mini_gauge("CIRS", cirs_val, 100, _CIRS_COLORS, cirs_grade),
        (f"<div style='text-align:center;min-width:70px;'>"
         f"<div style='font-size:0.7rem;color:var(--muted);margin-bottom:2px;'>{acwr_tip}</div>"
         f"<div style='font-size:1.3rem;font-weight:700;color:{acwr_clr};'>{acwr_str}</div></div>"),
        _mini_gauge("RTTI", rtti, 100, [(0, "#e53935"), (40, "#fb8c00"), (70, "#43a047")]),
        _mini_icon_val("&#128267;", "BB", bb, "", "var(--orange)"),
        _mini_icon_val("&#128164;", "수면", sleep, "", "var(--cyan)"),
        _mini_icon_val("&#128147;", "HRV", f"{hrv:.0f}" if hrv else None, "", "var(--green)"),
    ]

    date_label = "오늘의 상태"
    if metric_date and metric_date != _date.today().isoformat():
        date_label = f"최근 상태 ({metric_date})"
    return (
        "<div class='card' style='padding:0.6rem 0.8rem;'>"
        f"<div style='font-size:0.8rem;color:var(--muted);margin-bottom:0.4rem;'>{date_label}</div>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.6rem;align-items:flex-end;justify-content:space-around;'>"
        + "".join(parts) +
        "</div></div>"
    )


def render_weekly_summary(weekly: dict, weekly_target_km: float = 40.0) -> str:
    """섹션 3: 주간 거리/시간 진행률 + TIDS 도넛."""
    if not weekly or weekly.get("count", 0) == 0:
        return no_data_card("이번 주 훈련 요약", "이번 주 활동이 없습니다")

    dist = weekly["distance_km"]
    dur = weekly["duration_sec"]
    count = weekly["count"]
    pct = min(100, round(dist / weekly_target_km * 100)) if weekly_target_km > 0 else 0

    bar_clr = "var(--green)" if pct >= 80 else ("var(--orange)" if pct >= 50 else "var(--cyan)")
    progress = (
        f"<div style='margin-bottom:0.6rem;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px;'>"
        f"<span>{dist:.1f} km / {weekly_target_km:.0f} km</span>"
        f"<span style='color:{bar_clr};font-weight:600;'>{pct}%</span></div>"
        f"<div style='background:rgba(255,255,255,0.1);border-radius:4px;height:8px;'>"
        f"<div style='width:{pct}%;background:{bar_clr};border-radius:4px;height:8px;"
        f"transition:width 0.5s;'></div></div></div>"
    )

    stats = (
        f"<div style='display:flex;gap:1rem;font-size:0.8rem;color:var(--secondary);'>"
        f"<span>{count}회</span><span>{fmt_duration(dur)}</span></div>"
    )

    z12 = weekly.get("tids_z12") or 0
    z3 = weekly.get("tids_z3") or 0
    z45 = weekly.get("tids_z45") or 0
    total = z12 + z3 + z45
    tids_html = ""
    if total > 0:
        p12 = round(z12 / total * 100)
        p3 = round(z3 / total * 100)
        p45 = 100 - p12 - p3
        tids_html = (
            f"<div style='display:flex;align-items:center;gap:0.8rem;margin-top:0.6rem;'>"
            f"<div style='width:60px;height:60px;border-radius:50%;"
            f"background:conic-gradient(#00d4ff 0% {p12}%, #ffaa00 {p12}% {p12 + p3}%, #ff4444 {p12 + p3}% 100%);"
            f"position:relative;'>"
            f"<div style='position:absolute;inset:12px;border-radius:50%;background:var(--bg);'></div></div>"
            f"<div style='font-size:0.75rem;line-height:1.5;'>"
            f"<div><span style='color:#00d4ff;'>&#9632;</span> Z1-2 {p12}%</div>"
            f"<div><span style='color:#ffaa00;'>&#9632;</span> Z3 {p3}%</div>"
            f"<div><span style='color:#ff4444;'>&#9632;</span> Z4-5 {p45}%</div></div></div>"
        )

    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.5rem;'>이번 주 훈련 요약</h2>"
        + progress + stats + tids_html +
        "</div>"
    )
