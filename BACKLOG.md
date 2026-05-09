# BACKLOG

## NOW

## BUGS

## 미해결 확인 사항 (MIGRATION-04 §6)
- [중간] curl_cffi ARM64 wheel 존재 여부 (AWS Graviton) — Dockerfile 빌드
- [낮음] test_flask_routes.py garmin 라우트 포함 여부 — 테스트 커버리지

## NEXT

## DONE (recent)
- **[BUG-METRIC-VO2MAX / BUG-METRIC-MISSING]** VO2Max 항상 None 수정: `trends.py` fallback metric, `race_readiness.py` scope/이름, `activity_deep.py` daily_fitness→metric_store 교체, `hr_zone_distribution`→`hr_zones_detail` 키 수정. `daily_fitness` 잔존 참조 3곳 정리(`suggestions.py` TSB, `views_dev.py` count, `runalyze.py` dead code). 1043 passed.
- **[TEST-STALE-DATES / TEST-GARMIN-AUTH / TEST-ENSURE-DEPS]** 테스트 9건 수정: 픽스처 하드코딩 날짜 → 상대 날짜, garmin_auth B안(테스트를 구현에 맞게 수정 + explicit-path 폴백 버그 수정), `patch.dict(sys.modules, {"garminconnect": None})` 격리 방식 채택. 1043 passed.
- **[GARMIN-REPROCESS]** source_payloads → 활동 18건·웰니스 15건·메트릭 43건 재구축 완료. `device_name/gear_id=NULL` — activity_detail 미보존, Garmin IP 블록 해소 후 API 재호출 필요.
- **[BUG-GEMINI-429]** `ai_cache` 데이터 핑거프린트 기반 무효화 — 신규 활동·웰니스·날짜 변경 시에만 재호출 (ADR-011)
- **[BUG-6]** `daily_wellness` v0.3 컬럼명 전면 수정 (5컬럼 rename, source 필터 제거, `source_payloads` 스키마 맞춰 test_raw_payload.py 재작성, `upsert_payload` activity_id COALESCE 버그 수정)
- **[BUG-5]** `garmin_backfill.py` Layer 0 설계 정합성 수정 (`upsert_activity()` 전환, whitelist 필터, metric_store 라우팅)
- **[BUG-4]** `garmin_api_extensions.py` DDL 3컬럼 수정, `activity_exercise_sets` DDL 추가
- **[BUG-3]** activity_streams 소비자 5개 v0.3 typed columns 마이그레이션
- Garmin 인증 실패: ADR-010 A안 (local sync 스크립트 + VPS 업로드 API), 17 tests
- **[DB-RESET]** `activity_summaries` DDL 컬럼 누락 → DB DROP 재생성, Strava/Intervals 재동기화
- fix: strava/intervals sync_activities/sync_wellness undefined 버그 수정
- garminconnect 0.3.x 마이그레이션 (MIGRATION-01~04) — curl_cffi, tokenstore, MFA, 38 new tests
