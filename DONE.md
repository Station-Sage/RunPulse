# DONE — 완료된 버그

- **[BUG-SYNC-STATUS]** `sync_jobs.service` 없음 → `source` 컬럼 사용으로 수정 (`views_training_loaders.py`, `views_training_plan_ui.py`).
- **[BUG-DEV-TAB]** `/dev` 라우트 없음 → `views_dev.py`에 `/dev` → `/config` 리다이렉트 추가.
- **[BUG-REPORT-METRICS]** 레포트탭 메트릭 데이터 없음 → `views_report*.py` 전체 메트릭 이름 소문자 canonical 이름으로 수정 (metric_store SSOT 기준).
- **[BUG-GARMIN-429]** bg_sync 배치마다 무조건 재인증하던 문제 수정 (45분 cooldown). trigger_sync/trigger-sync-stream에서 bg_sync 활성 중 수동 동기화 차단 추가.
- **[BUG-PARTIAL-FLAG]** trigger_sync/trigger-sync-stream에서 returncode=0 시 stderr를 error로 처리하던 로직 제거.
- **[BUG-RAW-PAYLOAD-LIST]** `upsert_payload` `isinstance` 체크를 `(dict, list)` 로 확장, 타입 선언도 `str | dict | list` 로 변경.
- **[BUG-DASHBOARD-INCLUDE-WEEKLY]** `views_dashboard.py` `run_for_date(include_weekly=False)` 잘못된 파라미터 제거 → `run_for_date(conn, today)`.
- **[BUG-WORKOUT-TYPE-COLUMN]** 앱 AI 코치 컨텍스트가 `workout_type_classified`를 `numeric_value`에서 읽어 항상 비던 버그 — `text_value`로 수정(`chat_context_builders.py` 2곳, `chat_context_rich.py` 3곳) + 회귀 테스트. 오토파일럿 P7-FIX-CHAT-WORKOUT-TYPE (2026-09-26).
- **[AI-CHAT-TOOL-PROMPT]** `_TOOL_SYSTEM_TEXT`에 누락된 `get_training_summary`·`get_activity_laps`·`compare_workout_sets` 추가 + 모든 도구 이름 포함 검증 테스트. 오토파일럿 P7-FIX-CHAT-TOOL-PROMPT (2026-09-26).
- **[P7-PRED r4 예측 리뉴얼]** 유닛 30개 구현(클라우드 세션, PR #66) 후 로컬 리뷰 — 명세 대조 이탈 없음(72 타입 보완만 수용), 리뷰 중 결함 3건 교정: TIDS `log10(0)`(88), Garmin LT 이력 응답 형태·366일 창 제한(25), 실 DB 범위 테스트를 글리치 허용 비율 방식으로 변경. 풀 pytest 1928 통과.
