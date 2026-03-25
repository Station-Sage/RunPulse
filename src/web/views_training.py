"""훈련 계획 뷰 — Flask Blueprint.

/training  : 훈련 계획 메인 (v0.3에서 완전 구현 예정)
"""
from __future__ import annotations

from flask import Blueprint

from src.web.helpers import html_page, bottom_nav, no_data_card

training_bp = Blueprint("training", __name__)


def _render_coming_soon() -> str:
    """Coming-soon 스캐폴딩 카드."""
    return (
        "<div class='card' style='text-align:center;padding:2.5rem 1.5rem;'>"
        "<div style='font-size:2.5rem;margin-bottom:0.8rem;'>🏗️</div>"
        "<h2 style='margin:0 0 0.5rem;'>훈련 계획 (준비 중)</h2>"
        "<p class='muted' style='margin:0 0 1.2rem;'>AI 기반 훈련 계획 생성 기능은 v0.3에서 제공됩니다.</p>"
        "<div style='display:flex;flex-direction:column;gap:0.6rem;max-width:340px;margin:0 auto;'>"
        + _feature_chip("📅", "주간 훈련 플랜 자동 생성")
        + _feature_chip("🎯", "레이스 목표 기반 빌드업")
        + _feature_chip("💤", "회복일·강도 자동 조절")
        + _feature_chip("⌚", "Garmin 워치 자동 등록")
        + "</div>"
        "</div>"
        + _render_current_week_placeholder()
    )


def _feature_chip(icon: str, text: str) -> str:
    return (
        f"<div style='display:flex;align-items:center;gap:0.7rem;"
        f"background:rgba(255,255,255,0.05);border-radius:10px;"
        f"padding:0.55rem 0.9rem;font-size:0.88rem;'>"
        f"<span style='font-size:1.1rem;'>{icon}</span>"
        f"<span>{text}</span>"
        f"</div>"
    )


def _render_current_week_placeholder() -> str:
    """이번 주 훈련 일정 placeholder."""
    days = ["월", "화", "수", "목", "금", "토", "일"]
    rows = "".join(
        f"<div style='display:flex;align-items:center;gap:0.8rem;"
        f"padding:0.6rem 0;border-bottom:1px solid rgba(255,255,255,0.06);'>"
        f"<span style='font-size:0.78rem;color:var(--muted);min-width:1.4rem;'>{d}</span>"
        f"<div style='flex:1;height:2.2rem;border-radius:8px;"
        f"background:rgba(255,255,255,0.04);'></div>"
        f"</div>"
        for d in days
    )
    return (
        "<div class='card'>"
        "<h2 style='margin-bottom:0.8rem;'>이번 주 훈련 일정</h2>"
        "<p class='muted' style='font-size:0.82rem;margin-bottom:0.8rem;'>훈련 계획이 설정되면 여기에 표시됩니다.</p>"
        + rows
        + "</div>"
    )


@training_bp.route("/training")
def training_page():
    """훈련 계획 페이지 (v0.3 스캐폴딩)."""
    body = (
        "<div style='max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px;'>"
        "<div style='display:flex;align-items:center;padding:20px 0;"
        "border-bottom:1px solid rgba(255,255,255,0.1);margin-bottom:1rem;'>"
        "<span style='font-size:20px;font-weight:bold;'>훈련 계획</span>"
        "</div>"
        + _render_coming_soon()
        + "</div>"
    )
    return html_page("훈련 계획", body + bottom_nav("training"))
