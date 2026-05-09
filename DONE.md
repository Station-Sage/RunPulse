# DONE — 완료된 버그

- **[BUG-WORKOUT-LABEL]** `activity_summaries.workout_label` 컬럼 누락 → DDL 추가 + SCHEMA_VERSION 14→15 마이그레이션.
- **[BUG-SYNC-STATUS]** `sync_jobs.service` 없음 → `source` 컬럼 사용으로 수정 (`views_training_loaders.py`, `views_training_plan_ui.py`).
- **[BUG-DEV-TAB]** `/dev` 라우트 없음 → `views_dev.py`에 `/dev` → `/config` 리다이렉트 추가.
- **[BUG-REPORT-METRICS]** 레포트탭 메트릭 데이터 없음 → `views_report*.py` 전체 메트릭 이름 소문자 canonical 이름으로 수정 (metric_store SSOT 기준).
- **[BUG-GARMIN-429]** bg_sync 배치마다 무조건 재인증하던 문제 수정 (45분 cooldown). trigger_sync/trigger-sync-stream에서 bg_sync 활성 중 수동 동기화 차단 추가.
- **[BUG-PARTIAL-FLAG]** trigger_sync/trigger-sync-stream에서 returncode=0 시 stderr를 error로 처리하던 로직 제거.
- **[BUG-RAW-PAYLOAD-LIST]** `upsert_payload` `isinstance` 체크를 `(dict, list)` 로 확장, 타입 선언도 `str | dict | list` 로 변경.
- **[BUG-DASHBOARD-INCLUDE-WEEKLY]** `views_dashboard.py` `run_for_date(include_weekly=False)` 잘못된 파라미터 제거 → `run_for_date(conn, today)`.
