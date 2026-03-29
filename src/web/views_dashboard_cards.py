"""대시보드 카드 진입점 — 하위 모듈 re-export (backward compat).

세부 구현:
  - views_dashboard_cards_status.py   : 상태 스트립 + 주간 요약 + 색상 상수
  - views_dashboard_cards_fitness.py  : 피트니스 추세 + PMC + 활동 목록 + 피트니스 미니
  - views_dashboard_cards_risk.py     : 리스크 pills + CIRS/UTRS 상세
  - views_dashboard_cards_recommend.py: 훈련 권장 + DARP 예측 + 게이지/RMR
"""
from __future__ import annotations

# Re-export everything views_dashboard.py imports directly
from .views_dashboard_cards_status import (  # noqa: F401
    _CIRS_COLORS,
    _UTRS_COLORS,
    render_daily_status_strip,
    render_weekly_summary,
)
from .views_dashboard_cards_fitness import (  # noqa: F401
    _render_activity_list,
    _render_fitness_mini,
    render_fitness_trends_chart,
)
from .views_dashboard_cards_risk import (  # noqa: F401
    _render_cirs_banner,
    _render_cirs_breakdown,
    _render_utrs_factors,
    render_risk_pills_v2,
)
from .views_dashboard_cards_recommend import (  # noqa: F401
    _render_darp_mini,
    _render_gauge_card,
    _render_rmr_card,
    _render_training_recommendation,
)
