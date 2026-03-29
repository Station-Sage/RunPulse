# Changelog

> 이전 이력은 `changelog_history.md` 참조

## [fix/metrics-everythings] 2026-03-29 (리팩토링 3차 — dashboard_cards 분리)

### 리팩토링
- `views_dashboard_cards.py` 880줄 → 5파일 분리:
  - `views_dashboard_cards.py` (34줄): re-export 진입점
  - `views_dashboard_cards_status.py` (145줄): 색상상수 + 미니게이지 + `render_daily_status_strip` + `render_weekly_summary`
  - `views_dashboard_cards_fitness.py` (280줄): `render_fitness_trends_chart` + `_render_pmc_chart` + `_render_activity_list` + `_render_fitness_mini` + `_fitness_ai_note`
  - `views_dashboard_cards_risk.py` (185줄): `render_risk_pills_v2` + `_render_cirs_banner` + `_render_utrs_factors` + `_render_cirs_breakdown` + `_render_risk_pills`
  - `views_dashboard_cards_recommend.py` (267줄): `_render_gauge_card` + `_render_rmr_card` + `_render_training_recommendation` + `_render_darp_mini`
- `views_dashboard.py`: 기존 import 경로 유지 (re-export 방식)

### 테스트
- 총 **1122 통과** 확인 (분리 후 회귀 없음)

---

> 이전 이력: `changelog_history.md` 참조
