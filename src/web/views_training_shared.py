"""훈련탭 공용 상수/헬퍼 — 여러 렌더러 모듈에서 공유."""
from __future__ import annotations

import html as _html

# 운동 타입별 색상·라벨·아이콘
_TYPE_STYLE: dict[str, tuple[str, str, str]] = {
    "easy":     ("linear-gradient(135deg,#00c853,#00e676)", "이지런",   "🟢"),
    "tempo":    ("linear-gradient(135deg,#ff9100,#ffab40)", "템포런",   "🟠"),
    "interval": ("linear-gradient(135deg,#ff1744,#ff5252)", "인터벌",   "🔴"),
    "long":     ("linear-gradient(135deg,#7c4dff,#b388ff)", "롱런",     "🟣"),
    "rest":     ("linear-gradient(135deg,#546e7a,#78909c)", "휴식",     "⚪"),
    "recovery": ("linear-gradient(135deg,#00bcd4,#4dd0e1)", "회복조깅", "🔵"),
    "race":     ("linear-gradient(135deg,#ffd600,#ffff00)", "레이스",   "🏁"),
}

# 타입별 배경색 (카드/셀 배경)
_TYPE_BG: dict[str, str] = {
    "easy":     "rgba(0,255,136,0.15)",
    "tempo":    "rgba(255,170,0,0.15)",
    "interval": "rgba(255,68,68,0.15)",
    "long":     "rgba(128,0,255,0.15)",
    "rest":     "rgba(84,110,122,0.1)",
    "recovery": "rgba(0,188,212,0.15)",
    "race":     "rgba(255,214,0,0.15)",
}


def _esc(s: str) -> str:
    """HTML 이스케이프."""
    return _html.escape(str(s))
