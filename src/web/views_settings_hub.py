"""Settings 허브 보조 렌더링 — sync 상태 요약 + 시스템 정보.

6.4 UI 보완: 참고 디자인(settings_sync.html) 수준 sync 허브.
"""
from __future__ import annotations

import html as _html
import os
from pathlib import Path

from .helpers import db_path


def render_sync_overview(statuses: dict[str, dict], sync_times: dict[str, str | None]) -> str:
    """연동 상태 요약 카드 — 연결된 서비스 수 + 최근 동기화 시간."""
    connected = sum(1 for s in statuses.values() if s.get("ok"))
    total = len(statuses)

    # 가장 최근 동기화 시점
    recent = None
    for t in sync_times.values():
        if t and (recent is None or t > recent):
            recent = t

    if connected == total:
        color, border, indicator = "#00ff88", "rgba(0,255,136,0.3)", "#00ff88"
        label = "모든 서비스 연결됨"
    elif connected > 0:
        color, border, indicator = "#ffaa00", "rgba(255,170,0,0.3)", "#ffaa00"
        label = f"{connected}/{total} 서비스 연결됨"
    else:
        color, border, indicator = "#ff4444", "rgba(255,68,68,0.3)", "#ff4444"
        label = "연결된 서비스 없음"

    sync_text = f"마지막 동기화: {_html.escape(recent)}" if recent else "동기화 기록 없음"

    # 개별 서비스 상태 도트
    dots = []
    names = {"garmin": "Garmin", "strava": "Strava", "intervals": "Intervals", "runalyze": "Runalyze"}
    for key, st in statuses.items():
        dot_color = "#00ff88" if st.get("ok") else "rgba(255,255,255,0.3)"
        dots.append(
            f"<span style='display:inline-flex;align-items:center;gap:4px;font-size:0.78rem;'>"
            f"<span style='width:8px;height:8px;border-radius:50%;background:{dot_color};display:inline-block;'></span>"
            f"{names.get(key, key)}</span>"
        )

    return (
        f"<div class='card' style='border-left:4px solid {color};margin-bottom:0.5rem;'>"
        f"<div style='display:flex;align-items:center;gap:12px;margin-bottom:8px;'>"
        f"<span style='width:12px;height:12px;background:{indicator};border-radius:50%;'></span>"
        f"<div>"
        f"<div style='font-size:1rem;font-weight:600;'>{label}</div>"
        f"<div style='font-size:0.8rem;color:var(--muted);'>{sync_text}</div>"
        f"</div></div>"
        f"<div style='display:flex;gap:16px;flex-wrap:wrap;'>"
        + "".join(dots)
        + "</div></div>"
    )


def render_system_info(config: dict) -> str:
    """시스템 정보 카드 — RunPulse 버전, DB 크기, 공식 버전."""
    dbp = db_path()
    db_size_str = "N/A"
    db_path_str = str(dbp) if dbp else "N/A"
    if dbp and dbp.exists():
        size_mb = dbp.stat().st_size / (1024 * 1024)
        db_size_str = f"{size_mb:.1f} MB"

    # 메트릭 공식 버전
    formula_ver = "v0.2 (PDF 원본 기준)"
    ai_model = config.get("ai", {}).get("model", "genspark (기본)")

    rows = [
        ("RunPulse 버전", "v0.2"),
        ("메트릭 공식", formula_ver),
        ("AI 모델", _html.escape(str(ai_model))),
        ("DB 경로", f"<code style='font-size:0.75rem;'>{_html.escape(db_path_str)}</code>"),
        ("DB 크기", db_size_str),
    ]
    items = "".join(
        f"<div style='display:flex;justify-content:space-between;padding:6px 0;"
        f"border-bottom:1px solid var(--row-border);font-size:0.85rem;'>"
        f"<span style='color:var(--muted);'>{label}</span>"
        f"<span>{value}</span></div>"
        for label, value in rows
    )
    return (
        "<div class='card'>"
        "<h2 style='margin-bottom:0.8rem;'>시스템 정보</h2>"
        + items
        + "</div>"
    )
