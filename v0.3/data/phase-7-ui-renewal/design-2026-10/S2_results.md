# S2 결과 (2026-10-13) — v1 일몰 준비 (공용 파일 view 밖 이관·v1 호출부 정리)

브랜치 `ccr-8ec9b1bc-q2i3u3`. 설계서 `bundles/v1-sunset-prep.md`. 롤백 = 단계별 커밋 revert. 미확인은 '미확인'으로 표시. **상태: 진행 중**(아래 §3 단계 표가 SSOT).

## 1. S2 결정 (2026-10-13, 사용자 승인)

| ID | 내용 |
|---|---|
| V1S-9 | 설계서 §4 6단계(/switch-user·SRV-6·uid 규칙)·7단계(MenuDrawer CSV)는 S3 로 이관. S2 = 1~5 + 마감 |
| V1S-10 | `template_helpers.py` 이름 유지(`src/utils/template_helpers.py`) |
| V1S-11 | S2 에서 ADR 추가 없음(ADR 048~051 은 S3 이후) |

## 2. 미결정·다른 작업으로 이관

| 항목 | 상태 | 이관처 |
|---|---|---|
| `app.py` 비UI 직접 라우트(`/trigger-sync*`·`/bg-sync/*`·`/api/garmin/local-sync`·`/import*`·`/sync-status`)의 위치·처리 (V1S-12) | **미결정**. S2 는 목록화만, 이동 안 함. 사용처 확인에 운영 접근 필요 | S3 이후 결정 |
| `/switch-user` v2 이관·SRV-6·uid 규칙(`validate_uid`)·MenuDrawer CSV→EXP 링크 | 결정됨(V1-3·8·9·11, SRV-6·13), 구현만 남음 | S3 |
| MenuDrawer `/ai-coach` quickLink, `SyncPanel.svelte` `/settings` 링크, `data/export/+page.svelte:133` | 결정됨(V1-5: BACKLOG 별도 항목) | MENUDRAWER-POST-V1 |
| `views_ai_coach.py`·`views_ai_coach_cards.py` 삭제 | 결정됨(V1-17) | v1 일몰 시 |
| 300줄 초과 파일 분할: `helpers.py`(이동 후에도 초과)·`bg_sync.py` 625·`app.py` 1161 | S2 에서 분할하지 않음. 별도 결정 없음 | 미배정 |
| `src/api` 를 `SCAN_DIRS` 에 추가하면 기존 `routes_data.py`(305줄)·`routes_library.py`(316줄)에 새 경고 | 경고일 뿐 필수 검사 아님 | 미배정(경고로 수용) |

## 3. 단계 진행 (1단계 = 1커밋)

| 단계 | 내용 | 커밋 |
|---|---|---|
| 0 | importer·`SCAN_DIRS`·비UI 라우트 실측(커밋 없음) | — |
| 1 | `bg_sync`·`auto_sync` → `src/sync/` | |
| 2 | `helpers` 3함수 → `src/utils/user_context.py` | |
| 3 | `views_mcp_remote` → `src/mcp_remote/http.py` | |
| 3b | `template_helpers.py` → `src/utils/` | |
| 3c | `views_calendar_feed.py` → `src/api/routes_calendar_feed.py` | |
| 4 | `load_adjustment` 제거 | |
| 5a | `/ai-coach` 라우트 등록 제거 | |
| 5b | suggestions 2함수 제거 | |
| 마감 | files_index·check_docs·전체 pytest·최종 grep·BACKLOG | |
