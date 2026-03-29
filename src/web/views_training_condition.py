"""훈련탭 — 컨디션 + AI추천 통합 카드 렌더러.

S5: render_condition_ai_card
"""
from __future__ import annotations

from src.web.views_training_shared import _TYPE_STYLE, _esc


def render_condition_ai_card(
    adj: dict | None,
    utrs_val: float | None,
    cirs_val: float | None,
    cirs_json: dict,
    workouts: list[dict],
    config: dict | None = None,
    conn=None,
    ai_override: str | None = None,
) -> str:
    """컨디션 스냅샷 + AI 훈련 추천 통합 카드.

    메트릭 배지 행(UTRS/CIRS/BB/수면/HRV/TSB) + 조정 정보(조정 시) + AI 추천 텍스트.
    utrs_val과 cirs_val이 모두 None이고 adj도 없으면 빈 문자열 반환.
    """
    # ── 메트릭 배지 ──────────────────────────────────────────────────────
    wellness = (adj or {}).get("wellness", {})
    tsb = (adj or {}).get("tsb")

    def _badge(icon: str, label: str, color: str) -> str:
        return (
            f"<span style='display:inline-flex;align-items:center;gap:4px;"
            f"background:rgba(255,255,255,0.07);border-radius:20px;"
            f"padding:4px 10px;font-size:0.8rem;'>"
            f"{icon} <span style='color:{color};font-weight:600;'>{label}</span>"
            f"</span>"
        )

    badges: list[str] = []

    if utrs_val is not None:
        c = "#00ff88" if utrs_val >= 70 else "#ffaa00" if utrs_val >= 40 else "#ff4444"
        badges.append(_badge("🎯", f"UTRS {utrs_val:.0f}", c))

    if cirs_val is not None:
        c = "#ff4444" if cirs_val >= 70 else "#ffaa00" if cirs_val >= 40 else "#00ff88"
        badges.append(_badge("⚠️", f"CIRS {cirs_val:.0f}", c))

    bb = wellness.get("body_battery")
    if bb is not None:
        c = "#00ff88" if bb >= 50 else "#ffaa00" if bb >= 30 else "#ff4444"
        badges.append(_badge("⚡", f"BB {bb}", c))

    ss = wellness.get("sleep_score")
    if ss is not None:
        c = "#00ff88" if ss >= 60 else "#ffaa00" if ss >= 40 else "#ff4444"
        badges.append(_badge("😴", f"수면 {ss:.0f}", c))

    hrv = wellness.get("hrv_value")
    if hrv is not None:
        badges.append(_badge("💓", f"HRV {hrv:.0f}", "var(--secondary)"))

    if tsb is not None:
        c = "#00ff88" if tsb > 0 else "#ffaa00" if tsb > -15 else "#ff4444"
        badges.append(_badge("📊", f"TSB {tsb:+.1f}", c))

    badges_html = (
        "<div style='display:flex;gap:6px;flex-wrap:wrap;margin-bottom:14px;'>"
        + "".join(badges)
        + "</div>"
    ) if badges else ""

    # ── 상단 상태 색상 결정 ───────────────────────────────────────────────
    if cirs_val is not None and cirs_val >= 70:
        border_color, status_icon = "#ff4444", "⚠️"
    elif utrs_val is not None and utrs_val >= 70:
        border_color, status_icon = "#00ff88", "✅"
    elif utrs_val is not None and utrs_val < 40:
        border_color, status_icon = "#ff4444", "😴"
    else:
        border_color, status_icon = "#ffaa00", "📊"

    # ── 컨디션 조정 섹션 ─────────────────────────────────────────────────
    adj_html = ""
    if adj and adj.get("adjusted"):
        orig_label = _TYPE_STYLE.get(adj.get("original_type", ""), ("", adj.get("original_type", ""), ""))[1]
        new_label = _TYPE_STYLE.get(adj.get("adjusted_type", ""), ("", adj.get("adjusted_type", ""), ""))[1]
        reason = _esc(adj.get("adjustment_reason", ""))
        adj_html = (
            "<div style='border-top:1px solid rgba(255,255,255,0.1);"
            "padding:10px 0;margin-bottom:10px;'>"
            "<p style='margin:0 0 4px;font-size:0.85rem;color:#ffaa00;font-weight:600;'>"
            f"⚡ 오늘 계획 조정: {orig_label} → <strong>{new_label}</strong></p>"
            + (f"<p style='margin:0;font-size:0.8rem;color:var(--muted);'>{reason}</p>" if reason else "")
            + "</div>"
        )
    elif adj and not adj.get("adjusted"):
        fatigue = adj.get("fatigue_level", "low")
        fatigue_ko = {"low": "낮음", "moderate": "보통", "high": "높음"}.get(fatigue, fatigue)
        boost = " 볼륨 부스트 가능 💪" if adj.get("volume_boost") and (cirs_val or 0) < 50 else ""
        adj_html = (
            "<div style='border-top:1px solid rgba(255,255,255,0.1);"
            "padding:10px 0;margin-bottom:10px;'>"
            f"<p style='margin:0;font-size:0.85rem;'>피로도: <strong>{fatigue_ko}</strong>"
            f" — 계획대로 진행하세요.{boost}</p>"
            "</div>"
        )

    # ── AI 추천 섹션 (메트릭 없으면 표시 안 함) ──────────────────────────
    from src.web.views_training_plan_ui import _build_rule_recommendation
    if utrs_val is not None or cirs_val is not None or ai_override:
        lines = _build_rule_recommendation(utrs_val, cirs_val, cirs_json, workouts)
        if ai_override:
            lines = [ai_override]
    else:
        lines = []

    ai_html = ""
    if lines:
        content = "</p><p style='margin:6px 0;'>".join(lines)
        ai_badge = (
            " <span style='font-size:0.65rem;color:var(--cyan);border:1px solid var(--cyan);"
            "padding:1px 5px;border-radius:8px;'>AI</span>"
            if ai_override else ""
        )
        ai_html = (
            "<div style='border-top:1px solid rgba(255,255,255,0.1);padding-top:12px;'>"
            "<div style='display:flex;align-items:center;gap:8px;margin-bottom:8px;'>"
            "<div style='width:28px;height:28px;"
            "background:linear-gradient(135deg,#00d4ff,#00ff88);"
            "border-radius:50%;display:flex;align-items:center;"
            "justify-content:center;font-size:14px;'>🤖</div>"
            f"<span style='font-size:0.9rem;font-weight:600;'>AI 훈련 추천{ai_badge}</span>"
            "</div>"
            f"<div style='font-size:0.85rem;line-height:1.7;color:rgba(255,255,255,0.88);'>"
            f"<p style='margin:0 0 6px;'>{content}</p></div>"
            "</div>"
        )

    if not badges_html and not adj_html and not ai_html:
        return ""

    return (
        f"<div class='card' style='border-left:4px solid {border_color};margin-bottom:0;'>"
        "<div style='display:flex;align-items:center;gap:8px;margin-bottom:12px;'>"
        f"<span style='font-size:1.1rem;'>{status_icon}</span>"
        "<h3 style='margin:0;font-size:0.95rem;font-weight:600;'>오늘 컨디션 &amp; AI 추천</h3>"
        "</div>"
        + badges_html
        + adj_html
        + ai_html
        + "</div>"
    )
