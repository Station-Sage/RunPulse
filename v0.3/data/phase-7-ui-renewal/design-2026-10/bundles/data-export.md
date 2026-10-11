# 사용자 데이터 전체 내보내기 (NEW-11) 설계 초안 — 2026-10-11

> 근거: decisions-table.md NEW-10·11·12, SRV-1/4/8, SEC-1~9, ERR-1~7, TZ-1, A11Y. 설계 초안이며 확정이 아니다. 코드 변경 없음.

## 1. 근본 원인 (현황, 코드로 확인한 것만)

| 경로 | 위치 | 하는 일 | 한계 |
|------|------|---------|------|
| v1 활동 CSV | `src/web/views_export.py` (`/activities/export.csv`, 99줄) | 활동 목록 CSV 동기 응답 | v1 제거 예정. 활동만 |
| v2 빠른 CSV 3종 | `src/services/export_service.py` `quick_export` + `POST /api/v1/data/export` kind=quick_* | 활동·웰니스·부하 CSV 동기 스트림 | from/to 범위만 |
| v2 아카이브 잡 | 같은 파일 `start_archive`→`_run`→`build_archive` (스레드), 원장 `sync_jobs(service='export')` | `data/users/<uid>/exports/<job>.zip`, 7일 만료(`EXPIRE_DAYS`) | 아래 결함 |
| 이력·다운로드 | `src/api/routes_data_export.py` `GET /data/exports`, `GET /data/exports/<id>/download` (`send_file`) | 이력·재다운로드 | 일회성 아님, no-store 없음 |
| v2 화면 | `frontend/src/routes/data/export/+page.svelte` (145줄) | 빠른 CSV·아카이브 버튼·이력 | 범위 선택 없음 |
| 월별 아카이브 | `src/services/archive_service.py` | 월별 활동 집계 조회(내보내기 아님) | 범위 밖 |

현재 아카이브 결함(설계가 필요한 이유):
1. `_ARCHIVE_TABLES = (activity_summaries, daily_wellness, metric_store)` + `source_payloads`(소스별 jsonl)만 담는다. 계획·목표·체크인·코치 대화·설정·(예정)에피소드·대회 캘린더가 없다 → "전체"가 아니다.
2. 테이블 CSV는 `SELECT *` 라 from/to 범위가 적용되지 않는다(빠른 CSV에만 적용). manifest 의 range 와 실제 내용이 어긋난다.
3. 포함 기준이 "테이블명 나열"이라 새 테이블(예: 토큰 컬럼 보유)이 들어올 때 비밀 제외를 보장하는 장치가 없다(허용 목록·열 검사 없음).
4. 만료는 `job_view` 판정뿐이고 zip 파일 삭제가 없다(디스크 잔존, 질병 정보 포함 시 문제가 커짐).
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
| activities | 활동 | activity_summaries·laps·best_efforts·exercise_sets·groups·feedback·gear | start_time | 결정 EXP-2 |
| streams | 활동 상세 기록(용량 큼) | activity_streams·stream_meta | 부모 활동 | EXP-3 |
| metrics | 지표·웰니스 | metric_store·daily_wellness·prediction_snapshots·milestones | date/scope 날짜 | EXP-2 |
| plans | 목표·훈련 계획 | goals·planned_workouts·plan_adjustments·plan_progression·plan_replans·user_training_prefs·session_outcomes | date | EXP-2 |
| checkins | 컨디션 체크인 | user_inputs | date | EXP-2 |
| episodes | 질병·여행·고도 기록 | context_episodes(전 status) | start_date | **포함(NEW-11 확정)** |
| races | 대회 캘린더 | race_calendar·race_results | race_date | **포함(NEW-11 확정)** |
| coach | 코치 대화 | chat_threads·chat_messages·ai_feedback | created_at | EXP-4 |
| profile | 프로필·설정 | athlete_profile·athlete_stats·user_settings·coach_consent | 없음 | EXP-2 |
| raw | 원본 수집 데이터 | source_payloads | entity_date | EXP-5 |

- v38 미적용 DB: episodes/races 그룹은 테이블 존재 확인 후 없으면 manifest 에 `"skipped": "not_migrated"` 로 기록(실패 아님). 화면은 그룹을 계속 보여주되 "기록 없음" 표시.
- 비밀 2중 방어: (1) 열 거부 규칙 — 열 이름에 `token|secret|password|api_key|cookie` 포함 시 제외, (2) 값 검사 — 문자열이 `enc:` 로 시작하면 행 기록 대신 잡 실패(`EXPORT_SECRET_DETECTED`)로 중단. 테스트가 생성 zip 전체를 스캔해 보장.
- 날짜 범위: 그룹마다 날짜 열로 from/to 를 적용(현재 `SELECT *` 결함 수정). 날짜 열 없는 그룹(profile)은 항상 전체.

### 2.2 형식 — zip 안 JSON+CSV 혼합(현 구조 확장)
```
manifest.json      # format_version, schema_version, created_at(오프셋 포함 ISO), range, groups[{key, tables, row_counts, skipped}], sensitive_groups
README.txt         # 각 파일 설명 + 건강 정보 공유 주의(문구는 EXP-7)
tables/<table>.csv # 표 형태(활동·지표·계획·체크인·대회)
json/<table>.json  # 중첩 구조(context_episodes.detail_json, chat_messages, user_settings)
csv/*.csv          # 기존 빠른 CSV 3종(사람용)
raw_payloads/<src>.jsonl
```
- 시각: 저장값 그대로 내보낸다. 활동 `start_time` 은 현지 벽시계(TZ-1·TZ-2 결정 따름), 잡 메타·`created_at` 류 생성 시각은 `datetime.now().astimezone().isoformat()`. manifest 에 열별 시각 의미(`local_wall` / `offset_iso` / `utc_naive`)를 적는다.
- 재가져오기: 이번 범위는 **내보내기만**. `format_version` 과 테이블 단위 원형 보존으로 향후 import 여지를 남김(EXP-6).

### 2.3 생성 방식 — 기존 백그라운드 잡 재사용
- `POST /api/v1/data/export {kind:"archive", groups:[...], from, to}` → 202 + job_id. 같은 사용자 동시 1건(`get_active_job`, 기존 409 유지).
- 입력 검증(SRV-4): `groups` 는 리스트·중복 제거·허용 키만(미지 키 400), 빈 리스트 400, 날짜는 기존 `parse_params`, JSON 아닌 본문 415(SRV-5).
- 크기 상한: 쓰는 중 누적 바이트가 상한(EXP-8) 초과 시 중단·파일 삭제·`EXPORT_TOO_LARGE`. 스트림은 테이블 단위 커서 반복(`fetchmany`)으로 메모리 상한 유지.
- 실패: 원장 `status=failed, error_code`(EXPORT_FAILED/TOO_LARGE/SECRET_DETECTED), 부분 zip 삭제. 화면은 공통 오류 컴포넌트(ERR) + "다시 만들기"(수동, ERR-3 결정 따름).
- 만료 정리: `purge_expired(user_id)` — 이력 조회·새 잡 시작 시 만료 zip 삭제(별도 스케줄러 불필요). 보관 기간 값은 EXP-1.

### 2.4 보안
- 인증 사용자 본인만: 경로는 `exports_dir(get_current_user_id())`, 잡 조회는 사용자별 `sync_jobs.db` → 타 사용자 job_id 는 NOT_FOUND. job_id 는 UUID 형식 검사 후 사용(경로 조작 차단).
- SRV-1 Origin 관문: POST 는 관문 적용(쓰기). 다운로드 GET 은 상태 변경이 없으나 EXP-9(일회성) 채택 시 상태를 바꾸므로 관문 적용 여부 함께 결정.
- 다운로드 응답 헤더: `Content-Disposition: attachment; filename="runpulse_export_<YYYY-MM-DD>.zip"`(ASCII 고정), `Content-Type: application/zip`, `Cache-Control: no-store`, `X-Content-Type-Options: nosniff`(SEC 공통 헤더가 이미 붙이면 중복 없이).
- 감사 기록: 사용자별 sync_jobs 원장 `result_json` 에 `groups`, `download_count`, `last_downloaded_at`(오프셋 포함) 추가 — 새 테이블 없음. 서버 로그 1줄(job_id·groups·크기, 내용 없음).
- 민감 표시: episodes·coach 를 `sensitive_groups` 로 manifest·이력에 표시. 질병 포함 시 생성 전 안내 1회(EXP-7).

### 2.5 화면 (`/data/export`, 375px 기준)
- 보이는 `h1`("데이터 내보내기"), 그룹 체크박스는 `<fieldset><legend>` + 라벨 클릭 영역 44px 이상, 각 그룹 옆 짧은 설명·민감 표시. "전체 선택/해제" 1개. 기간 선택은 기존 from/to 재사용.
- 진행: 이력 목록의 상태(queued/running/done/failed/expired) 폴링 유지, `aria-live="polite"`.
- 그룹 상태 계산은 순수 함수 `frontend/src/lib/exportScope.ts` 로 분리해 단위 테스트.

## 3. 변경 파일 표

| 파일 | 구분 | 내용 | 예상 줄 |
|------|------|------|--------|
| `src/services/export_groups.py` | 신규 | GroupDef·EXPORT_GROUPS·열 거부 규칙·`enc:` 검사·테이블 존재 확인 | ~120 |
| `src/services/export_archive.py` | 신규 | `build_archive(conn, path, groups, frm, to, max_bytes)` — 현 build_archive 이동·확장, manifest/README | ~170 |
| `src/services/export_service.py` | 수정 | parse_params 에 groups, start_archive 인자, purge_expired, 다운로드 기록, created_at 오프셋. build_archive 제거로 300줄 이하 유지 | 230→~220 |
| `src/api/routes_data_export.py` | 수정 | groups 전달, 415, job_id 형식 검사, no-store 헤더, 다운로드 기록 | 56→~85 |
| `frontend/src/lib/exportScope.ts` | 신규 | 그룹 메타·기본 체크·요청 본문 생성 | ~50 |
| `frontend/src/lib/components/ExportScopeForm.svelte` | 신규 | fieldset 체크박스 그룹·민감 안내 | ~120 |
| `frontend/src/routes/data/export/+page.svelte` | 수정 | 폼 삽입, 공통 오류 컴포넌트 | 145→~170 |
| `frontend/src/lib/types/index.ts` | 수정 | ExportGroup·manifest 타입 | +15 |
| `src/web/views_export.py` | 유지 | v1 제거 시 함께 삭제(이번 변경 없음) | 0 |
| tests: `test_export_groups.py`, `test_export_archive.py`, `test_export_service.py`(확장), `test_routes_data_export.py`(확장), 프론트 `exportScope.test.ts`, `ExportScopeForm.test.ts` | 신규/수정 | 함수마다 ≥1 | ~35개 |

## 4. 단계·검증
1. **S1 그룹 허용 목록**: export_groups.py. 검증 — db_setup·db_schema_v* 의 모든 `CREATE TABLE` 이 "그룹 소속 또는 항상 제외" 중 하나로 분류됐는지 검사하는 테스트(새 테이블 추가 시 자동 실패 → 누락 방지). check_docs.py 검사 후보로도 등록 검토.
2. **S2 아카이브 확장**: export_archive.py. 검증 — 임시 DB에 `enc:` 값·`token_hash` 열·calendar_feeds 행을 심고 zip 전체 바이트에서 미검출; from/to 가 각 테이블에 적용; v38 미적용 DB에서 episodes skipped; 상한 초과 시 파일 삭제·TOO_LARGE; manifest created_at 오프셋 포함.
3. **S3 API**: 미지 그룹 400, 빈 그룹 400, 비JSON 415, 타 사용자 job_id 404, 만료 410 + 파일 삭제됨, 다운로드 헤더(no-store·attachment), Origin 없는 POST 는 SRV-1·SRV-8 모드대로.
4. **S4 화면**: 375px 브라우저 확인(체크박스 44px, 가로 스크롤 없음, h1 보임, 키보드만으로 선택·생성·다운로드), 실패 시 공통 오류·재시도, 스크린리더 상태 알림.
5. 전체 `python3 -m pytest tests/`, 프론트 테스트, `python3 scripts/check_docs.py`. 신규 ADR 필요 여부(비밀 허용 목록 원칙) 메인 판단.

호환성: 기존 kind=archive 요청에 groups 가 없으면 현재와 같은 그룹(activities·metrics·raw + 빠른 CSV)으로 처리해 기존 화면/테스트 무회귀. v1 `views_export.py` 는 의존하지 않음. 스키마 변경 없음(v38 은 다른 묶음 소관, 이 설계는 존재 여부만 검사).

대안:
- **A(추천) zip JSON+CSV 그룹 허용 목록** — 기존 잡·이력·화면 재사용, 비밀 제외를 코드로 보장, 스프레드시트로 열람 가능. 단점: 재가져오기는 별도 구현 필요.
- B SQLite 사본(`VACUUM INTO` 후 제외 테이블 DROP) — 재가져오기 쉽고 구현 짧음. 단점: 삭제 누락 시 비밀 유출(차단 목록 방식), free page 잔존 가능, 내부 스키마가 사용자 계약이 됨, 그룹·기간 필터가 번거로움.

## 5. 결정 필요
- **EXP-1 생성 파일 보관 기간**: (a) 현행 7일 — 재다운로드 여유, 디스크·노출 기간 김 / (b) 24시간 — 노출 최소, 늦게 받으면 재생성 / (c) 첫 다운로드 후 즉시 삭제 — 가장 안전, 다운로드 실패 시 재생성 필요.
- **EXP-2 일반 그룹 기본 체크**(activities·metrics·plans·checkins·profile): (a) 모두 체크 — "전체 내보내기" 취지 / (b) 활동·지표만 — 파일 작음, 누락 오해 가능.
- **EXP-3 streams 포함 기본값**: (a) 기본 해제 — 크기·시간 절감 / (b) 기본 포함 — 완전한 백업, 수백 MB 가능.
- **EXP-4 코치 대화 포함·기본값**: (a) 포함·기본 체크 / (b) 포함·기본 해제(대화에 질병 언급 가능) / (c) 제외.
- **EXP-5 원본 payload(raw) 포함 기본값**: (a) 포함(현행) — 소스 원형 보존, 외부 계정 프로필 정보 포함 가능 / (b) 기본 해제 / (c) 제외.
- **EXP-6 재가져오기 지원 범위**: (a) 이번엔 없음, format_version 만 / (b) 에피소드·대회 캘린더만 import 지원 / (c) 전체 import 로드맵 등록.
- **EXP-7 민감 정보 안내 방식·문구**: (a) 질병 에피소드 포함 시 생성 전 확인 1회 / (b) 화면 상시 안내문 + README 만 / (c) 둘 다. 문구는 사용자 확정 필요.
- **EXP-8 파일 크기 상한 값**: (a) 500MB / (b) 2GB / (c) 상한 없이 디스크 여유 검사만. 초과 시 동작(실패 vs streams 자동 제외 후 경고).
- **EXP-9 다운로드 URL 성격**: (a) 현행 — 세션 인증 + 만료까지 반복 다운로드 / (b) 일회성 — 다운로드 1회 후 무효(재생성 필요) / (c) 횟수 제한(예 3회). (b)(c)는 GET 이 상태를 바꾸므로 Origin 관문 적용 여부 함께.
- **EXP-10 dismissed 에피소드 포함**: (a) 전 status 포함(원형 보존) / (b) confirmed 만 / (c) 체크박스로 선택.
- **EXP-11 에피소드 단건 삭제(NEW-10)와 기존 생성 파일 관계**: (a) 이미 생성된 zip 은 유지(보관 기간 만료로 소멸) / (b) 에피소드 삭제 시 해당 사용자 미만료 zip 모두 삭제 + 이력에 "무효" 표시.

## 6. 범위 밖 메모
- `config.json` 자격 증명·`enc:` 키 백업/이관은 이 기능에서 다루지 않는다(별도 계정 이전 설계).
- 질병 별도 동의(NEW-12)는 AI 전송 대상이며 로컬 내보내기에는 적용하지 않는 것으로 해석 — 메인 확인 권장.
- `archive_service.py` 의 월별 아카이브 조회는 이름만 유사, 무관.
- v1 `/activities/export.csv` 삭제는 v1 제거 작업에 포함.
- 계정 삭제(전체 데이터 삭제) 기능과 "삭제 전 내보내기" 연결은 LATER 후보.
