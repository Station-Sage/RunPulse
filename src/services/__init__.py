# src/services/__init__.py
"""서비스 레이어 — Phase 5(읽기 전용 3개) + Phase 7 D5 확장(today/coach 추가, 3개는 스텁).

DB에서 데이터를 읽어 가공된 dict를 반환한다. 원칙은 읽기 전용이지만, Today의
save_checkin()과 Coach의 스레드/메시지 저장은 명시적 예외다(07-migration-roadmap.md
Phase 7a). 첫 번째 인자는 항상 sqlite3.Connection. 반환값은 dict (snake_case 키).
단위 변환 하지 않음 — SI 그대로 반환.

파일: activity_service·dashboard_service·wellness_service(Phase 5, 구현 완료) /
today_service·coach_service(Phase 7a, 구현 완료) / metrics_service·plan_service·
data_service(Phase 7b~7d 스텁). story_service는 없음 — Story는 Today L2로 흡수됨
(REVIEW-03, 00-diagnostic-and-direction.md §5.1).

설계 문서: v0.3/data/phase-5-impl/01-service-layer.md,
v0.3/data/phase-7-ui-renewal/06-data-layer-extensions.md (D5)
의존: src/utils/db_helpers.py, src/utils/metric_registry.py, src/ai/chat_engine.py(Coach)
주의: metric_store 조회 시 is_primary=1 필터 필수. CalcContext는 사용하지 않는다
(ADR-009는 Calculator 전용, 서비스 레이어와 다른 레이어).
"""
