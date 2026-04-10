# BACKLOG

## NOW
(없음)

## BUGS
- ❌ Garmin 인증 실패: VPS(AWS) IP 차단으로 로그인 시 429 발생 — 해결 방안 미결

## 미해결 확인 사항 (MIGRATION-04 §6)
- [높음] garminconnect 0.3.x connectapi 내부 자동 토큰 갱신 여부 — 장시간 배치 안정성
- [중간] curl_cffi ARM64 wheel 존재 여부 (AWS Graviton) — Dockerfile 빌드
- [낮음] test_flask_routes.py garmin 라우트 포함 여부 — 테스트 커버리지
- [낮음] garminconnect 0.3.x get_body_battery_events(cdate) 시그니처 — 현행 코드가 (cdate, cdate) 2인자 호출

## NEXT
- Phase 7: UI 재설계 (views_activities_table.py → activity_service 전환 포함)

## DONE (recent)
- fix: strava/intervals sync_activities/sync_wellness undefined 버그 수정 (wrapper 추가)
- garminconnect 0.3.x 마이그레이션 (MIGRATION-01~04) — curl_cffi, tokenstore, MFA, 38 new tests
- Phase 6: Initial Data Load & Validation — GarminBulkLoader, DataValidator(12-check), initial-load CLI(9-step), db_status, snapshot.sh
