"""운영 상태 저장소 — 다중 사용자 스케줄러 상태·실행 기록·활동 신호·LLM 사용량(전역 `data/ops.db`).

사용자 DB(running.db)·원장(sync_jobs.db)과 분리된 전역 파일 하나에 둔다(AUTH-MULTIUSER-SYNC MS-3).
- store.py: OpsStore — DDL·UPSERT·보존 정리(clock 주입)
- activity.py: 활동 신호(before_request 10분 스로틀, /mcp, local-sync) — 캘린더 피드 제외

설계 문서: v0.3/data/phase-7-ui-renewal/design-2026-11-features/multiuser-sync.md §3.4·§3.5
주의: 경로는 env `OPS_DB_PATH` 로 덮어쓸 수 있다(테스트 격리). 계정 삭제 시 `OpsStore.delete_user`.
"""
