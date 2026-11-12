# src/web/__init__.py
"""Flask 앱 셸 + 남은 v1 라우트.

v1 화면은 일몰 중(V1-1). S4-91(ADR-056)에서 대체 완료 화면을 퇴역 — `v1_retired`(GET→v2 302, POST→410).
남은 v1: `views_settings_garmin`(CF 설정 폼 대체 없음)·`views_strava_oauth`(OAuth URL 불변)·`views_training_export`(.ics).
공용 파일은 view 밖으로 이관했다(V1-10·V1-19):
bg_sync·auto_sync → src/sync/, 공용 3함수 → src/utils/user_context.py,
views_mcp_remote → src/mcp_remote/http.py, template_helpers → src/utils/template_helpers.py.

설계 문서: v0.3/data/phase-7-ui-renewal/design-2026-10/bundles/v1-sunset-prep.md
의존: src/services/, src/utils/metric_registry.py
주의: 기존 뷰는 v0.2 스키마 기준 — 새 스키마와 혼용 금지
"""
