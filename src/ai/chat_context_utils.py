"""AI 채팅 컨텍스트 — 공통 유틸리티.

chat_context.py에서 분리 (2026-03-29).
"""
from __future__ import annotations

from src.utils.pace import seconds_to_pace as _raw_pace


def _r1(v) -> float | None:
    """소수점 2자리 반올림."""
    return round(float(v), 2) if v is not None else None


def _ri(v) -> int | None:
    """정수 반올림."""
    return round(float(v)) if v is not None else None


def seconds_to_pace(val) -> str:
    """float-safe wrapper."""
    return _raw_pace(int(val))


def _fmt_sec(sec) -> str:
    """초를 H:MM:SS로."""
    if sec is None:
        return "-"
    s = int(sec)
    h, r = divmod(s, 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
