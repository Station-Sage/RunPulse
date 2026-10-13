# S2 결과 (2026-10-13) — v1 일몰 준비 (공용 파일 view 밖 이관·v1 호출부 정리)

브랜치 `ccr-8ec9b1bc-q2i3u3`. 설계서 `bundles/v1-sunset-prep.md`. 롤백 = 단계별 커밋 revert. 미확인은 '미확인'으로 표시. **상태: 구현·검증 완료, 사용자 승인 2026-10-13**.

## 1. S2 결정 (2026-10-13, 사용자 승인)

| ID | 내용 |
|---|---|
| V1S-9 | 설계서 §4 6단계(/switch-user·SRV-6·uid 규칙)·7단계(MenuDrawer CSV)는 S3 로 이관. S2 = 1~5 + 마감 |
| V1S-10 | `template_helpers.py` 이름 유지(`src/utils/template_helpers.py`) |
| V1S-11 | S2 에서 ADR 추가 없음(ADR 048~051 은 S3 이후) |
| (승인) | S2 결과 승인(2026-10-13). V1S-12 는 S3 로 연기, 열려 있는 항목(R1 백필·TXT-1·FRS-28·`TEST-PLAN-CREATION-DATE`)은 그대로 유지 |
| ENV-1 | Flask 설치·테스트 환경 정비는 S3 0단계(단계만 결정, 내용은 S3 계획에서 승인 — 아래 §7) |

## 2. 미결정·다른 작업으로 이관

| 항목 | 상태 | 이관처 |
|---|---|---|
| `app.py` 비UI 직접 라우트(`/trigger-sync*`·`/bg-sync/*`·`/api/garmin/local-sync`·`/import*`·`/sync-status`)의 위치·처리 (V1S-12) | **미결정**. S2 는 목록화만, 이동 안 함. 사용처 확인에 운영 접근 필요 | **S3 에서 결정**(2026-10-13 사용자 연기) |
| `/switch-user` v2 이관·SRV-6·uid 규칙(`validate_uid`)·MenuDrawer CSV→EXP 링크 | 결정됨(V1-3·8·9·11, SRV-6·13), 구현만 남음 | S3 |
| MenuDrawer `/ai-coach` quickLink, `SyncPanel.svelte` `/settings` 링크, `data/export/+page.svelte:133` | 결정됨(V1-5: BACKLOG 별도 항목) | MENUDRAWER-POST-V1 |
| `views_ai_coach.py`·`views_ai_coach_cards.py` 삭제 | 결정됨(V1-17) | v1 일몰 시 |
| 300줄 초과 파일 분할: `helpers.py`(이동 후에도 초과)·`bg_sync.py` 625·`app.py` 1161 | S2 에서 분할하지 않음. 별도 결정 없음 | 미배정 |
| `src/api` 를 `SCAN_DIRS` 에 추가하면 기존 `routes_data.py`(305줄)·`routes_library.py`(316줄)에 새 경고 | 경고일 뿐 필수 검사 아님 | 미배정(경고로 수용) |

## 3. 단계와 커밋 (1단계 = 1커밋)

| 단계 | 내용 | 커밋 |
|---|---|---|
| 문서 | S2 결정·미결정·이관 기록 | `87c4a66` |
| 1 | `bg_sync`·`auto_sync` → `src/sync/` (importer src 8·tests 10) | `2b13ea7` |
| 2 | `project_root`·`get_current_user_id`·`db_path` → `src/utils/user_context.py` (47파일) | `ff45965` |
| 3 | `views_mcp_remote` → `src/mcp_remote/http.py`, `SCAN_DIRS`+`src/mcp_remote` | `4e72fbc` |
| 3b | `template_helpers.py` → `src/utils/` | `a4e7b08` |
| 3c | `views_calendar_feed` → `src/api/routes_calendar_feed.py`, `SCAN_DIRS`+`src/api` | `cd3c80c` |
| 4 | `load_adjustment` 제거, `adjustment = None` | `7f0a93e` |
| 5a | `/ai-coach` 라우트 등록 제거(파일 잔존) | `daba402` |
| 5b | `get_runner_state`·`rule_based_chips`·`RunnerState` 제거, 테스트 12개 삭제 | `f504d2a` |

구 경로 재노출 shim 은 두지 않았다(V1S-5). 롤백 = 단계별 커밋 revert(역순).

## 4. 사용자에게 보이는 변화 (v1 만, V1-13 감수)

- v1 `/ai-coach` 5개 경로(`/ai-coach`, `/chat-async`, `/chat`, `/prompt`, `/paste-response`) 모두 404.
- v1 `/training` 의 컨디션 조정 카드가 표시되지 않는다.
- v2 화면·API·`/mcp`·`/feeds/cal/<token>.ics` URL 동작은 불변(테스트 기준; 실제 브라우저·운영 확인은 '미확인').
- v2 `MenuDrawer` 의 `AI 코치` 링크는 404 로 간다(죽은 링크 — MENUDRAWER-POST-V1 소관, 프런트는 S2 에서 수정하지 않음).

## 5. 구현 중 확인·결정한 세부 (설계서에 없던 것)

| 항목 | 내용 |
|---|---|
| 한 import 문에 3함수와 HTML 헬퍼가 섞인 곳 | AST 로 전수 처리(MIX 24곳): 이동 대상은 `from src.utils.user_context import …` 로 분리, 나머지는 `from .helpers import …` 유지 |
| `resolve_user_id` 의 폴백 | 이전엔 `except Exception` 으로 flask 미설치도 `"default"`. 이관 후 `ImportError` 만 `"default"` 로 좁혀 유지(`RuntimeError` 는 `get_current_user_id` 내부에서 처리) |
| 테스트 패치 바인딩 | `test_api_today`·`test_flask_routes` 의 모듈 속성 교체 대상을 `src.utils.user_context` 로 변경. 각 라우트 모듈이 `db_path` 를 따로 바인딩하므로 기존처럼 모듈별 교체도 유지 — 통과 확인 |
| `src/api` SCAN_DIRS 추가 | 새 경고는 이미 알려진 `routes_data.py` 305줄·`routes_library.py` 316줄이 전부일 것으로 보았으나, 추가 전후 경고 수는 동일(63). 두 파일은 이미 경고 목록에 있었음 |

## 6. 위험·한계

| # | 내용 | 처리 |
|---|---|---|
| R1 | `app.py` 비UI 직접 라우트가 `src/web/app.py` 에 그대로 있다(V1S-12 미결정). v1 일몰 때 `app.py` 를 정리하면 같이 사라질 수 있음 — 아래 목록 | S3 에서 결정 |
| R2 | `views_ai_coach.py` 의 `_load_chips` 가 제거된 함수를 import 한다. 라우트 미등록이라 도달 불가이며 `except Exception` 으로 감싸 있음. 파일째 일몰 때 삭제(V1-17) | 수용 |
| R3 | `src/web/helpers.py` 880줄, `bg_sync.py` 625줄, `app.py` 1159줄: 300줄 초과 경고 지속 | 미배정 |
| R4 | v1 `/ai-coach` 외 v1 HTML 곳곳(`helpers.py:569` 하단 내비, `views_report_sections.py` 3곳)이 `/ai-coach` 링크를 유지 → 404 | V1-13 감수. 일몰 때 정리 |
| R5 | `src/web/__init__.py` docstring 에서 'Phase 5 template_helpers' 문구를 이관 내용으로 교체 | 완료 |
| R6 | 운영 DB·실제 브라우저·gunicorn 기동은 확인하지 못했다 | 미확인 |

### `app.py` 비UI 직접 라우트 목록 (0단계 (d), 코드 사실 2026-10-13)

| 경로 | 메서드 | 비고 |
|---|---|---|
| `/api/garmin/local-sync` | POST | 로컬 동기화 클라이언트용 추정(사용처 미확인) |
| `/trigger-sync`, `/trigger-sync-bg`, `/trigger-sync-stream` | POST | v1 동기화 트리거 |
| `/bg-sync/start`·`pause`·`resume`·`stop`·`status` | POST/GET | bg_sync 제어 |
| `/sync-status` | GET | |
| `/import`, `/import-preview`, `/import/upload`, `/import/upload-archive` | GET/POST | |
| `/switch-user` | GET/POST | S3(V1-3·8·9) |
| 그 밖(UI) | `/`, `/analyze/full`·`race`·`today`, `/home-legacy`, `/v2/`, `/v2/<path>` | `/v2` 는 앱 셸(spa_static 설계) |

## 7. 다음 단계로 넘길 것

| 작업 | 단계 | 내용 |
|---|---|---|
| `/switch-user` v2 이관·SRV-6·uid 규칙(`validate_uid` 를 `src/utils/user_context.py` 에) | S3 | 설계서 §4 6단계. 이제 `user_context.py` 에 `db_path` 가 있어 같은 모듈에 둘 수 있음 |
| MenuDrawer CSV → EXP 링크 | S3 | 설계서 §4 7단계 |
| 비UI 직접 라우트의 위치·처리 | **S3 에서 결정**(V1S-12, 미결정) | 위 목록 |
| **0단계 환경: Flask 설치·표준 테스트 명령(ENV-1)** | S3 0단계 | (제안, 미승인) `.venv/bin/python -m pytest tests/` 를 CLAUDE.md 에 문서화, `docs/install-guide.md`·`docs/setup-termux.md` 의 flask '선택' → 필수(`pip install -r requirements.txt`). 시스템 `python3` 에는 설치하지 않음. 근거: 시스템 python3 로 `pytest tests/` 하면 수집 오류 32건으로 중단 |
| MenuDrawer `AI 코치` quickLink 등 v2→v1 링크 | MENUDRAWER-POST-V1 | V1-5 |
| `views_ai_coach*.py`·`views_training_*`·v1 HTML 삭제 | v1 일몰 | V1-17 |

## 8. 검증

- 환경: `.venv`(flask 3.1.3, pytest 9.1.1), 시스템 python3 3.13. 지정 venv 는 이 샌드박스에 없음.
- 전체 pytest: 기준선(S1 후) `1 failed, 2829 passed, 247 skipped` → S2 후 `1 failed, 2822 passed, 242 skipped`. 차이 = 삭제한 suggestions 테스트 12개(통과 7·skip 5). 실패 1건은 기준선과 같은 `test_plan_creation`(BACKLOG `TEST-PLAN-CREATION-DATE`).
- `check_docs.py`: 오류 0 / 경고 63(기준선 동일).
- 최종 grep: `src/web/` 밖에서 `src.web.` 를 쓰는 곳은 `src/serve.py`(앱 팩토리 `create_app`) 1곳뿐. 옛 경로 문자열(`src.web.bg_sync` 등)은 코드·테스트에서 0건(docstring 이관 설명 1곳 제외).
- `create_app()` 기동 및 `/ai-coach` 404 확인(테스트 클라이언트). 프런트 검사: 변경 없음.
