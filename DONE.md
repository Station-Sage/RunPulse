# DONE — 완료된 버그

- **[BUG-GARMIN-429]** bg_sync 배치마다 무조건 재인증하던 문제 수정 (45분 cooldown). trigger_sync/trigger-sync-stream에서 bg_sync 활성 중 수동 동기화 차단 추가.
- **[BUG-PARTIAL-FLAG]** trigger_sync/trigger-sync-stream에서 returncode=0 시 stderr를 error로 처리하던 로직 제거.
- **[BUG-RAW-PAYLOAD-LIST]** `upsert_payload` `isinstance` 체크를 `(dict, list)` 로 확장, 타입 선언도 `str | dict | list` 로 변경.
- **[BUG-DASHBOARD-INCLUDE-WEEKLY]** `views_dashboard.py` `run_for_date(include_weekly=False)` 잘못된 파라미터 제거 → `run_for_date(conn, today)`.
- **[BUG-WORKOUT-TYPE-COLUMN]** 앱 AI 코치 컨텍스트가 `workout_type_classified`를 `numeric_value`에서 읽어 항상 비던 버그 — `text_value`로 수정(`chat_context_builders.py` 2곳, `chat_context_rich.py` 3곳) + 회귀 테스트. 오토파일럿 P7-FIX-CHAT-WORKOUT-TYPE (2026-09-26).
- **[AI-CHAT-TOOL-PROMPT]** `_TOOL_SYSTEM_TEXT`에 누락된 `get_training_summary`·`get_activity_laps`·`compare_workout_sets` 추가 + 모든 도구 이름 포함 검증 테스트. 오토파일럿 P7-FIX-CHAT-TOOL-PROMPT (2026-09-26).
- **[P7-PRED r4 예측 리뉴얼]** 유닛 30개 구현(클라우드 세션, PR #66) 후 로컬 리뷰 — 명세 대조 이탈 없음(72 타입 보완만 수용), 리뷰 중 결함 3건 교정: TIDS `log10(0)`(88), Garmin LT 이력 응답 형태·366일 창 제한(25), 실 DB 범위 테스트를 글리치 허용 비율 방식으로 변경. 풀 pytest 1928 통과.
- **[DATA-CTL-WARMUP]** 2025-09 이전 CTL 과소(심박 결측으로 TRIMP 없음). `TRIMPEstCalculator`(ADR-024)로 심박 결측 러닝 133건 추정 TRIMP 산출 + 운영 DB 전 기간 PMC 재계산(2026-10-07, 백업 /tmp/bk/running_pre_trimp_est_20261007.db). 2024-10~2025-03 월평균 CTL 3→24~33, 2025-10 이후 불변. 비-정본 중복 활동 7건·측정 TRIMP 우선 1건은 정본 활동에 값이 있어 정상.
- **[SYNC-ERROR-SURFACE]** 외부 API 오류 표면화 — U15g(SyncSourceError·error_code·동기화 탭 표시)에 이어, 일반 예외로 끝난 배치도 전체 0건이면 job `failed`+분류 코드로 마감(`bg_sync._batch_error`). 일부 성공이면 `completed` 유지 (2026-10-07).
- **[BUG-INDOOR-RUN-TYPE]** Garmin `indoor_running` 16건을 러닝으로 정규화(`_RUNNING_TYPES`, 2026-09-26) + 운영 DB 16건 `running` 정정 및 전 기간 `recompute_all` 완료(2026-10-10). 활동 632·645 등에 TRIMP·HRSS 생성 확인. 백업 `running.db.bak-20261009-pre-indoor`(커밋 금지).
