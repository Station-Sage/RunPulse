# 사용자 데이터 전체 내보내기 (NEW-11) 설계 초안 — 2026-10-11

> 근거: decisions-table.md NEW-10·11·12, EXP-1~19(2026-10-11 결정), TXT-1(문구), SRV-1/4/8, SEC-1~9, ERR-1~7, TZ-1, A11Y. EXP 결정 반영본이며 §5 의 열린 질문은 미확정. 코드 변경 없음.
> 변경 이력: 2026-10-11 3차 동기화 — EXP-18(고정 여유)·EXP-19(삭제 안내 항상 표시) 반영, EXP-7 문구는 TXT-1 로 구현 단계 후보 제시.

## 1. 근본 원인 (현황, 코드로 확인한 것만)

| 경로 | 위치 | 하는 일 | 한계 |
|------|------|---------|------|
| v1 활동 CSV | `src/web/views_export.py` (`/activities/export.csv`, 99줄) | 활동 목록 CSV 동기 응답 | 일몰 예정(V1-1), 설계 대상 아님 |
| v2 빠른 CSV 3종 | `src/services/export_service.py` `quick_export` + `POST /api/v1/data/export` kind=quick_* | 활동·웰니스·부하 CSV 동기 스트림 | from/to 범위만 |
| v2 아카이브 잡 | 같은 파일 `start_archive`→`_run`→`build_archive` (스레드), 원장 `sync_jobs(service='export')` | `data/users/<uid>/exports/<job>.zip`, 7일 만료(`EXPIRE_DAYS`) | 아래 결함 |
| 이력·다운로드 | `src/api/routes_data_export.py` `GET /data/exports`, `GET /data/exports/<id>/download` (`send_file`) | 이력·재다운로드 | 반복 다운로드(EXP-9 로 유지), no-store 없음 |
| v2 화면 | `frontend/src/routes/data/export/+page.svelte` (145줄) | 빠른 CSV·아카이브 버튼·이력 | 범위 선택 없음 |
| 월별 아카이브 | `src/services/archive_service.py` | 월별 활동 집계 조회(내보내기 아님) | 범위 밖 |

현재 아카이브 결함(설계가 필요한 이유):
1. `_ARCHIVE_TABLES = (activity_summaries, daily_wellness, metric_store)` + `source_payloads`(소스별 jsonl)만 담는다. 계획·목표·체크인·코치 대화·설정·(예정)에피소드·대회 캘린더가 없다 → "전체"가 아니다.
2. 테이블 CSV는 `SELECT *` 라 from/to 범위가 적용되지 않는다(빠른 CSV에만 적용). manifest 의 range 와 실제 내용이 어긋난다.
3. 포함 기준이 "테이블명 나열"이라 새 테이블(예: 토큰 컬럼 보유)이 들어올 때 비밀 제외를 보장하는 장치가 없다(허용 목록·열 검사 없음).
4. 만료는 `job_view` 판정뿐이고 zip 파일 삭제가 없다(디스크 잔존, 질병 정보 포함 시 문제가 커짐). 보관 기간도 7일로 EXP-1(24시간)과 다르다.
5. 다운로드 응답에 `Cache-Control: no-store`·`X-Content-Type-Options` 명시 없음, 감사 기록 없음(누가 언제 받았는지).
6. manifest `created_at` 이 `datetime.now().isoformat()` — 오프셋 없음(TZ-1 위반).

사용자 데이터 위치: `data/users/<uid>/running.db`(get_db_path), `data/users/<uid>/sync_jobs.db`(`sync_jobs._jobs_db_path`, 사용자별), `data/users/<uid>/exports/`. 자격 증명은 `config.json` 의 `enc:` 필드(`src/utils/credential_store.py`) — DB 밖.

DB 테이블(코드 `CREATE TABLE` 기준, SCHEMA_VERSION=36) 분류:

| 분류 | 테이블 |
|------|--------|
| 활동 | activity_summaries, activity_laps, activity_best_efforts, activity_exercise_sets, activity_streams, activity_stream_meta, activity_groups, activity_feedback, gear, weather_cache |
| 지표·예측 | metric_store, daily_wellness, prediction_snapshots, milestones, race_results |
| 계획·목표 | goals, planned_workouts, plan_adjustments, plan_progression, plan_replans, user_training_prefs, session_outcomes |
| 체크인 | user_inputs |
| 코치 | chat_threads, chat_messages, ai_feedback |
| 프로필·설정 | athlete_profile, athlete_stats, user_settings, coach_consent |
| 원본 | source_payloads |
| **항상 제외(비밀·내부)** | mcp_tokens(token_hash), calendar_feeds(token_hash, token_enc), mcp_audit, sync_gates, ai_cache, caldav_pushes, sync_jobs, config.json 전체 |
| 예정(v38, 다른 묶음) | context_episodes(adjustment-new-signals.md), race_calendar(race-calendar.md) |

## 2. 설계안

### 2.1 범위 선택 = 그룹 허용 목록 (서버가 유일한 정의)
신규 `src/services/export_groups.py` 에 `EXPORT_GROUPS: dict[str, GroupDef]` — 그룹 키 → (테이블, 날짜 열, 형식, 기본 체크, 민감 여부). **목록에 없는 테이블은 절대 나가지 않는다**(차단 목록이 아닌 허용 목록).

| 그룹 키 | 화면 라벨 후보 | 테이블 | 날짜 필터 열 | 기본 |
|---------|---------------|--------|-------------|------|
| activities | 활동 | activity_summaries·laps·best_efforts·exercise_sets·groups·feedback·gear | start_time | **체크**(EXP-2) |
| streams | 활동 상세 기록(용량 큼) | activity_streams·stream_meta | 부모 활동 | **해제**(EXP-3) |
| metrics | 지표·웰니스 | metric_store·daily_wellness·prediction_snapshots·milestones | date/scope 날짜 | **체크**(EXP-2) |
| plans | 목표·훈련 계획 | goals·planned_workouts·plan_adjustments·plan_progression·plan_replans·user_training_prefs·session_outcomes | date | 해제(EXP-2) |
| checkins | 컨디션 체크인 | user_inputs | date | 해제(EXP-2) |
| episodes | 질병·여행·고도 기록 | context_episodes(dismissed 는 하위 체크박스, EXP-10) | start_date | **체크**(EXP-15), dismissed 하위 해제 |
| races | 대회 캘린더 | race_calendar·race_results | race_date | **체크**(EXP-15) |
| coach | 코치 대화 | chat_threads·chat_messages·ai_feedback | created_at | 해제(EXP-4, 포함 가능) |
| profile | 프로필·설정 | athlete_profile·athlete_stats·user_settings·coach_consent | 없음 | 해제(EXP-2) |
| raw | 원본 수집 데이터 | source_payloads | entity_date | **체크**(EXP-5, 현행 포함) |

- 기본 체크는 activities·metrics·raw·episodes·races **5개**(EXP-2·5·15, NEW-11 '기본 포함'과 일치). streams·coach·plans·checkins·profile 은 해제 상태로 노출. "전체 내보내기"가 아니라는 오해를 줄이도록 해제 그룹도 목록에 항상 보인다(누락 오해는 EXP-2 결정 시 인지된 단점).
- episodes 하위 체크박스 "해제한(dismissed) 기록도 포함"(EXP-10): 체크 시 전 status, 해제 시 dismissed 제외. 하위 체크박스 기본값은 **해제**(EXP-15). manifest 그룹 항목에 `include_dismissed` 기록.

- v38 미적용 DB: episodes/races 그룹은 테이블 존재 확인 후 없으면 manifest 에 `"skipped": "not_migrated"` 로 기록(실패 아님). 화면은 그룹을 계속 보여주되 "기록 없음" 표시.
- 비밀 2중 방어: (1) 열 거부 규칙 — 열 이름에 `token|secret|password|api_key|cookie` 포함 시 제외, (2) 값 검사 — 문자열이 `enc:` 로 시작하면 행 기록 대신 잡 실패(`EXPORT_SECRET_DETECTED`)로 중단. 테스트가 생성 zip 전체를 스캔해 보장.
- 날짜 범위: 그룹마다 날짜 열로 from/to 를 적용(현재 `SELECT *` 결함 수정). 날짜 열 없는 그룹(profile)은 항상 전체.

### 2.2 형식 — zip 안 JSON+CSV 혼합(현 구조 확장)
```
manifest.json      # format_version, schema_version, created_at(오프셋 포함 ISO), range, groups[{key, tables, row_counts, skipped}], sensitive_groups
README.txt         # 각 파일 설명 + 건강 정보 공유 주의(문구 미확정, EXP-7 → TXT-1)
tables/<table>.csv # 표 형태(활동·지표·계획·체크인·대회)
json/<table>.json  # 중첩 구조(context_episodes.detail_json, chat_messages, user_settings)
csv/*.csv          # 기존 빠른 CSV 3종(사람용)
raw_payloads/<src>.jsonl
```
- 시각: 저장값 그대로 내보낸다. 활동 `start_time` 은 현지 벽시계(TZ-1·TZ-2 결정 따름), 잡 메타·`created_at` 류 생성 시각은 `datetime.now().astimezone().isoformat()`. manifest 에 열별 시각 의미(`local_wall` / `offset_iso` / `utc_naive`)를 적는다.
- 재가져오기: 이번 범위는 **내보내기만**, manifest 에 `format_version` 만 둔다. 전체 import 는 로드맵(`LATER.md` 등록, EXP-6) — 테이블 단위 원형 보존으로 여지를 남긴다.
- 원본 payload(raw)는 현행대로 포함(EXP-5). 외부 계정 프로필 정보가 들어갈 수 있음을 README 에 적는다.

### 2.3 생성 방식 — 기존 백그라운드 잡 재사용
- `POST /api/v1/data/export {kind:"archive", groups:[...], include_dismissed, from, to}` → 202 + job_id. 같은 사용자 동시 1건(`get_active_job`, 기존 409 유지).
- 입력 검증(SRV-4): `groups` 는 리스트·중복 제거·허용 키만(미지 키 400), 빈 리스트 400, `include_dismissed` 는 bool(episodes 미선택 시 무시), 날짜는 기존 `parse_params`, JSON 아닌 본문 415(SRV-5).
- 크기: **상한 없음, 디스크 여유 검사만**(EXP-8). 잡 시작 전 `shutil.disk_usage(exports_dir)` 여유 확인, 쓰는 중에도 테이블 경계마다 재확인. 부족하면 **안전한 실패만**(EXP-13) — 쓰기 중단·부분 zip 삭제·원장 `failed`·`EXPORT_DISK_FULL`, 다른 사용자 데이터·DB 는 건드리지 않는다. 그룹 자동 제외 후 계속하는 대체 동작은 두지 않는다. 필요 여유량은 **고정 여유**(EXP-18) — 상수 `EXPORT_MIN_FREE_BYTES`(예 1GB, 값은 구현 시 확인)를 `export_service` 에 두고 시작 전·테이블 경계 재확인 모두 같은 값과 비교한다(선택 그룹 크기·DB 크기 추정 없음). 스트림은 테이블 단위 커서 반복(`fetchmany`)으로 메모리 상한 유지.
- 실패: 원장 `status=failed, error_code`(EXPORT_FAILED/DISK_FULL/SECRET_DETECTED), 부분 zip 삭제. 화면은 공통 오류 컴포넌트(ERR) + "다시 만들기"(수동, ERR-3 결정 따름).
- 보관·만료: **24시간**(EXP-1, 현행 `EXPIRE_DAYS=7` → `EXPIRE_HOURS=24`). 만료는 판정만이 아니라 **zip 파일 삭제 잡**으로 보장한다 — `purge_expired(user_id)` 를 (1) 이력 조회·새 잡 시작 시, (2) 사용자 방문과 무관한 주기 정리 잡에서 전 사용자 대상으로 호출. 원장 행은 남기고 `status=expired`. 주기 잡은 **앱 시작 시 띄우는 별도 경량 데몬 스레드**(EXP-14) — `auto_sync` 루프와 분리되어 자동 동기화가 꺼져 있어도 동작한다. `src/web/app.py` 의 `auto_sync` 시작 지점 옆에서 시작하고, 시작 실패는 경고 로그만 남긴다. 주기 간격은 구현 시 정한다(만료 24시간 대비 짧게).
- 에피소드 단건 삭제(NEW-10)와의 관계(EXP-11): 이미 생성된 zip 은 건드리지 않고 24시간 만료로 소멸. 삭제·익명화(NEW-10 추가 결정: `signals_json` 질병 항목 제거, `source='illness'`→`'readiness'`) 이후 새로 만드는 zip 에만 반영된다. 삭제 시 화면에 **"기존 내보내기 파일에는 최대 24시간 남아 있음" 안내**(EXP-16)를 표시한다 — 삭제 UI 는 adjustment-new-signals.md 소관이므로 이 설계는 문구 요구만 전달한다. 안내는 만료 전 내보내기 zip 유무와 무관하게 **항상 표시**한다(EXP-19) — 삭제 화면이 내보내기 이력을 조회할 필요 없음.

### 2.4 보안
- 인증 사용자 본인만: 경로는 `exports_dir(get_current_user_id())`, 잡 조회는 사용자별 `sync_jobs.db` → 타 사용자 job_id 는 NOT_FOUND. job_id 는 UUID 형식 검사 후 사용(경로 조작 차단).
- 다운로드 URL 은 현행 유지(EXP-9): 세션 인증 + 만료(24시간)까지 반복 다운로드. 다운로드가 접근 권한 상태를 바꾸지 않으므로 SRV-1 Origin 관문은 현행대로 POST 에만 적용, GET 변경 없음(아래 `download_count` 는 감사용 기록일 뿐 권한 판정에 쓰지 않는다).
- 다운로드 응답 헤더: `Content-Disposition: attachment; filename="runpulse_export_<YYYY-MM-DD>.zip"`(ASCII 고정), `Content-Type: application/zip`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`(SEC 공통 헤더가 이미 붙이면 중복 없이).
- 감사 기록: 사용자별 sync_jobs 원장 `result_json` 에 `groups`, `download_count`, `last_downloaded_at`(오프셋 포함) 추가 — 새 테이블 없음. 서버 로그 1줄(job_id·groups·크기, 내용 없음).
- 민감 표시: episodes·coach 를 `sensitive_groups` 로 manifest·이력에 표시.
- 질병 확인(EXP-7·12): **episodes 그룹을 선택하면 항상** 생성 **전** 확인 단계 1회(확인 → POST, 취소 → 요청 없음). 선택 범위에 질병 에피소드가 실제 있는지는 조회하지 않는다(서버 사전 조회 없음). 상시 안내문은 두지 않는다. 문구는 TXT-1 에 따라 구현 단계에서 후보 제시 후 사용자 확정(§5). 확인은 화면 단계이며 서버 POST 계약은 바꾸지 않는다.
- NEW-12 와의 관계(EXP-17): NEW-12 의 질병 별도 동의는 **AI 코치 전송** 범위이며 내보내기에 **영향 없음** — 미동의·철회 상태여도 episodes 기본 체크·확인 단계·포함 내용은 같다. 로컬 내보내기의 민감 정보 처리는 EXP-7·12 확인으로 다룬다. 내보낸 `chat_messages` 는 저장된 대화 원문이라 사용자가 직접 쓴 질병 언급이 있을 수 있다(EXP-4 기본 해제 근거). 질병 동의 저장소(위치 미정, adjustment-new-signals.md)가 DB 테이블로 생기면 S1 분류 테스트가 그룹 지정을 강제한다.

### 2.5 화면 (`/data/export`, 375px 기준)
- 보이는 `h1`("데이터 내보내기"), 그룹 체크박스는 `<fieldset><legend>` + 라벨 클릭 영역 44px 이상, 각 그룹 옆 짧은 설명·민감 표시. 초기 상태는 activities·metrics·raw·episodes·races 5개 체크, dismissed 하위 해제(EXP-2·3·4·5·15). episodes 아래 "해제한 기록도 포함" 하위 체크박스(EXP-10, episodes 미선택 시 비활성). "전체 선택/해제" 1개. 기간 선택은 기존 from/to 재사용.
- 질병 확인 단계(EXP-7·12): 기본 상태(episodes 체크, EXP-15)에서는 생성할 때마다 확인이 뜬다. 생성 버튼 → episodes 선택 시 확인 대화상자(포커스 이동·Esc 취소·키보드 조작) → 확인 시 POST.
- 이력·완료 안내에 "24시간 후 자동 삭제" 와 만료 시각(오프셋 포함) 표시.
- 진행: 이력 목록의 상태(queued/running/done/failed/expired) 폴링 유지, `aria-live="polite"`.
- 그룹 상태 계산은 순수 함수 `frontend/src/lib/exportScope.ts` 로 분리해 단위 테스트.

## 3. 변경 파일 표

| 파일 | 구분 | 내용 | 예상 줄 |
|------|------|------|--------|
| `src/services/export_groups.py` | 신규 | GroupDef·EXPORT_GROUPS(기본 체크 activities·metrics·raw·episodes·races, dismissed 기본 해제)·열 거부 규칙·`enc:` 검사·테이블 존재 확인·episodes dismissed 필터 | ~130 |
| `src/services/export_archive.py` | 신규 | `build_archive(conn, path, groups, frm, to, include_dismissed, space_check)` — 현 build_archive 이동·확장, manifest(format_version)/README, 디스크 여유 재확인 | ~180 |
| `src/services/export_service.py` | 수정 | parse_params 에 groups·include_dismissed, start_archive 인자, `EXPIRE_DAYS=7`→`EXPIRE_HOURS=24`, 시작 전 디스크 여유 검사(고정 `EXPORT_MIN_FREE_BYTES`, EXP-18), purge_expired(파일 삭제), 다운로드 기록, created_at 오프셋. build_archive 제거로 300줄 이하 유지 | 230→~230 |
| `src/web/export_purge.py`(신규 경량 스레드, EXP-14), `src/web/app.py`(시작 호출) | 신규/수정 | 앱 시작 시 데몬 스레드, 주기마다 전 사용자 `purge_expired`, 실패 시 로그만 | ~40 / +4 |
| `src/api/routes_data_export.py` | 수정 | groups·include_dismissed 전달, 415, job_id 형식 검사, no-store 헤더, 다운로드 기록(Origin 관문 변경 없음) | 56→~85 |
| `frontend/src/lib/exportScope.ts` | 신규 | 그룹 메타·기본 체크·질병 확인 필요 여부 판정(episodes 선택 = 확인, EXP-12)·요청 본문 생성 | ~60 |
| `frontend/src/lib/components/ExportScopeForm.svelte` | 신규 | fieldset 체크박스 그룹·dismissed 하위 체크박스·민감 표시 | ~130 |
| `frontend/src/lib/components/ExportConfirmDialog.svelte` | 신규 | 질병 포함 생성 전 확인 1회(문구 자리만, EXP-7·TXT-1) | ~60 |
| `frontend/src/routes/data/export/+page.svelte` | 수정 | 폼·확인 단계 삽입, 공통 오류 컴포넌트, 24시간 만료 안내 | 145→~180 |
| `frontend/src/lib/types/index.ts` | 수정 | ExportGroup·manifest 타입 | +15 |
| tests: `test_export_groups.py`, `test_export_archive.py`, `test_export_service.py`(확장), `test_routes_data_export.py`(확장), 프론트 `exportScope.test.ts`, `ExportScopeForm.test.ts`, `ExportConfirmDialog.test.ts` | 신규/수정 | 함수마다 ≥1 | ~40개 |
| `LATER.md` | 메인 처리 | 전체 import 로드맵 항목 등록(EXP-6) — 이 설계 구현 범위 아님 | — |

## 4. 단계·검증
1. **S1 그룹 허용 목록**: export_groups.py. 검증 — db_setup·db_schema_v* 의 모든 `CREATE TABLE` 이 "그룹 소속 또는 항상 제외" 중 하나로 분류됐는지 검사하는 테스트(새 테이블 추가 시 자동 실패 → 누락 방지). 기본 체크 집합이 정확히 {activities, metrics, raw, episodes, races} 이고 `include_dismissed` 기본 false 인지 검사(EXP-15). check_docs.py 검사 후보로도 등록 검토.
2. **S2 아카이브 확장**: export_archive.py. 검증 — 임시 DB에 `enc:` 값·`token_hash` 열·calendar_feeds 행을 심고 zip 전체 바이트에서 미검출; from/to 가 각 테이블에 적용; v38 미적용 DB에서 episodes skipped; `include_dismissed` false 면 dismissed 행 없음·true 면 있음; 디스크 여유 부족(가짜 `space_check`) 시 부분 파일 삭제·`EXPORT_DISK_FULL`·streams 포함 요청도 그룹 제외 없이 실패(EXP-13); 여유가 `EXPORT_MIN_FREE_BYTES` 바로 아래면 실패·이상이면 진행(선택 그룹과 무관한 고정 기준, EXP-18); manifest `format_version`·created_at 오프셋 포함.
3. **S3 API·만료**: 미지 그룹 400, 빈 그룹 400, `include_dismissed` 비bool 400, 비JSON 415, 타 사용자 job_id 404, 생성 24시간 경과 시 410 + zip 파일 실제 삭제됨(시계 주입), 주기 정리 스레드가 자동 동기화 꺼짐 상태에서도 방문 없는 사용자의 만료 zip 을 삭제(EXP-14), 만료 전에는 반복 다운로드 200(EXP-9), 다운로드 헤더(no-store·attachment), Origin 없는 POST 는 SRV-1·SRV-8 모드대로·다운로드 GET 은 현행과 동일. 에피소드 단건 삭제 후 기존 zip 그대로·새 zip 에는 미포함(EXP-11). 24시간 안내(EXP-16)는 만료 전 zip 이 없어도 표시(EXP-19) — 삭제 UI 테스트는 adjustment-new-signals.md 소관이므로 요구 사항으로 전달. NEW-12 미동의·철회 사용자도 episodes 포함 결과 동일(EXP-17).
4. **S4 화면**: 375px 브라우저 확인(초기 체크 5개·dismissed 해제, 체크박스 44px, 가로 스크롤 없음, h1 보임, 키보드만으로 선택·생성·다운로드), episodes 선택 시 질병 기록 유무와 무관하게 확인 단계 1회·취소 시 요청 없음·episodes 해제 시 확인 없이 생성(EXP-12), dismissed 하위 체크박스 비활성 전환, 24시간 만료 안내, 실패 시 공통 오류·재시도, 스크린리더 상태 알림.
5. 전체 `python3 -m pytest tests/`, 프론트 테스트, `python3 scripts/check_docs.py`. 신규 ADR 필요 여부(비밀 허용 목록 원칙) 메인 판단.

호환성: 기존 kind=archive 요청에 groups 가 없으면 현재와 같은 그룹(activities·metrics·raw + 빠른 CSV)으로 처리해 기존 화면/테스트 무회귀(화면 기본 체크는 EXP-15 로 episodes·races 가 추가되지만 groups 없는 구 요청은 현행 3그룹 유지). 단 보관 기간 7일→24시간은 의도된 동작 변경이므로 기존 만료 테스트는 갱신한다. 스키마 변경 없음(v38 은 다른 묶음 소관, 이 설계는 존재 여부만 검사).

대안:
- **A(추천) zip JSON+CSV 그룹 허용 목록** — 기존 잡·이력·화면 재사용, 비밀 제외를 코드로 보장, 스프레드시트로 열람 가능. 단점: 재가져오기는 별도 구현 필요.
- B SQLite 사본(`VACUUM INTO` 후 제외 테이블 DROP) — 재가져오기 쉽고 구현 짧음. 단점: 삭제 누락 시 비밀 유출(차단 목록 방식), free page 잔존 가능, 내부 스키마가 사용자 계약이 됨, 그룹·기간 필터가 번거로움.

## 5. 결정 필요
EXP-1~19 결정 완료(decisions-table.md 표 참조). 아래는 남은 열린 질문이다.
- **EXP-7 확인 문구**(TXT-1, 미결정): 생성 전 확인 대화상자·README 의 건강 정보 주의 문구. 후보 문구는 구현 단계에서 제시, 사용자 확정.
- 해소(EXP-12) 확인 발동 조건 · 해소(EXP-13) 부족 시 동작 · 해소(EXP-14) 정리 잡 위치 · 해소(EXP-15) episodes·races·dismissed 기본값 · 해소(EXP-17) NEW-12 연동.
- 해소(EXP-18) 디스크 여유 기준 · 해소(EXP-19) 삭제 안내 항상 표시. 남은 확인: 고정 여유 실제 값(예 1GB)은 구현 시 확인.

## 6. 범위 밖 메모
- `config.json` 자격 증명·`enc:` 키 백업/이관은 이 기능에서 다루지 않는다(별도 계정 이전 설계).
- 질병 별도 동의(NEW-12)의 동의 UI·저장은 adjustment-new-signals.md 소관. 내보내기와는 연동하지 않는다(EXP-17).
- 전체 import 구현은 LATER(EXP-6). 에피소드 단건 삭제·익명화(NEW-10) 구현도 adjustment-new-signals.md 소관이며 이 설계는 기존 zip 을 건드리지 않는다(EXP-11).
- `archive_service.py` 의 월별 아카이브 조회는 이름만 유사, 무관.
- 계정 삭제(전체 데이터 삭제) 기능과 "삭제 전 내보내기" 연결은 LATER 후보.
