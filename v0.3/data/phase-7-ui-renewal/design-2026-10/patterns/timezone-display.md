# 설계: 시간대 표기 (UTC 표기·날짜 절단)

- 대상 ID: C-06 (코치 답변 근거 시트 "계산 시각" 9시간 어긋남), S-17 (Strava 단독 활동 상세 헤더 날짜가 KST 자정 경계에서 틀림)
- 상태: 설계 초안 (구현 전. TZ-1·2·5 결정, TZ-3 부분 결정, D4·D6~D9 결정 필요)
- 관련 ADR: ADR-006 (Strava `start_date_local` 우선 — 활동 시각은 "현지 벽시계"가 기준이라는 기존 결정), ADR-009 (Calculator 무변경, 해당 없음)
- 결정 번호 대응: 본문 D1~D5 = `decisions-table.md`의 TZ-1~TZ-5. D6 이후는 이 문서에서 새로 생긴 결정 필요 항목(아직 표에 없음).

### 변경 이력
- 2026-10-11 TZ-5 결정 반영 (Strava CSV 고정 오프셋 → 활동별 timezone, Strava 연결 무효 시 폴백. 2.2.1 신설, 표·단계·검증·결정 필요 갱신, D6~D9 추가)

## 1. 근본 원인

**RC-1. 시각 문자열의 "의미(시간대)"가 응답 계약에 없고, 프론트가 문자열 패턴으로 추측한다.**
- DB 기록 시각(`metric_store.updated_at` 등 `DEFAULT (datetime('now'))`)은 **시간대 표기 없는 UTC**(`YYYY-MM-DD HH:MM:SS`)다. `coach_evidence.py`가 이를 `computed_at`으로 그대로 내보내고, `answerEvidence.ts`의 `stamp()`는 정규식으로 숫자만 잘라 표시한다 → C-06.
- 같은 문제를 이미 아는 코드가 흩어져 있다. `format.ts`의 `parseDbTimestamp()`(무표기=UTC 간주), `sync_state_service.py`의 `naive_utc → astimezone()` 변환, `wellness_day.py:154`. 즉 변환 규칙이 프론트 1곳·백엔드 2곳에 각각 있고, `stamp()`는 그 어느 것도 쓰지 않는다. 공용 표시 함수가 없어서 새 화면마다 재발한다.

**RC-2. `activity_summaries.start_time`의 시간대 의미가 소스·수집 경로별로 다르다.**
- Garmin `startTimeLocal`, Intervals/Strava API `start_date_local`(ADR-006)은 **현지 벽시계**다. 단 Strava API의 `start_date_local`은 현지 시각인데도 끝에 `Z`가 붙는다(Strava 관례). 반면 `start_date` 폴백, FIT 가져오기(`import_history.py:107`, `+00:00`)는 **진짜 UTC**다. Strava CSV(`strava_csv.py`)는 고정 오프셋(`_LOCAL_UTC_OFFSET`)으로 로컬화해 무표기로 저장한다.
- 결과적으로 `…Z` 접미사만 보고는 "UTC"인지 "Z가 붙은 현지 시각"인지 구분할 수 없다. 프론트 `formatDateShort()`(`/library/[id]/+layout.svelte:55`)는 앞 10자를 자를 뿐이라 진짜 UTC 행에서 날짜가 하루 틀린다 → S-17.
- **주의:** 프론트에서 "`Z`면 KST로 변환"하는 땜질은 Strava API 경로(가짜 `Z`)의 정상 행을 9시간 밀어 오히려 깨뜨린다. 그래서 수정 지점은 프론트가 아니라 저장 계약이어야 한다. 활동 1327이 어느 경로로 들어왔는지(`source_payloads`의 `start_date`/`start_date_local` 대조)는 구현 첫 단계에서 확인한다.

## 2. 설계안 (추천: A안 — 두 종류 시각을 계약으로 분리)

시각을 두 부류로 나누고 각각 단일 규칙을 둔다.

| 부류 | 예 | 저장 규칙 | API 출력 규칙 | 표시 |
|---|---|---|---|---|
| 기록 시각 (instant) | `updated_at`, `created_at`, `computed_at`, 동기화 시각 | 기존 그대로(무표기 UTC) | **오프셋 포함 ISO 8601**로 직렬화(`…+09:00` 또는 `…Z`) | 프론트 공용 함수로 사용자 시간대 변환 |
| 활동 시각 (wall-clock) | `activity_summaries.start_time` | **현지 벽시계, 시간대 접미사 없음**(`YYYY-MM-DDTHH:MM:SS`)으로 정규화 | 그대로 | 변환 없이 앞 10자/시:분 사용 (현재 프론트 동작이 맞아짐) |

### 2.1 백엔드 — 기록 시각 직렬화 단일화
- 신규 `src/utils/timefmt.py`: `to_iso_instant(db_ts: str | None) -> str | None` (무표기=UTC 간주, 표기 있으면 존중, 출력은 오프셋 포함 ISO). `sync_state_service`의 `_naive_utc_to_iso` 계열과 `wellness_day.py:154`를 이 함수로 대체.
- `coach_evidence.py`의 `computed_at` 3곳에 적용. 다른 응답의 `*_at` 필드는 2단계에서 grep(`updated_at|created_at|_at"`)으로 목록화해 순차 적용.

### 2.2 백엔드 — 활동 시각 정규화 (RC-2)
- `src/utils/timefmt.py`에 `to_local_wallclock(local: str | None, utc: str | None, offset_sec: int | None) -> str | None` 추가. 우선순위: 소스가 준 현지 시각(가짜 `Z` 제거) → `utc + offset` → (offset 미상) D2 결정대로 FIT 현지 시각, 없으면 KST 변환. Strava CSV는 2.2.1의 체인을 따른다.
- 적용: `strava_extractor.py:30`, `intervals_extractor.py:34`, `garmin_extractor.py:42`, `import_history.py:107`(FIT: `timestamp`+`local_timestamp` 메시지 활용 가능 여부 확인).
- 기존 행 교정: `source_payloads` 원본에서 재추출하는 1회성 스크립트(`scripts/normalize_start_time.py`, dry-run 기본). dedup 매칭 키에 영향이 있으므로 실행 여부·범위는 결정 필요 D3.

### 2.2.1 Strava CSV — 활동별 timezone (TZ-5 결정 반영)

**확인한 사실 (2026-10-11 grep)**
- 코드 위치는 `src/sync/extractors/`가 아니라 `src/import_export/strava_csv.py`. `_parse_strava_date()`가 CSV `Activity Date`(UTC)에 `_LOCAL_UTC_OFFSET = timedelta(hours=9)`를 더해 무표기로 저장한다. `strava_archive.py`(ZIP 내보내기)도 같은 `_parse_activity_row()`를 쓰므로 영향 범위가 같다.
- **조인 키 있음**: CSV `Activity ID` → `source_id`. API 경로(`strava_extractor.py:25`)도 `source_id = raw["id"]`이고 둘 다 `source='strava'`라서 **같은 `activity_summaries` 행**이다(CSV는 `INSERT OR IGNORE` 후 기존 행이면 `update_changed_fields`).
- **payload timezone**: API 경로는 `source_payloads`에 `entity_type='activity_summary'`(목록 응답 원본)와 `'activity_detail'`을 저장한다(`strava_activity_sync.py`). Strava API 활동 객체에는 `start_date`, `start_date_local`, `timezone`(예: `"(GMT+09:00) Asia/Seoul"`), `utc_offset`(초)이 있고, `timezone`은 metric `timezone_offset`(text)으로도 추출된다(`strava_extractor.py:87`). 실제 DB 행에 `utc_offset`이 채워져 있는지는 단계 1에서 확인한다.
- CSV 경로의 payload는 `entity_type='csv_export'`로 **이미 +9h 된** 파싱값만 저장한다. 원본 UTC·시간대 출처가 남지 않는다(고정 +9라 역산은 가능).
- **잠재 버그**: API로 이미 들어온 행에 CSV를 가져오면 `update_changed_fields`(값이 다르면 덮어씀)와 `_fill_null_fields`(start_time 강제 갱신)가 API의 `start_date_local`을 `UTC+9`로 덮어쓴다. KST 밖 활동은 이때 틀어진다. TZ-5 구현에서 함께 고친다(아래 규칙 4).
- **연결 상태 판정**: `strava_auth.check_strava_connection(config) -> {"ok", "status", "detail"}`. `ok`는 설정·refresh_token 유무만 본다(만료 access_token은 `ok=True`, 자동 갱신 전제). 폐기된 토큰은 갱신/호출 시 401 → `sync_errors.classify_exception()`이 `"auth_expired"`로 분류한다.

**우선순위 체인** — 신규 `src/import_export/strava_tz.py`의 `resolve_strava_start(conn, source_id, utc_naive, *, api=None, fit_local=None) -> tuple[str, str]` (반환: 무접미사 현지 벽시계, `tz_source`)

| 순서 | 출처 | 방법 | `tz_source` |
|---|---|---|---|
| 1 | 저장된 API payload | 같은 `source_id`의 `source_payloads`(`activity_detail` → `activity_summary`)에서 `start_date_local`(가짜 `Z` 제거) 사용. 없으면 `start_date`+`utc_offset` | `api_payload` |
| 2 | Strava API 조회 (연결 유효 시만) | `GET /activities/{id}` 결과를 `upsert_raw_payload(..., "activity_detail", ...)`로 저장한 뒤 1과 같은 규칙. 조회 시점(가져오기 중/백필 작업)은 D7 | `api_fetch` |
| 3 | CSV/ZIP 내 단서 | ZIP 가져오기에 FIT 원본이 있으면 `local_timestamp`(TZ-2 규칙 재사용). 단독 CSV에는 시간대 컬럼이 없으므로 이 단계 없음 | `fit_local` |
| 4 | 폴백 | 고정 오프셋(현재 +9h, TZ-2의 KST 폴백과 같은 값). 값 자체는 D6 | `fallback_fixed` |

규칙:
1. 체인 1·3·4는 네트워크 없이 끝난다. 2만 외부 호출이며 실패(401/403/429/네트워크)는 coding-rules대로 재시도 1회 → 로그 → 폴백으로 계속 진행(가져오기 중단 금지). 401은 그 가져오기 세션에서 `api_unavailable`로 표시하고 남은 행은 2단계를 건너뛴다.
2. CSV payload(`csv_export`)에 `start_date_utc`(CSV 원본 UTC)와 `tz_source`를 추가 저장한다. DDL 변경 없음(JSON 필드 추가). 이 두 값이 나중 재교정의 입력이 된다.
3. `tz_source='fallback_fixed'`인 행은 "시간대 추정" 상태다. 사용자 노출(가져오기 결과 요약·활동 상세 표시 여부·문구)은 D8.
4. 기존 행 갱신 규칙: CSV가 기존 행의 `start_time`을 바꾸는 것은 새 값의 `tz_source`가 기존 값보다 **같거나 높은 우선순위일 때만** 허용한다. 즉 API 경로로 들어온 행은 CSV의 폴백값으로 덮어쓰지 않는다. `_fill_null_fields`의 강제 갱신도 같은 규칙을 따른다.

**연결 유효성 인터페이스** — 기존 판정을 재사용하고 새 판정 로직은 만들지 않는다.
- `strava_tz.StravaTzLookup` (얇은 래퍼): `available: bool`, `status: str`, `fetch(source_id) -> dict | None`.
  - 생성 시 `config`가 없으면(가져오기 호출자가 안 넘김) `available=False, status="config 없음"`.
  - `check_strava_connection(config)["ok"]`가 False면 `available=False`, `status`는 그 반환값(`"설정 누락"`/`"재연동 필요"`).
  - `ok=True`면 `refresh_token(config)`를 1회 호출. 실패 시 `classify_exception()` 코드가 `auth_expired`면 `available=False, status="auth_expired"`.
  - `fetch()`는 `rate_limiter.py`를 거친다. 실행 중 401이 나오면 `available=False`로 전환.
- `import_strava_activities(conn, path, ..., config: dict | None = None)`와 `import_strava_archive(...)`에 선택 인자 `config` 추가. 기본값 None이라 기존 호출자(v1 `views_export_import.py` 포함)는 수정 없이 "저장 payload → FIT → 폴백" 체인으로 동작한다. v2 `import_service.apply_import()`만 config를 넘긴다.
- 반환 dict에 `tz_resolved: {"api_payload": n, "api_fetch": n, "fit_local": n, "fallback_fixed": n}`, `tz_lookup_status: str` 추가. 로그는 `[strava_csv] 시간대 폴백 N건 (Strava 연결: {status})` 한 줄(행별 로그 금지).

**연결 무효 시 동작 요약**: API 조회 생략 → 저장된 payload가 있는 행은 정확, 없는 행만 폴백 → 결과 요약에 폴백 건수·연결 상태 → 재연결 후 재교정은 D9(수동 스크립트 `normalize_start_time.py --source strava --tz-source fallback_fixed` 또는 동기화 후 자동).

**dedup 영향 (TZ-3 dry-run과 연결)**
- KST 활동은 체인 어느 단계든 결과가 지금(+9h)과 같다 → `start_time`·`group_id` 무변화.
- KST 밖에서 한 활동만 바뀐다(예: 도쿄 +9는 동일, 방콕 +7은 −2h, 유럽은 −7~−8h). 이 행들은 지금 Garmin `startTimeLocal`과 시간 차가 커서 `dedup._TIME_TOLERANCE`(7분)를 넘어 **매칭이 안 되던** 행이다. 교정 후 새로 매칭되어 group 병합이 생길 수 있다(분리는 드묾).
- `normalize_start_time.py --dry-run` 출력에 Strava CSV 행용 항목을 추가: `source_id`, 기존/신규 `start_time`, `tz_source`, 기존/예상 `group_id`. 예상 group은 `dedup.is_duplicate` 재평가로 산출하고 DB에 쓰지 않는다. 사용자가 이 목록을 보고 TZ-3 일괄 교정 여부를 정한다.
- "다른 시간대에서 한 활동"은 체인 1·2가 있으면 정확, 폴백이면 KST로 남는다 — 연결 무효 사용자에게 남는 유일한 오차이며 `tz_source`로 식별 가능하다.

**호환성**: v1(`src/web/views_export_import.py`)은 config 없이 호출하므로 API 조회 없이 동작, 수정하지 않는다(v1 제거 예정). 저장 형식은 무접미사 현지 시각 그대로라 v1 `[:10]` 절단과 충돌 없음. `_LOCAL_UTC_OFFSET` 상수는 폴백 값으로 남기되(D6 결과로 값/이름 변경 가능) 모듈 주석의 "dedup 기준" 설명을 "체인 4단계 폴백"으로 바꾼다.

### 2.3 프론트(v2) — 표시 함수 단일화
- `format.ts`에 `formatInstant(iso, style: 'stamp'|'time'|'date')` 추가: `parseDbTimestamp()` 재사용 후 `Intl.DateTimeFormat`(시간대는 D1)으로 포맷. `answerEvidence.ts`의 `stamp()`는 이를 호출하도록 교체.
- 활동 시각 표시 함수(`formatDateShort`, `formatDate`)는 동작 유지, JSDoc에 "wall-clock 전용, instant 금지" 명시. 사용처 0인 `formatDate()`는 제거 후보(범위 밖 메모).
- 2.1 완료 후에도 `parseDbTimestamp()`의 무표기 처리 분기는 v1·구 응답 호환을 위해 유지.

## 3. 변경 파일 표

| 구분 | 파일 | 내용 | 예상 줄 |
|---|---|---|---|
| 신규 | `src/utils/timefmt.py` | `to_iso_instant`, `to_local_wallclock` | ~60 |
| 신규 | `tests/test_timefmt.py` | 무표기 UTC, 오프셋 존재, 가짜 Z, offset 미상, None | ~80 |
| 신규 | `scripts/normalize_start_time.py` | source_payloads 기반 start_time 재계산(dry-run 기본) | ~90 |
| 수정 | `src/services/coach_evidence.py` | `computed_at` 직렬화 3곳 | +4 |
| 수정 | `src/services/sync_state_service.py` | 로컬 변환 헬퍼를 `timefmt`로 대체 | −10/+3 |
| 수정 | `src/services/wellness_day.py` | 154행 변환 대체 | ±2 |
| 수정 | `src/sync/extractors/{strava,intervals,garmin}_extractor.py` | `start_time`을 `to_local_wallclock`로 | 각 +3 |
| 수정 | `src/import_history.py` | FIT start_time 현지화 | +5 |
| 수정 | `frontend/src/lib/format.ts` (253줄) | `formatInstant` 추가, wall-clock 함수 주석 | +20 (→~273) |
| 수정 | `frontend/src/lib/answerEvidence.ts` | `stamp()` → `formatInstant` | ±4 |
| 수정 | `tests/test_coach_evidence*.py`, extractor 테스트 | `computed_at` 오프셋, `start_time` 무접미사 단언 추가 | +30 |
| 신규 | `src/import_export/strava_tz.py` | `resolve_strava_start`, `StravaTzLookup`(연결 판정 재사용 래퍼) | ~120 |
| 신규 | `tests/test_strava_tz.py` | 체인 4단계 각각, 연결 무효(설정 누락/재연동 필요/401), 가져오기 중 401 전환, 우선순위 낮은 값의 덮어쓰기 금지 | ~120 |
| 수정 | `src/import_export/strava_csv.py` (488줄, 이미 300줄 초과) | `_parse_strava_date`가 UTC를 반환하고 현지화는 `strava_tz`에 위임, payload에 `start_date_utc`·`tz_source`, 기존 행 갱신 규칙, `config` 인자, 반환 dict 확장. 새 로직은 `strava_tz.py`로 빼서 순증을 막음 | −10/+25 |
| 수정 | `src/import_export/strava_archive.py` | `config` 전달, FIT `local_timestamp`를 체인 3에 전달 | +10 |
| 수정 | `src/services/import_service.py` | Strava 가져오기에 config 전달, 결과의 `tz_resolved`·`tz_lookup_status` 노출 | +5 |
| 수정 | `scripts/normalize_start_time.py` (신규 파일에 포함) | `--source strava --tz-source` 필터, CSV 행의 예상 group_id 출력 | +30 |
| 수정 | 프론트 가져오기 결과 화면(v2, 구현 시 grep) | 폴백 건수·연결 상태 안내 (문구는 D8) | +10 |
| 수정 | `tests/test_strava_csv*.py` | 기존 +9h 단언을 "저장 payload 없음+config 없음 → 폴백" 케이스로 이동, API 행 보존 케이스 추가 | +40 |

v1 의존: `src/web/`(v1) 7개 파일이 `[:10]` 절단을 쓴다. 2.2로 저장값이 무접미사 현지 시각이 되면 v1도 같이 맞아지고 깨지는 부분은 없다. 2.1의 `computed_at` 형식 변경은 v1이 이 필드를 직접 잘라 쓰는지 구현 시 grep으로 확인한다(v1 제거 예정이므로 수정은 하지 않고 깨지면 기록만).

## 4. 단계와 검증

1. **조사(코드 무변경)**: 로컬 개발 DB 사본에서 `start_time LIKE '%Z' OR LIKE '%+00:00'` 행 수를 소스별로 집계하고, 1327의 `source_payloads` 원본과 대조해 RC-2 경로를 확정한다. 운영 DB는 쓰지 않는다.
2. **`timefmt.py` + 단위 테스트** → `pytest tests/test_timefmt.py`.
3. **C-06 적용**(2.1 + 2.3) → `pytest tests/`. 브라우저: `/coach`에서 근거 시트를 열고 "계산" 시각이 `metric_store.updated_at`+9h와 같은지 확인. `/today` 동기화 시각이 회귀하지 않았는지 확인.
4. **S-17 신규 수집 경로 적용**(extractor·FIT) → extractor 테스트에 `start_date_local`(가짜 Z)과 `start_date`만 있는 픽스처를 둘 다 둔다. dedup 테스트 전체 통과 확인.
4-1. **Strava CSV 활동별 timezone(2.2.1)**: 단계 1 조사에 "같은 `source_id`에 API payload가 있는 CSV 행 수 / 없는 행 수", `activity_summary` payload의 `timezone`·`utc_offset` 채움률을 추가한다. `strava_tz.py` + 테스트 → `pytest tests/test_strava_tz.py tests/test_strava_csv*.py`. 검증: (a) config 없이 가져오기 → 결과가 지금과 같음(폴백), (b) API payload가 있는 해외 활동 픽스처 → `start_date_local` 사용, (c) 연결 무효 config(`refresh_token` 없음, 401 모의) → 네트워크 호출 0회·가져오기 완료·`tz_lookup_status` 기록, (d) API로 들어온 행에 CSV 재가져오기 → `start_time` 유지.
5. **기존 행 교정**(D3 승인 시, dry-run 선행은 결정됨) — Strava CSV 행은 2.2.1 dry-run 목록(예상 group 변화 포함)을 먼저 사용자에게 보인다. → 스크립트 dry-run 출력 검토 후 적용. 브라우저: `/library/1327` 헤더가 "7/1(월)"인지, Garmin/Intervals 활동 날짜가 그대로인지, 목록 월 그룹(`activities/+page.svelte:220`)의 경계 확인.
6. `python3 scripts/check_docs.py`, `npm run check`(타입).

## 5. 대안 비교

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A (추천)** | 저장/직렬화 계약 분리: instant는 오프셋 ISO, 활동은 무접미사 현지 시각 | 근본 해결. 프론트 추측 제거, 소스별 차이 소멸, v1도 함께 교정 | 기존 행 교정 스크립트와 dedup 회귀 검증 필요 |
| B | 프론트만 수정: `stamp()`에 `parseDbTimestamp` 적용, 활동 날짜는 `Z`면 로컬 변환 | 변경 작음(프론트 2파일) | Strava API 가짜 `Z` 행을 9시간 밀어 정상 데이터를 깨뜨림. 소스별 의미 차이가 남아 재발 |

## 6. 결정 필요

- **D1. 표시 시간대 기준**: (a) 브라우저 시간대 — 구현 단순, 해외 접속 시 화면마다 달라짐 / (b) 서버 프로세스 로컬 시간대(현재 `date('now','localtime')`와 일치) — 백엔드 "오늘"과 일관, 컨테이너 TZ 설정에 의존 / (c) 사용자 설정값 — 가장 정확, 설정 항목·저장소 추가 필요.
- **D2. 오프셋 미상 UTC 활동(FIT 등)의 현지화**: (a) D1 기준 시간대로 변환 — 해외 레이스 날짜가 틀릴 수 있음 / (b) UTC 그대로 두고 "시간대 미상" 플래그 — 정직하지만 날짜 경계 문제 잔존.
- **D3. 기존 `start_time` 행 교정**: (a) 스크립트로 일괄 교정 — 즉시 일관, dedup 결과가 바뀔 수 있음(매칭/분리 재발생) / (b) 신규 수집분만 적용 — 안전, 과거 행 불일치 지속 / (c) 재동기화로 대체 — 외부 API 호출 비용.
- **D4. 근거 시트 시각 문구 형식**: 현재 `M/D HH:mm 계산`. 연도 포함·상대시각("3시간 전") 병기 여부.
- **D5. Strava CSV의 고정 오프셋(`_LOCAL_UTC_OFFSET`)** — **결정됨(2026-10-11, TZ-5): 활동별 timezone 기반으로 교체, Strava 연결 무효 시 폴백.** 설계는 2.2.1.

(D1~D3도 2026-10-11에 결정·부분 결정됨: D1 활동 시각=현지 벽시계/기록 시각=브라우저 시간대, D2 FIT 현지 시각 우선→KST, D3 dry-run 선행 후 일괄 교정 검토. 상세는 `decisions-table.md` TZ-1~3.)

아래 D6~D9는 TZ-5 설계로 새로 생긴 항목이다.

- **D6. 폴백 오프셋 값(체인 4단계)**: (a) KST +9 고정 — 현재 동작·TZ-2 폴백과 같아 dedup 결과 무변화, 해외 거주 사용자는 전부 틀림 / (b) 서버 프로세스 로컬 시간대 — 설정 불필요, 컨테이너 TZ(대개 UTC)에 따라 오히려 나빠질 수 있음 / (c) 사용자 설정 시간대 — 가장 정확, 설정 항목 신설 필요(TZ-1에서 사용자 설정은 채택 안 됨) / (d) 같은 날 앞뒤 활동 중 timezone이 확인된 활동의 값을 빌림 — 여행 중 정확도가 높지만 추론 규칙이 복잡하고 설명하기 어려움.
- **D7. API 조회(체인 2단계) 시점**: (a) 가져오기 요청 안에서 동기 조회 — 즉시 정확, 수천 건 CSV면 Strava 한도(15분 100회·일 1,000회)에 걸려 가져오기가 길어지거나 대부분 폴백 / (b) 가져오기는 폴백으로 끝내고 별도 백필 작업이 `tz_source='fallback_fixed'` 행을 한도 안에서 점진 조회 — 응답 빠르고 한도 안전, 교정이 늦게 반영되고 그 사이 날짜가 바뀌어 보일 수 있음 / (c) 조회하지 않음(저장 payload만) — 외부 호출 0, Strava API 동기화로 이미 들어온 활동만 정확.
- **D8. 연결 무효 시 사용자 안내**: 노출 위치 (a) 가져오기 결과 요약에만 "N건은 시간대를 확인하지 못해 한국 시간으로 저장했어요" / (b) (a) + 해당 활동 상세 헤더에 "시간대 추정" 표시 / (c) 로그만(UI 없음). (b)는 정직하지만 KST 사용자에겐 대부분 불필요한 표시가 늘고, (c)는 해외 활동 날짜 오류를 사용자가 알 수 없다. 문구와 "Strava 다시 연결" 링크 동반 여부도 함께.
- **D9. 연결 복구 후 재교정**: (a) 자동 — 재연결 후 첫 동기화(또는 D7-b 백필)가 `fallback_fixed` 행을 재계산 — 사용자 수고 없음, 과거 활동 날짜·dedup 그룹이 예고 없이 바뀔 수 있음 / (b) 수동 — 데이터 화면이나 스크립트에서 dry-run 확인 후 적용(TZ-3 원칙과 일관) — 안전, 사용자가 기능을 모르면 영구 미교정 / (c) 자동이되 KST와 결과가 같은 행은 조용히 확정, 바뀌는 행만 확인 요청 — 절충, 구현 범위 가장 큼.

## 7. 범위 밖 메모

- `format.ts`의 `formatDate()`는 사용처 0 — 제거 후보.
- `replanBanner.ts`, `wellnessDay.ts`, `onboarding.ts`, `RangeSyncForm.svelte` 등의 `new Date().toISOString().slice(0,10)`은 "오늘" 날짜를 UTC로 구해 KST 00~09시에 하루 전이 된다(별도 묶음 권장, coach plan 페이지는 이미 보정).
- `metrics/base.py:227,268`의 `datetime.now(timezone.utc)` 기본 종료일도 같은 경계 문제 가능성.
