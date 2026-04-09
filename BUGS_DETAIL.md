# BUGS_DETAIL

> v0.2 버그는 전체 재개발 대상이므로 아카이브됨.
> v0.3 버그만 기록한다.

## #P5J — Phase 5-J: distance_km → distance_m 마이그레이션

**범위 결정 (2026-04-09):**

`views_activities_table.py`는 `unified_activities.get_unified_activities()`를 통해
소스별 그룹화 + Provenance 추적(`UnifiedField`)을 수행한다.
`activity_service.get_activity_list()`는 그룹화/Provenance 기능이 없으므로
단순 전환 시 소스별 서브행 UI가 깨진다.

→ `views_activities_table.py` 및 `unified_activities.py`는 **변경 제외**.
→ Phase 7 UI 재설계 시 `activity_service`로 전환한다.

**변경 대상 (activity_summaries를 직접 읽는 소비자):**
- `src/analysis/` — report.py, trends.py, weekly_score.py, compare.py, activity_deep.py, race_readiness.py
- `src/ai/` — context_builders.py, chat_context_rich.py, chat_context_format.py, tools.py, chat_engine_rules.py
- `src/web/views_dashboard.py`, views_dashboard_loaders.py, views_report.py, views_report_loaders.py, views_race.py, views_race_enhanced.py 등

**유지 대상 (km이 올바른 단위):**
- `src/import_export/` — 외부 CSV 컬럼명 매핑
- `src/training/` — planned_workouts.distance_km (사용자 지정 km 목표)
- `src/web/views_training_*.py` — 훈련 계획 뷰
- `src/db_setup.py` — goals.distance_km, planned_workouts.distance_km 스키마
- `src/services/unified_activities.py` — Phase 7까지 현행 유지

**DoD #9**: `src/web/views_export.py` 신규 (activity CSV 내보내기, distance_m → km 변환)
**DoD #12**: `tests/test_consumer_migration.py` 신규 (~15개 스모크 테스트)