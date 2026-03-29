"""대시보드 리스크 카드 — ACWR/LSI/Monotony/TSB + UTRS/CIRS 상세."""
from __future__ import annotations

from .helpers import METRIC_DESCRIPTIONS, no_data_card, tooltip


def render_risk_pills_v2(risk_data: dict, trends_7d: dict,
                         config: dict | None = None, conn=None,
                         ai_override: str | None = None) -> str:
    """섹션 6: 위험지표 pills + AI 요약."""
    if not risk_data:
        return ""

    def _trend_arrow(vals: list) -> str:
        clean = [v for v in vals if v is not None]
        if len(clean) < 2:
            return ""
        diff = clean[-1] - clean[0]
        if abs(diff) < 0.01:
            return "<span style='color:var(--muted);font-size:0.7rem;'>&#8594;</span>"
        if diff > 0:
            return "<span style='color:var(--red);font-size:0.7rem;'>&#8593;</span>"
        return "<span style='color:var(--green);font-size:0.7rem;'>&#8595;</span>"

    def _pill(label: str, val: float | None, lo: float, hi: float,
              fmt: str = ".2f", invert: bool = False, trend_key: str = "",
              desc_key: str = "") -> str:
        trend = _trend_arrow(trends_7d.get(trend_key, [])) if trend_key else ""
        desc = METRIC_DESCRIPTIONS.get(desc_key or trend_key, "")
        if val is not None:
            if not invert:
                status = "위험" if val > hi else "주의" if val > lo else "적정"
            else:
                status = "위험" if val < lo else "주의" if val < hi else "적정"
            range_text = f" (적정: {lo}~{hi})"
            desc = f"{desc}{range_text} | 현재: {status}" if desc else f"적정 범위: {lo}~{hi} | 현재: {status}"
        tip_label = tooltip(label, desc) if desc else label

        if val is None:
            return (f"<span style='background:rgba(255,255,255,0.08);color:var(--muted);"
                    f"border-radius:16px;padding:0.25rem 0.7rem;font-size:0.78rem;"
                    f"white-space:nowrap;'>{tip_label} — {trend}</span>")
        bad = val > hi if not invert else val < lo
        warn = (lo < val <= hi) if not invert else (lo <= val < hi)
        if bad:
            bg, clr = "rgba(255,68,68,0.18)", "var(--red)"
        elif warn:
            bg, clr = "rgba(255,170,0,0.18)", "var(--orange)"
        else:
            bg, clr = "rgba(0,255,136,0.15)", "var(--green)"
        return (f"<span style='background:{bg};color:{clr};border-radius:16px;"
                f"padding:0.25rem 0.7rem;font-size:0.78rem;white-space:nowrap;'>"
                f"{tip_label} {val:{fmt}} {trend}</span>")

    tsb = risk_data.get("tsb")
    strain = risk_data.get("strain")

    return (
        "<div class='card' style='padding:0.6rem 1rem;'>"
        "<div style='font-size:0.8rem;color:var(--muted);margin-bottom:0.3rem;'>리스크 상세</div>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.4rem;align-items:center;'>"
        + _pill("ACWR", risk_data.get("acwr"), 1.3, 1.5, ".2f", trend_key="ACWR")
        + _pill("LSI", risk_data.get("lsi"), 1.0, 1.5, ".1f", trend_key="LSI")
        + _pill("단조로움", risk_data.get("monotony"), 1.5, 2.0, ".1f", trend_key="Monotony")
        + _pill("Strain", strain, 200, 400, ".0f", trend_key="Strain")
        + _pill("TSB", tsb, -20, -10, ".0f", invert=True, trend_key="TSB")
        + "</div>"
        + _risk_ai_summary(risk_data, config, conn, ai_override=ai_override)
        + "</div>"
    )


def _risk_ai_summary(risk_data: dict, config, conn, ai_override: str | None = None) -> str:
    """리스크 AI 한 줄 요약."""
    msg = ai_override
    if not msg:
        return ""
    return (f"<div style='margin-top:0.4rem;font-size:0.78rem;color:var(--secondary);'>"
            f"💡 {msg}</div>")


def _render_cirs_banner(cirs: float) -> str:
    """CIRS 경고 배너 (>=75 위험, >=50 주의)."""
    if cirs >= 75:
        return (
            "<div style='background:rgba(229,57,53,0.15);color:#ff4444;"
            "border-left:4px solid #ff4444;padding:0.7rem 1rem;"
            "border-radius:6px;margin-bottom:1rem;'>"
            f"&#9888; <strong>부상 위험 (CIRS {cirs:.0f})</strong> — 훈련 강도를 즉시 낮추세요."
            "</div>"
        )
    if cirs >= 50:
        return (
            "<div style='background:rgba(251,140,0,0.15);color:#ffaa00;"
            "border-left:4px solid #ffaa00;padding:0.7rem 1rem;"
            "border-radius:6px;margin-bottom:1rem;'>"
            f"&#9889; <strong>부상 주의 (CIRS {cirs:.0f})</strong> — 회복·부하 관리가 필요합니다."
            "</div>"
        )
    return ""


def _render_utrs_factors(utrs_json: dict) -> str:
    """UTRS 하위 요인 progress bar 표시."""
    labels = {"sleep": "수면점수", "hrv": "HRV 지수", "tsb_norm": "TSB", "rhr": "안정심박", "consistency": "수면일관성"}
    rows = []
    for key, label in labels.items():
        val = utrs_json.get(key)
        pct = max(0, min(100, val)) if val is not None else 0
        val_str = f"{val:.0f}" if val is not None else "—"
        opacity = "1" if val is not None else "0.4"
        clr = "#00ff88" if pct >= 60 else ("#ffaa00" if pct >= 40 else "#ff4444")
        rows.append(
            f"<div style='opacity:{opacity};margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.76rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<span style='font-weight:600;'>{val_str}</span></div>"
            f"<div style='background:rgba(255,255,255,0.1);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{clr};border-radius:3px;height:5px;'></div></div></div>"
        )
    return "<div style='margin-top:0.7rem;'>" + "".join(rows) + "</div>"


def _render_cirs_breakdown(cirs_json: dict) -> str:
    """CIRS 구성요소 breakdown (progress bar + 상태 뱃지)."""
    factors = [("acwr_risk", "ACWR 과부하", "×0.4"), ("mono_risk", "훈련 단조로움", "×0.2"),
               ("spike_risk", "부하 급증", "×0.3")]
    if cirs_json.get("has_asym_data"):
        factors.append(("asym_risk", "비대칭", "×0.1"))
    rows = []
    for key, label, weight in factors:
        val = float(cirs_json.get(key) or 0)
        pct = max(0, min(100, val))
        if val < 30:
            sc, bc = "var(--green)", "#00ff88"
            status = "안전"
        elif val < 60:
            sc, bc = "var(--orange)", "#ffaa00"
            status = "주의"
        else:
            sc, bc = "var(--red)", "#ff4444"
            status = "위험"
        rows.append(
            f"<div style='margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.76rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label} <span style='color:var(--muted);font-size:0.68rem;'>{weight}</span></span>"
            f"<span style='color:{sc};font-weight:600;'>{status} {val:.0f}</span></div>"
            f"<div style='background:rgba(255,255,255,0.1);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{bc};border-radius:3px;height:5px;'></div></div></div>"
        )
    return "<div style='margin-top:0.6rem;'>" + "".join(rows) + "</div>"


def _render_risk_pills(risk_data: dict) -> str:
    """ACWR / LSI / Monotony / TSB 상태 pill 행."""
    if not risk_data:
        return ""

    def _pill(label: str, val: float | None, lo: float, hi: float, fmt: str = ".2f", invert: bool = False) -> str:
        if val is None:
            return f"<span style='background:rgba(255,255,255,0.08);color:var(--muted);border-radius:16px;padding:0.25rem 0.7rem;font-size:0.78rem;white-space:nowrap;'>{label} —</span>"
        bad = val > hi if not invert else val < lo
        warn = (lo < val <= hi) if not invert else (lo <= val < hi)
        if bad:
            bg, clr = "rgba(255,68,68,0.18)", "var(--red)"
        elif warn:
            bg, clr = "rgba(255,170,0,0.18)", "var(--orange)"
        else:
            bg, clr = "rgba(0,255,136,0.15)", "var(--green)"
        return (f"<span style='background:{bg};color:{clr};border-radius:16px;"
                f"padding:0.25rem 0.7rem;font-size:0.78rem;white-space:nowrap;'>"
                f"{label} {val:{fmt}}</span>")

    tsb = risk_data.get("tsb")
    tsb_pill = _pill("TSB", tsb, -20, -10, ".0f", invert=True)
    return (
        "<div class='card' style='padding:0.6rem 1rem;'>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.4rem;align-items:center;'>"
        "<span style='font-size:0.78rem;color:var(--muted);margin-right:0.2rem;'>위험지표</span>"
        + _pill("ACWR", risk_data.get("acwr"), 1.3, 1.5, ".2f")
        + _pill("LSI", risk_data.get("lsi"), 1.0, 1.5, ".1f")
        + _pill("단조로움", risk_data.get("monotony"), 1.5, 2.0, ".1f")
        + tsb_pill
        + "</div></div>"
    )
