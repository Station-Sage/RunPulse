# 설계: 시간대 표기 (UTC 표기·날짜 절단)

- 대상 ID: C-06 (코치 답변 근거 시트 "계산 시각" 9시간 어긋남), S-17 (Strava 단독 활동 상세 헤더 날짜가 KST 자정 경계에서 틀림)
- 상태: 설계 확정 (구현 전. TZ-1·2·4~16 결정, TZ-3만 부분 결정 — dry-run 결과 확인 후 범위 확정). 2026-10-11 설계서 동기화(TZ-10~16 확정 반영, TZ-1 추가 결정 '오늘' 기준일 헬퍼 반영)
- 관련 ADR: ADR-006 (Strava `start_date_local` 우선 — 활동 시각은 "현지 벽시계"가 기준이라는 기존 결정), ADR-009 (Calculator 무변경, 해당 없음)
- 결정 번호 대응: 본문 D1~D16 = `decisions-table.md`의 TZ-1~TZ-16(같은 번호).

### 변경 이력
- 2026-10-11 TZ-5 결정 반영 (Strava CSV 고정 오프셋 → 활동별 timezone, Strava 연결 무효 시 폴백. 2.2.1 신설, 표·단계·검증·결정 필요 갱신, D6~D9 추가)
- 2026-10-11 TZ-6 교차 소스 참조 반영 (Strava 연결 무효여도 같은 활동의 다른 소스 현지 시각/오프셋을 우선 폴백으로 사용. 2.2.2 신설, 체인 5단계로 재배치, D6 범위 축소, D7~D9 영향 기술, D10~D12 추가)
- 2026-10-11 TZ-6~9 결정 반영 (D6 같은 날 차용→KST, D7 별도 백필, D8 `fallback` 행만 '시간대 추정', D9 자동 재교정+이력·되돌리기·상한. 2.2.3 신설, 체인·표·단계·검증 갱신, D13~D16 추가)
- 2026-10-11 설계서 동기화(TZ-10~16 확정 반영): TZ-4 상대시각 병기, 허용오차 60초, 소스 우선순위 고정, 범위 Strava CSV/ZIP, 그룹 변화 행 자동 적용(`held` 보류 제거), 이동일=UTC 순시 가까운 쪽, 계기 확장(다른 소스 동기화 후 오프라인 재실행), 재연결 링크·툴팁. 6절을 결정 목록으로 정리
- 2026-10-11 설계서 동기화(TZ-1 추가 결정): 날짜 전용 필드의 '오늘' = 사용자 최근 활동의 현지 시간대 기준 날짜, 활동 없으면 서버 로컬 날짜 폴백 → 2.4 `reference_day` 헬퍼 신설, 변경 파일 표·단계 추가, 6절을 '결정 완료(표 참조)'로 축약, 7절 말미 '동기화 중 발견한 모호점'으로 정리

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
- `src/utils/timefmt.py`에 `to_local_wallclock(local: str | None, utc: str | None, offset_sec: int | None) -> str | None` 추가. 우선순위: 소스가 준 현지 시각(가짜 `Z` 제거) → `utc + offset` → (offset 미상) TZ-2대로 FIT 현지 시각, 없으면 KST 변환. Strava CSV는 2.2.1의 체인을 따른다.
- 적용: `strava_extractor.py:30`, `intervals_extractor.py:34`, `garmin_extractor.py:42`, `import_history.py:107`(FIT: `timestamp`+`local_timestamp` 메시지 활용 가능 여부 확인).
- 기존 행 교정(TZ-3 부분 결정): `source_payloads` 원본에서 재추출하는 1회성 스크립트(`scripts/normalize_start_time.py`, dry-run 기본). 일괄 교정을 전제로 하되 dry-run으로 dedup 변화를 먼저 확인하고, 적용 범위는 그 결과를 본 뒤 확정한다.

### 2.2.1 Strava CSV — 활동별 timezone (TZ-5 결정 반영)

**확인한 사실 (2026-10-11 grep)**
- 코드 위치는 `src/sync/extractors/`가 아니라 `src/import_export/strava_csv.py`. `_parse_strava_date()`가 CSV `Activity Date`(UTC)에 `_LOCAL_UTC_OFFSET = timedelta(hours=9)`를 더해 무표기로 저장한다. `strava_archive.py`(ZIP 내보내기)도 같은 `_parse_activity_row()`를 쓰므로 영향 범위가 같다.
- **조인 키 있음**: CSV `Activity ID` → `source_id`. API 경로(`strava_extractor.py:25`)도 `source_id = raw["id"]`이고 둘 다 `source='strava'`라서 **같은 `activity_summaries` 행**이다(CSV는 `INSERT OR IGNORE` 후 기존 행이면 `update_changed_fields`).
- **payload timezone**: API 경로는 `source_payloads`에 `entity_type='activity_summary'`(목록 응답 원본)와 `'activity_detail'`을 저장한다(`strava_activity_sync.py`). Strava API 활동 객체에는 `start_date`, `start_date_local`, `timezone`(예: `"(GMT+09:00) Asia/Seoul"`), `utc_offset`(초)이 있고, `timezone`은 metric `timezone_offset`(text)으로도 추출된다(`strava_extractor.py:87`). 실제 DB 행에 `utc_offset`이 채워져 있는지는 단계 1에서 확인한다.
- CSV 경로의 payload는 `entity_type='csv_export'`로 **이미 +9h 된** 파싱값만 저장한다. 원본 UTC·시간대 출처가 남지 않는다(고정 +9라 역산은 가능).
- **잠재 버그**: API로 이미 들어온 행에 CSV를 가져오면 `update_changed_fields`(값이 다르면 덮어씀)와 `_fill_null_fields`(start_time 강제 갱신)가 API의 `start_date_local`을 `UTC+9`로 덮어쓴다. KST 밖 활동은 이때 틀어진다. TZ-5 구현에서 함께 고친다(아래 규칙 4).
- **연결 상태 판정**: `strava_auth.check_strava_connection(config) -> {"ok", "status", "detail"}`. `ok`는 설정·refresh_token 유무만 본다(만료 access_token은 `ok=True`, 자동 갱신 전제). 폐기된 토큰은 갱신/호출 시 401 → `sync_errors.classify_exception()`이 `"auth_expired"`로 분류한다.

**우선순위 체인 (TZ-6·7 반영, 1~5b)** — 신규 `src/import_export/strava_tz.py`의 `resolve_strava_start(conn, source_id, utc_naive, distance_m, *, api=None, fit_local=None, peers=None) -> tuple[str, str]` (반환: 무접미사 현지 벽시계, `tz_source`). `peers`는 2.2.2의 `PeerTzIndex`(없으면 체인 3 생략).

| 순서 | 출처 | 방법 | 네트워크 | `tz_source` |
|---|---|---|---|---|
| 1 | 저장된 Strava API payload | 같은 `source_id`의 `source_payloads`(`activity_detail` → `activity_summary`)에서 `start_date_local`(가짜 `Z` 제거) 사용. 없으면 `start_date`+`utc_offset` | 없음 | `api_payload` |
| 2 | CSV/ZIP 내 단서 | ZIP 가져오기에 FIT 원본이 있으면 `local_timestamp`(TZ-2 규칙 재사용). 단독 CSV에는 시간대 컬럼이 없으므로 이 단계 없음 | 없음 | `fit_local` |
| 3 | **다른 소스의 같은 활동 (TZ-6)** | 2.2.2. Garmin·Intervals·Runalyze 행 중 UTC 순시가 허용오차 안이고 거리가 맞는 활동의 오프셋(현지 벽시계 − UTC)을 빌림 | 없음(DB 내부만) | `peer_direct:{source}` / `peer_derived:{source}` |
| 4 | Strava API 조회 (**가져오기 밖, TZ-7**) | 가져오기 요청 안에서는 호출하지 않는다. 2.2.3 백필 작업이 `GET /activities/{id}` 결과를 `upsert_raw_payload(..., "activity_detail", ...)`로 저장한 뒤 1과 같은 규칙 | 있음(백필만) | `api_fetch` |
| 5a | 같은 날 차용 (TZ-6 d) | 대상과 같은 현지 날짜에 앞뒤로 있는 **시간대 확인 활동**(등급 `api_*`·`fit_local`·`peer_direct`, 모든 소스)의 오프셋을 빌림. 아래 "차용 규칙" | 없음 | `neighbor:{source}` |
| 5b | 최종 폴백 (TZ-2와 동일) | 차용 대상도 없으면 KST +9 (`_LOCAL_UTC_OFFSET`) | 없음 | `fallback` |

**차용 규칙 (5a)** — `PeerTzIndex.nearest_confirmed(utc_target) -> (prev, next)`. 후보는 확인 등급 활동만(차용·폴백·`peer_derived` 값은 다시 빌려주지 않음 → 연쇄 추정 차단). 후보의 오프셋으로 환산한 대상의 현지 날짜가 후보의 현지 날짜와 같을 때만 "같은 날"로 본다. 앞·뒤 중 한쪽만 있으면 그 값, 둘의 오프셋이 같으면 그 값, **다르면(이동일)** UTC 순시가 대상에 더 가까운 쪽(TZ-14). `tz_peer`에 `{"mode":"neighbor","prev":…,"next":…}`를 남긴다.

**순서 변경 이유 (TZ-5 대비)**
- 기존 순서는 "payload → API → FIT → 고정 오프셋"이었다. TZ-6로 **오프라인 단계를 모두 외부 호출 앞에** 둔다. 근거: (1) coding-rules의 "sync 중단 금지"와 Strava 한도(15분 100회·일 1,000회)를 고려하면 DB 안에서 풀리는 행은 API를 쓰지 않는 편이 낫다. (2) 사용자 지시의 핵심 상황이 "Strava 연결 무효"이므로 교차 소스는 연결 상태와 무관하게 항상 실행돼야 한다.
- FIT(2)를 교차 소스(3)보다 앞에 둔 이유: FIT `local_timestamp`는 **같은 활동의 원본 파일**이라 매칭 불확실성이 없다. 교차 소스는 "같은 활동인가"를 추정하는 단계라 한 단계 아래다.
- API 조회(4)를 교차 소스 뒤에 둔 이유: `peer_direct`는 정확도가 API와 사실상 같다(같은 기기 기록이 각 플랫폼으로 전파). `peer_derived`·`neighbor:*`·`fallback`으로 끝난 행만 2.2.3 백필이 API로 덮어쓸 대상이다(TZ-7: 가져오기 안에서는 4를 건너뛰고 5로 끝냄).

규칙:
1. 가져오기 경로의 체인(1·2·3·5a·5b)은 **네트워크 호출 0회**로 끝난다(TZ-7 b). `config`는 연결 상태 기록과 백필 예약 판단에만 쓴다.
2. CSV payload(`csv_export`)에 `start_date_utc`(CSV 원본 UTC)와 `tz_source`, 교차 소스/차용으로 풀린 경우 `tz_peer`(`{"source", "source_id", "offset_sec", "delta_sec"}` 또는 차용 형식)를 추가 저장한다. DDL 변경 없음(JSON 필드 추가). 재교정 이력은 같은 payload의 `tz_history`(2.2.3).
3. "시간대 추정" **표시**는 `tz_source == "fallback"`(5b 실제 사용) 행에만 한다(TZ-8). `peer_derived:*`·`neighbor:*`는 표시하지 않되 백필 대상에는 포함한다.
4. 기존 행 갱신 규칙: `start_time` 변경은 새 값의 신뢰 등급이 기존보다 **같거나 높을 때만** 허용. 등급(높음→낮음): `api_payload` = `api_fetch` = `fit_local` > `peer_direct:*` > `peer_derived:*` > `neighbor:*` > `fallback`. API 경로 행은 CSV의 추정값으로 덮어쓰지 않는다. `_fill_null_fields` 강제 갱신·2.2.3 재교정도 같은 규칙. 등급 표는 `strava_tz.TZ_SOURCE_RANK` 1곳.

**연결 유효성 인터페이스** — 기존 판정을 재사용하고 새 판정 로직은 만들지 않는다.
- `strava_tz.StravaTzLookup` (얇은 래퍼): `available: bool`, `status: str`, `fetch(source_id) -> dict | None`.
  - 생성 시 `config`가 없으면(가져오기 호출자가 안 넘김) `available=False, status="config 없음"`.
  - `check_strava_connection(config)["ok"]`가 False면 `available=False`, `status`는 그 반환값(`"설정 누락"`/`"재연동 필요"`).
  - `ok=True`면 `refresh_token(config)`를 1회 호출. 실패 시 `classify_exception()` 코드가 `auth_expired`면 `available=False, status="auth_expired"`.
  - `fetch()`는 `rate_limiter.py`를 거친다. 실행 중 401이 나오면 `available=False`로 전환. **호출자는 2.2.3 백필뿐**이다.
- `import_strava_activities(conn, path, ..., config: dict | None = None)`와 `import_strava_archive(...)`에 선택 인자 `config` 추가(연결 상태 판정만, 네트워크는 `refresh_token` 1회 이하). 기본값 None이라 기존 호출자(v1 포함)는 수정 없이 같은 오프라인 체인으로 동작. v2 `import_service.apply_import()`만 config를 넘긴다.
- 반환 dict에 `tz_resolved: {"api_payload", "fit_local", "peer_direct", "peer_derived", "neighbor", "fallback"}`(건수), `tz_lookup_status: str`, `tz_peer_conflicts: n`, `tz_backfill_pending: n`(백필 대상 수) 추가. 로그는 `[strava_csv] 시간대 교차소스 N건·차용 K건·폴백 M건 (Strava 연결: {status})` 한 줄(행별 로그 금지).

**연결 무효 시 동작 요약 (TZ-6~9 반영)**: 가져오기는 연결과 무관하게 오프라인 체인으로 끝남 → payload 있는 행 정확 → 다른 소스에 같은 활동 있으면 그 오프셋 → 없으면 같은 날 앞뒤 확인 활동 차용 → 그것도 없으면 KST(`fallback`, '시간대 추정' 표시) → 결과 요약에 건수·연결 상태 → 연결이 유효해지면 2.2.3 백필·자동 재교정이 추정 행을 점진 교정(다른 소스 동기화 뒤에는 연결 없이도 오프라인 단계 재실행, TZ-15).

**사용자 안내 (TZ-8 B)**
- 가져오기 결과 요약(v2 가져오기 결과 화면): `fallback`이 1건 이상일 때만 "N건은 시간대를 확인하지 못해 한국 시간으로 저장했어요" + 연결 상태. 0건이면 문구 없음. 연결이 무효일 때만 "Strava 다시 연결" 링크(설정 화면)를 붙이고 유효하면 숨긴다(TZ-16).
- 활동 상세 헤더(`/library/[id]/+layout.svelte`): 응답 필드 `tz_estimated: bool`(= `csv_export` payload의 `tz_source == "fallback"`)이 참일 때만 날짜 옆 "시간대 추정" 보조 표기, 툴팁 "Strava 시간대를 확인하지 못해 한국 시간으로 표시했어요. 연결하면 자동으로 고쳐져요"(TZ-16). 상세 서비스가 payload를 `json_extract`로 1회 읽음(DDL 무변경, 서비스 파일은 구현 시 grep). 재교정으로 등급이 오르면 표기는 자동 소멸.
- 대상은 드물 것으로 예상(Strava 단독·payload 없음·연결 무효·교차/차용 실패의 교집합). 단계 1에서 실제 건수를 집계해 0건에 가까우면 UI 작업 순서를 뒤로 미룬다(설계는 유지).

**dedup 영향 (TZ-3 dry-run과 연결)**
- KST 활동은 체인 어느 단계든 결과가 지금(+9h)과 같다 → `start_time`·`group_id` 무변화.
- KST 밖에서 한 활동만 바뀐다(예: 도쿄 +9는 동일, 방콕 +7은 −2h, 유럽은 −7~−8h). 이 행들은 지금 Garmin `startTimeLocal`과 시간 차가 커서 `dedup._TIME_TOLERANCE`(7분)를 넘어 **매칭이 안 되던** 행이다. 교정 후 새로 매칭되어 group 병합이 생길 수 있다(분리는 드묾).
- `normalize_start_time.py --dry-run` 출력에 Strava CSV 행용 항목을 추가: `source_id`, 기존/신규 `start_time`, `tz_source`, 기존/예상 `group_id`. 예상 group은 `dedup.is_duplicate` 재평가로 산출하고 DB에 쓰지 않는다. 사용자가 이 목록을 보고 TZ-3 일괄 교정의 적용 범위를 확정한다.
- "다른 시간대에서 한 활동"은 체인 1~3이면 정확, 5a면 대개 정확(이동일 제외), 5b면 KST로 남는다 — 연결 무효 사용자에게 남는 오차는 "같은 날 다른 확인 활동도 없는 Strava 단독 해외 활동"뿐이며 `tz_source`로 식별된다.
- 교차 소스(체인 3)는 dedup 결과에 **의존하지 않는다**(2.2.2 순환 방지). 교정된 `start_time`으로 dedup이 다시 판정되는 것은 한 방향(시간대 → dedup)뿐이다.

**호환성**: v1(`src/web/views_export_import.py`)은 config 없이 호출하므로 API 조회 없이 동작, 수정하지 않는다(v1 제거 예정). v1 경로도 `peers`는 내부에서 기본 생성하므로 교차 소스 교정은 함께 받는다(외부 호출 없음). 저장 형식은 무접미사 현지 시각 그대로라 v1 `[:10]` 절단과 충돌 없음. `_LOCAL_UTC_OFFSET` 상수는 5b 값(+9)으로 남기고 모듈 주석의 "dedup 기준" 설명을 "체인 5b 최종 폴백"으로 바꾼다.

### 2.2.2 교차 소스 시간대 참조 (TZ-6 결정 반영)

**사용자 결정(2026-10-11)**: "Strava 연결이 안 되어 타임존을 모르더라도, 다른 앱(소스)에 기록된 같은 활동의 타임존을 참고하면 된다." → 같은 실제 활동이 다른 소스에 있으면 그 소스의 현지 시각/오프셋을 우선 폴백으로 쓴다(체인 3단계).

**확인한 사실 (2026-10-11 grep)**
- 지원 활동 소스는 `src/sync/extractors/`의 **garmin·intervals·runalyze·strava 4개뿐**이다(그 외 `base.py`, `garmin_lap_fields.py`, `garmin_maxmet_fields.py`, `stream_time.py`는 보조 모듈). **삼성헬스 소스는 코드에 없다**(`src/` 전체에서 `samsung|shealth` grep 0건). 아래 인터페이스는 삼성헬스 등 향후 소스를 함수 1개 추가로 흡수하도록만 설계하고, 삼성헬스 자체는 범위 밖이다.
- 소스별 활동 시간 정보와 원본 보존 위치:

| 소스 | 원본 필드(활동 요약) | 현재 `start_time`에 쓰는 값 (extractor) | 오프셋 단서 | `source_payloads` 저장 | 교차 소스 등급 |
|---|---|---|---|---|---|
| Garmin | `startTimeLocal`(현지, 무표기), `startTimeGMT`(UTC, 무표기) | `startTimeLocal or startTimeGMT` (`garmin_extractor.py:42`) | `timeZoneUnitDTO.offset` → metric `timezone_offset` (`:161`, 상세에 있을 때) | `activity_summary`·`activity_detail` 등 (`garmin_activity_sync.py`, bulk loader, `garmin_backfill.py`는 `activity_zip`) | **direct** (local − GMT) |
| Intervals | `start_date_local`(현지), `start_date`(UTC) | `start_date_local or start_date` (`intervals_extractor.py:34`) | extractor는 timezone 필드를 읽지 않음. 원본에 `timezone` 키가 있는지는 단계 1에서 확인 | `activity_summary` (`intervals_activity_sync.py:72`) | **direct** (local − UTC) |
| Runalyze | `datetime` (또는 `start_time`) | `datetime or start_time` (`runalyze_extractor.py:37`) | extractor에 오프셋/UTC 필드 없음. `datetime` 문자열에 오프셋 접미사가 붙는지는 미확인(단계 1) | `activity_summary` (`runalyze_activity_sync.py:64`) | 접미사 있으면 direct, 없으면 **derived**(현지만 있음 → 대상의 UTC로 오프셋 역산) |
| Strava API | `start_date`(UTC), `start_date_local`(가짜 `Z`), `timezone`, `utc_offset` | `start_date_local or start_date` (`strava_extractor.py:30`) | `timezone` → metric `timezone_offset` (`:87`) | `activity_summary`·`activity_detail` (`strava_activity_sync.py:85,97`) | 같은 소스 — 체인 1이 처리 |
| Strava CSV/ZIP | `Activity Date`(UTC) | +9h 고정 (`strava_csv.py`) | 없음 | `csv_export`(이미 +9h 값만) | 교차 소스의 **대상**이지 제공자가 아님 |
| FIT 가져오기 | `timestamp`(UTC), `local_timestamp`(있으면) | UTC `+00:00` (`import_history.py:107`) | `local_timestamp` | 구현 시 확인 | `local_timestamp` 있을 때만 direct, 없으면 제공자 제외 |

**순환 문제와 매칭 키 선택**
- 기존 dedup(`src/utils/dedup.py`)은 `activity_summaries.start_time`을 `_parse_dt()`로 **시간대를 버리고** 비교한다(`_TIME_TOLERANCE` 7분 + 거리 규칙, `matched_group_id`). `start_time`의 의미가 소스마다 다르므로(Garmin 현지, Strava CSV는 UTC+9 고정) 해외 활동에서 dedup 결과 자체가 틀린 시간대 위에서 만들어진다. 이 그룹을 "같은 활동" 판정의 근거로 쓰면 "틀린 시각 → 그룹 → 그 그룹으로 시각 교정"의 순환이 생긴다.
- 따라서 **판정 키는 각 소스의 UTC 순시(instant)**로 한다. `start_time` 컬럼은 판정에 쓰지 않는다.
  - 대상(Strava CSV 행): CSV 원본 UTC(`start_date_utc`, 규칙 2로 신규 저장). 기존 행은 `csv_export` payload의 값 − 9h(고정 +9였으므로 정확히 역산 가능).
  - 제공자: Garmin `startTimeGMT`, Intervals `start_date`, Runalyze는 접미사가 있을 때만 UTC 환산, FIT `timestamp`.

**매칭 경로 2가지**
1. **단순 경로 (dedup 그룹 재사용)** — 대상 행에 `matched_group_id`가 있으면 같은 그룹의 다른 소스 행을 후보로 먼저 본다. KST 활동은 지금도 대부분 이 경로로 잡힌다. **단, 그룹 소속만으로 확정하지 않고** 아래 2의 UTC 순시·거리 검증을 똑같이 통과해야 채택한다(그룹이 틀린 시각으로 우연히 묶였을 가능성 차단). 검증 실패한 그룹 후보는 버리고 2로 진행한다.
2. **UTC 순시 경로 (기본)** — `PeerTzIndex`가 제공자 소스들의 `activity_summary` payload를 한 번에 읽어 `(utc_instant, local_wallclock|None, distance_m, source, source_id, grade)` 목록을 UTC 순으로 정렬해 둔다. 대상마다 `bisect`로 `|utc_peer − utc_target| ≤ 허용오차(TZ-10: 60초, 상수 `PEER_TOLERANCE_SEC`)` 후보를 찾고, 거리 조건은 `dedup.is_duplicate`의 거리 규칙을 재사용한다(시간 비교는 이 경로가 대신하므로 거리 함수만 분리 호출. dedup 모듈 변경은 거리 판정 헬퍼를 공개 함수로 꺼내는 정도).
   - 수천 건 CSV에서도 payload 조회는 제공자 소스별 1회 쿼리 + 메모리 이분 탐색이라 O((N+M) log M). 행마다 SQL을 날리지 않는다.
   - derived 제공자(Runalyze 현지만)는 UTC가 없어 순시 비교가 불가하다. 대신 `local_peer − utc_target`이 −12h~+14h 안이고 15분 배수 ± 허용오차(60초)인 후보를 찾되, 그 창 안에서 거리 조건까지 통과하는 Runalyze 활동이 **정확히 1건일 때만** 채택한다(같은 날 비슷한 거리 활동이 2건 이상이면 오프셋이 달라질 수 있어 포기). 단순 경로(그룹)에서 후보가 Runalyze뿐일 때도 같은 규칙.

**오프셋 계산**
- `offset_sec = local_wallclock − utc_instant`(초). 실제 시간대는 15분 단위이므로 가장 가까운 900초 배수로 반올림하고, 반올림 오차가 120초를 넘거나 범위(−12h~+14h)를 벗어나면 그 후보를 버린다(기록 지연·파싱 오류 방지).
- 대상의 현지 벽시계 = `utc_target + offset_sec`. 제공자의 현지 시각을 그대로 복사하지 **않는다**(소스 간 시작 시각이 수 초~수십 초 다를 수 있으므로 대상 자신의 UTC를 기준으로 한다).

**소스 간 오프셋 충돌 시 우선순위**
1. 등급: `direct`(소스가 현지 시각과 UTC를 함께 줌: Garmin, Intervals, 접미사 있는 Runalyze, `local_timestamp` 있는 FIT) > `derived`(현지만 있어 역산).
2. 같은 등급 안에서 오프셋이 모두 같으면 채택, `tz_source`에는 순시 차가 가장 작은 제공자를 기록.
3. 같은 등급 안에서 오프셋이 다르면 **소스 우선순위 고정**(TZ-11): `dedup._SOURCE_PRIORITY`(garmin > intervals > runalyze) 최상위 제공자의 오프셋 채택. 충돌 건수는 `tz_peer_conflicts`로 집계하고 payload `tz_peer`에 후보 전부를 남긴다.
4. 상위 등급 결과가 있으면 하위 등급 후보는 비교하지 않는다(충돌로 세지 않음).

**인터페이스 (삼성헬스 등 향후 소스 흡수 방식)** — 신규 `src/utils/tz_peers.py`
- `PeerTime` (dataclass): `source, source_id, utc: datetime | None, local: datetime | None, distance_m: float | None, grade: Literal["direct","derived"]`.
- `_PEER_READERS: dict[str, Callable[[dict], PeerTime | None]]` — 소스별 **payload → PeerTime** 순수 함수 등록표. 현재 `garmin`(startTimeGMT/startTimeLocal), `intervals`(start_date/start_date_local), `runalyze`(datetime, 접미사 판별). 새 소스(예: 삼성헬스)가 생기면 해당 sync가 `source_payloads`에 `activity_summary`를 저장하고 reader 1개를 등록하는 것만으로 체인 3에 합류한다. Strava는 대상 자신이므로 등록하지 않되, `strava` reader는 등록하지 않는다(TZ-12: 적용 범위가 Strava CSV/ZIP뿐).
- `PeerTzIndex.build(conn, exclude_sources: set[str]) -> PeerTzIndex` / `lookup(utc_target, distance_m, group_id=None) -> PeerMatch | None` (`PeerMatch`: `offset_sec, grade, source, source_id, delta_sec, conflicts: list`).
- DB 접근은 `source_payloads` 읽기 전용, 외부 호출 없음. 데이터가 없으면 `None`(에러 없음).
- `strava_tz.py`는 이를 호출만 한다. 파일 300줄 규칙상 매칭 로직을 `strava_tz.py`에 넣지 않는다.

**적용 범위 (TZ-12)**: Strava CSV/ZIP(체인 3)만. FIT 가져오기·전체 소스 확장은 후속.

**다른 결정과의 관계**: 교차 소스로 5a·5b 행이 줄어 D6 차용·D8 표시·D7 백필 대상이 모두 작아진다. 다른 소스 동기화로 같은 활동이 나중에 들어오면 외부 호출 없는 재교정 계기가 된다(TZ-15, 2.2.3).

### 2.2.3 백필·자동 재교정 (TZ-7·TZ-9 결정 반영)

신규 `src/import_export/tz_backfill.py`: `run_tz_backfill(conn, config, *, offline_only=False, max_rows=TZ_BACKFILL_MAX_ROWS, dry_run=False) -> dict`. 백필(TZ-7, 체인 4)과 자동 재교정(TZ-9)을 **한 함수**로 처리한다 — 둘 다 "추정 행의 체인 재실행 + 등급 상승 시 갱신"이라 같은 경로다.

**대상 선택**: `source='strava'` 행 중 `csv_export` payload의 `tz_source`가 `fallback` → `neighbor:*` → `peer_derived:*` 순, 같은 등급 안에서는 최근 활동부터. `tz_backfill.attempts ≥ 3`(404·삭제 활동 등 영구 실패)은 제외.

**실행 계기 (TZ-15)**: (1) Strava 동기화 성공 직후 꼬리 작업 — 연결 유효(`StravaTzLookup.available`)·대상 1건 이상이면 체인 1~5a 전체(API 포함). (2) 다른 소스(Garmin·Intervals·Runalyze) 동기화 후 `offline_only=True` — 체인 1~3·5a만, 외부 호출 0회, 상한 미적용(대상 0이면 쿼리 1회). 둘 다 `orchestrator.py`(위치는 구현 시 grep).

**한도 처리**
- 1회 상한 `TZ_BACKFILL_MAX_ROWS = 50`(Strava 15분 100회 중 동기화 몫을 남김). 호출은 `rate_limiter.py` 경유.
- 429 → 즉시 중단(`stopped_reason="rate_limited"`), 401 → 중단(`"auth_expired"`), 기타 실패 → 재시도 1회 후 그 행 `attempts += 1`, 다음 행 계속. 남은 행은 다음 동기화가 이어받는다(진행 상태 저장소 불필요 — 대상 선택 쿼리 자체가 남은 일).
- 행마다 체인 1~3을 먼저 재실행(외부 호출 없이 풀리면 API 생략), 안 풀리면 4(API).

**안전장치 (TZ-9)**
1. **이력 보존·되돌리기**: 값이 바뀌는 행의 `csv_export` payload `tz_history`(최근 5건)에 `{"run_id", "at", "prev_start_time", "prev_tz_source", "new_start_time", "new_tz_source", "prev_group_id", "new_group_id"}`를 append. 되돌리기는 `normalize_start_time.py --revert-run <run_id>`(dry-run 기본): `prev_*` 복원 + 해당 행 dedup 재평가. 되돌린 행은 `tz_pinned=true`로 표시해 이후 자동 재교정에서 제외(재실행 시 다시 바뀌는 왕복 방지).
2. **등급 단조 증가**: 2.2.1 규칙 4. 같은 등급·같은 값이면 쓰지 않고 이력도 남기지 않는다.
3. **dedup 그룹 변화 (TZ-13)**: 그룹이 바뀌는 행도 자동 적용한다(보류 없음). 갱신 전 `group_id`와 새 `start_time`으로 `dedup` 재평가(`src/utils/dedup.py`의 단일 행 재매칭 함수, 없으면 공개 헬퍼로 분리)한 결과를 `tz_history`의 `prev_group_id`/`new_group_id`에 남기고 `group_changed`로 집계·로그. 되돌리기는 1의 `--revert-run`.
4. **원자성**: 행 단위 트랜잭션(`start_time`·payload·dedup 갱신을 한 번에). 중간 중단 후 재실행해도 끝난 행은 등급이 올라 대상에서 빠지므로 중복 처리 없음.
5. **멱등성**: 같은 DB 상태·같은 API 응답이면 두 번째 실행은 변경 0건·이력 추가 0건. `run_id`는 실행마다 새로 발급.
6. **보고**: 동기화 결과에 `tz_recalibrated: {"checked", "changed", "date_changed", "group_changed", "api_calls", "stopped_reason", "run_id"}`, 로그 1줄 `[tz_backfill] run=… 확인 N·변경 M(날짜 변경 D·그룹 변화 G)·API A회`. 행별 목록은 `tz_history`로 조회(`normalize_start_time.py --list-run <run_id>`).

**TZ-3(일괄 교정 dry-run 선행)과의 관계**: TZ-3은 "규칙 변경으로 **확정값을 포함한** 기존 행 전체를 다시 쓰는" 일괄 교정에 적용된다. TZ-9 자동 재교정은 대상이 추정 행(`fallback`·`neighbor`·`peer_derived`)으로 한정되고, 등급이 오르는 방향만 허용되며, 이력·되돌리기가 있으므로 dry-run 없이 자동 실행한다(TZ-9). dedup 그룹이 바뀌는 행도 자동 적용하고 로그·이력으로 추적한다(TZ-13). `dry_run=True`는 같은 함수로 제공해 스크립트·테스트가 재사용.

### 2.3 프론트(v2) — 표시 함수 단일화
- `format.ts`에 `formatInstant(iso, style: 'stamp'|'time'|'date')` 추가: `parseDbTimestamp()` 재사용 후 `Intl.DateTimeFormat`(시간대 = 브라우저 기본, TZ-1)으로 포맷. `answerEvidence.ts`의 `stamp()`는 이를 호출하도록 교체하고, 문구는 현행 `M/D HH:mm 계산` 유지 + 상대시각 병기(`· 3시간 전`, TZ-4) — `formatRelative(iso)`를 `format.ts`에 함께 둔다.
- 활동 시각 표시 함수(`formatDateShort`, `formatDate`)는 동작 유지, JSDoc에 "wall-clock 전용, instant 금지" 명시. 사용처 0인 `formatDate()`는 제거 후보(범위 밖 메모).
- 2.1 완료 후에도 `parseDbTimestamp()`의 무표기 처리 분기는 v1·구 응답 호환을 위해 유지.

### 2.4 '오늘' 기준일 헬퍼 (TZ-1 추가 결정 반영)

**결정(2026-10-11)**: 날짜 전용 필드(`race_date` 검증·대회 자동 done·D-day·'오늘 이후')의 '오늘'은 **사용자의 최근 활동의 현지 날짜(시간대) 기준**, 활동이 없으면 **서버 로컬 날짜로 폴백**. 활동 시각(현지 벽시계)·기록 시각(브라우저) 규칙(D1)은 그대로이고, 이 헬퍼는 "날짜만 있는 값과 비교할 오늘"만 정한다.

신규 `src/utils/reference_day.py` (서버가 유일한 계산 지점, ~70줄)
- `reference_offset(conn) -> tuple[int | None, dict]`: 최근 활동의 UTC 오프셋(초)과 근거(`{"activity_id", "source", "tz_source"}`). 오프셋은 2.2·2.2.1 체인이 이미 만든 값만 읽는다(새 해석기 없음) — `metric_store.timezone_offset`(Garmin 초, Strava 텍스트는 파서 공유), Strava CSV 행은 `csv_export` payload의 `start_time − start_date_utc`. 활동 없음·오프셋을 못 구함 → `(None, {})`. 추정 등급(`fallback` 등) 행의 취급은 7절 모호점.
- `reference_today(conn, *, now_utc: datetime | None = None) -> date`: 오프셋이 있으면 `(now_utc + offset).date()`, 없으면 서버 로컬 날짜(`date('now','localtime')`와 같은 값). `now_utc` 주입으로 테스트 결정적.
- `reference_today_info(conn) -> {"date", "basis": "activity_tz"|"server_local", "offset_sec"}`: API 응답 동봉용. 날짜 전용 필드를 다루는 응답(대회 캘린더 목록·D-day 등)은 이 `today`를 함께 내려 주고, 프론트는 `new Date()`로 오늘을 따로 구하지 않는다.
- DB 접근은 읽기 전용 쿼리 1~2회, 외부 호출 없음, 데이터 없으면 폴백(에러 없음). 한 요청 안에서 여러 번 부르면 호출자가 값을 넘겨 재사용한다.

**사용처(이 묶음 밖 설계서가 참조)**: `bundles/race-calendar.md`(지연 done 전이 `race_date < 오늘`, D-day, 다가오는/지난 구역, race_date 검증), `bundles/adjustment-signals.md`(`race_plan` 수집 창·phase), `bundles/adjustment-new-signals.md`(에피소드 신선도·자동 후보 2일 무응답 판정). 구현 시 해당 경로의 `date.today()`·`date('now','localtime')`를 grep해 이 헬퍼로 바꾼다.

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
| 수정 | `frontend/src/lib/format.ts` (253줄) | `formatInstant`·`formatRelative`(TZ-4) 추가, wall-clock 함수 주석 | +28 (→~281) |
| 수정 | `frontend/src/lib/answerEvidence.ts` | `stamp()` → `formatInstant` + 상대시각 병기 | ±6 |
| 수정 | `tests/test_coach_evidence*.py`, extractor 테스트 | `computed_at` 오프셋, `start_time` 무접미사 단언 추가 | +30 |
| 신규 | `src/import_export/strava_tz.py` | `resolve_strava_start`, `StravaTzLookup`(연결 판정 재사용 래퍼) | ~120 |
| 신규 | `tests/test_strava_tz.py` | 오프라인 체인 각 단계(교차 소스·5a 차용·5b), 가져오기 중 네트워크 0회, 연결 무효(설정 누락/재연동 필요/401) 상태 기록, 낮은 등급 덮어쓰기 금지 | ~120 |
| 신규 | `src/import_export/tz_backfill.py` | TZ-7·9: `run_tz_backfill`(대상 선택·상한·한도 중단·이력·그룹 변화 자동 적용+기록·`offline_only`·보고) | ~160 |
| 신규 | `tests/test_tz_backfill.py` | 2.2.3 검증 목록(단계 4-3) | ~170 |
| 수정 | `src/sync/orchestrator.py` | Strava 동기화 성공 후 `run_tz_backfill`, 다른 소스 동기화 후 `offline_only=True` 호출(TZ-15), 결과에 `tz_recalibrated` | +14 |
| 수정 | 활동 상세 서비스(구현 시 grep) + `frontend/src/routes/library/[id]/+layout.svelte` | TZ-8·16: `tz_estimated` 필드, 헤더 "시간대 추정" 표기+툴팁 | +5 / +10 |
| 수정 | `src/import_export/strava_csv.py` (488줄, 이미 300줄 초과) | `_parse_strava_date`가 UTC를 반환하고 현지화는 `strava_tz`에 위임, payload에 `start_date_utc`·`tz_source`, 기존 행 갱신 규칙, `config` 인자, 반환 dict 확장. 새 로직은 `strava_tz.py`로 빼서 순증을 막음 | −10/+25 |
| 수정 | `src/import_export/strava_archive.py` | `config` 전달, FIT `local_timestamp`를 체인 3에 전달 | +10 |
| 수정 | `src/services/import_service.py` | Strava 가져오기에 config 전달, 결과의 `tz_resolved`·`tz_lookup_status` 노출 | +5 |
| 수정 | `scripts/normalize_start_time.py` (신규 파일에 포함) | `--source strava --tz-source` 필터, CSV 행의 예상 group_id 출력, 교차 소스 결과(`tz_peer`) 열, TZ-9 `--list-run`/`--revert-run <run_id>`(dry-run 기본, `tz_history` 기반) | +60 |
| 신규 | `src/utils/tz_peers.py` | TZ-6: `PeerTime`, `_PEER_READERS`(garmin/intervals/runalyze), `PeerTzIndex.build/lookup/nearest_confirmed`(5a 차용), 오프셋 반올림·범위 검증, 60초 허용오차(TZ-10), 소스 우선순위 충돌 처리(TZ-11), 이동일 순시 근접 차용(TZ-14) | ~170 |
| 신규 | `tests/test_tz_peers.py` | TZ-6 교차 소스 매칭 단위 테스트(4단계 검증 목록) | ~150 |
| 수정 | `src/utils/dedup.py` | `is_duplicate`의 거리 판정을 공개 헬퍼(`distance_matches`)로 분리, 기존 동작 무변화 | ±10 |
| 수정 | `src/import_export/strava_tz.py` (위 신규에 포함) | 체인 재배치(가져오기는 오프라인만, 5a/5b), `peers` 인자, `TZ_SOURCE_RANK` | +30 |
| 수정 | 프론트 가져오기 결과 화면(v2, 구현 시 grep) | TZ-8·16: `fallback` ≥1건일 때만 안내·연결 상태, 연결 무효일 때만 "Strava 다시 연결" 링크 | +12 |
| 수정 | `tests/test_strava_csv*.py` | 기존 +9h 단언을 "저장 payload 없음+config 없음 → 폴백" 케이스로 이동, API 행 보존 케이스 추가 | +40 |
| 신규 | `src/utils/reference_day.py` | TZ-1 추가 결정: `reference_offset`·`reference_today`·`reference_today_info`(2.4) | ~70 |
| 신규 | `tests/test_reference_day.py` | 활동 없음 → 서버 로컬, 최근 활동 +7·UTC 날짜 경계, Strava 텍스트 오프셋, CSV 행 오프셋, `now_utc` 주입 결정성 | ~70 |

v1 의존: `src/web/`(v1) 7개 파일이 `[:10]` 절단을 쓴다. 2.2로 저장값이 무접미사 현지 시각이 되면 v1도 같이 맞아지고 깨지는 부분은 없다. 2.1의 `computed_at` 형식 변경은 v1이 이 필드를 직접 잘라 쓰는지 구현 시 grep으로 확인한다(v1 제거 예정이므로 수정은 하지 않고 깨지면 기록만).

## 4. 단계와 검증

1. **조사(코드 무변경)**: 로컬 개발 DB 사본에서 `start_time LIKE '%Z' OR LIKE '%+00:00'` 행 수를 소스별로 집계하고, 1327의 `source_payloads` 원본과 대조해 RC-2 경로를 확정한다. 운영 DB는 쓰지 않는다.
2. **`timefmt.py` + 단위 테스트** → `pytest tests/test_timefmt.py`.
3. **C-06 적용**(2.1 + 2.3) → `pytest tests/`. 브라우저: `/coach`에서 근거 시트를 열고 "계산" 시각이 `metric_store.updated_at`+9h와 같은지 확인. `/today` 동기화 시각이 회귀하지 않았는지 확인.
4. **S-17 신규 수집 경로 적용**(extractor·FIT) → extractor 테스트에 `start_date_local`(가짜 Z)과 `start_date`만 있는 픽스처를 둘 다 둔다. dedup 테스트 전체 통과 확인.
4-1. **Strava CSV 활동별 timezone(2.2.1)**: 단계 1 조사에 "같은 `source_id`에 API payload가 있는 CSV 행 수 / 없는 행 수", `timezone`·`utc_offset` 채움률, **TZ-8 대상 예상 건수**(API payload 없음 ∧ 교차 소스 매칭 없음 ∧ 같은 날 확인 활동 없음 = 5b 행 수, 그중 연결 무효 사용자 기준)를 추가한다. `strava_tz.py` + 테스트 → `pytest tests/test_strava_tz.py tests/test_strava_csv*.py`. 검증: (a) config 없고 다른 소스·같은 날 활동 없음 → 지금과 같은 값, `tz_source="fallback"`, (b) API payload 있는 해외 활동 → `start_date_local`, (c) 연결 유효/무효 모두 가져오기 중 네트워크 호출 0회(`refresh_token` 판정 제외)·`tz_lookup_status`·`tz_backfill_pending` 기록, (d) API 행에 CSV 재가져오기 → `start_time` 유지, (e) 같은 활동의 Garmin payload(방콕 +7) → `peer_direct:garmin`, (f) 같은 활동은 없고 같은 날 앞 Garmin(+7)·뒤 Intervals(+7) → `neighbor:garmin`(+7), 앞뒤 +7/+9 → UTC 순시가 가까운 쪽 값(TZ-14)·`tz_peer`에 두 후보, 다른 날 활동만 있음 → `fallback`, `neighbor`/`fallback` 행은 차용 제공자가 되지 않음, (g) 상세 응답 `tz_estimated`는 `fallback` 행만 참(`neighbor`·`peer_derived`는 거짓), (h) 결과 요약 재연결 링크는 연결 무효일 때만.
4-3. **백필·자동 재교정(2.2.3, TZ-7·9)** → `pytest tests/test_tz_backfill.py`. 검증: (a) 연결 무효 → 호출 0회·변경 0, (b) 대상 120건·상한 50 → API 최대 50회, 다음 실행이 나머지 처리, (c) 429 → 즉시 중단·`stopped_reason`, 끝난 행은 커밋 유지, (d) 체인 1~3으로 풀리는 행은 API 미호출, (e) 값 변경 행은 `tz_history`에 prev/new·group 기록, 같은 값은 이력 없음, (f) 2회 연속 실행 → 두 번째 변경 0·이력 0(멱등), (g) `--revert-run` → `start_time`·`tz_source`·group 원복, `tz_pinned` 행은 재교정 제외, (h) dedup 그룹 변화 행 → 자동 적용·`group_changed` 집계·`tz_history`에 prev/new group(TZ-13), (i) 404 3회 → 대상 제외, (j) 날짜 경계: UTC 6/30 15:30 활동이 KST 7/1 00:30 → +2(6/30 17:30) 교정 시 `date_changed` 집계, (k) `offline_only=True` → API 호출 0회·체인 1~3·5a로 풀리는 행만 변경(TZ-15).
4-2. **교차 소스 인덱스(2.2.2, TZ-6)**: 단계 1 조사에 추가 — Garmin `activity_summary`의 `startTimeGMT` 채움률, Intervals 원본의 `start_date`·`timezone` 키 유무, Runalyze `datetime`의 오프셋 접미사 유무, Strava CSV 행 중 UTC 순시로 다른 소스와 매칭되는 비율(허용오차 30/60/120/420초별 집계 — TZ-10 60초 상수 조정 근거). `tz_peers.py` + 테스트 → `pytest tests/test_tz_peers.py tests/test_dedup*.py`. 단위 테스트:
   - Garmin 있음: Strava CSV UTC 01:00Z, Garmin GMT 01:00:20/Local 08:00:20(+7) → 오프셋 +25200, 대상 현지 = 08:00:00(제공자 시각 복사 아님).
   - Garmin 없음: Intervals만 있음 → `peer_direct:intervals` / 아무 소스 없음 → `None`(에러 없음) → 체인 다음 단계.
   - 허용오차 경계: 순시 차 = 허용오차 → 채택, 허용오차 + 1초 → 미채택. 거리 불일치(규칙 밖) → 미채택.
   - 소스 간 오프셋 충돌: Garmin +9 / Intervals +8 → Garmin +9 채택(TZ-11 소스 우선순위), `conflicts`에 두 후보 기록.
   - 등급: Garmin direct +9와 Runalyze derived +7 → direct 채택, 충돌로 세지 않음. Runalyze만 있고 창 안 후보 2건 → 포기.
   - 오프셋 검증: local−GMT가 +9h 03분(반올림 오차 > 120초) → 후보 제외, +15h → 제외.
   - 순환 방지: 대상과 같은 `matched_group_id`지만 UTC 순시가 허용오차 밖인 행 → 채택 안 함. 그룹 없는 행도 순시로 매칭됨.
   - 외부 호출 0: `PeerTzIndex`는 `conn` 외 의존성 없음(네트워크 모의 객체 호출 0회 단언).
4-4. **TZ-8 UI**: 단계 1 건수 확인 후 진행. 브라우저: `fallback` 픽스처 활동 상세 헤더에 "시간대 추정" 표기, `neighbor`/정확 행은 미표기, 가져오기 결과 요약 문구는 `fallback` ≥1건일 때만.
5. **기존 행 교정**(TZ-3 부분 결정: dry-run 선행, 적용 범위는 결과 확인 후 확정. TZ-9 자동 재교정과 별개 — 2.2.3 "TZ-3과의 관계") — Strava CSV 행은 2.2.1 dry-run 목록(예상 group 변화 포함)을 먼저 사용자에게 보인다. → 스크립트 dry-run 출력 검토 후 적용. 브라우저: `/library/1327` 헤더가 "7/1(월)"인지, Garmin/Intervals 활동 날짜가 그대로인지, 목록 월 그룹(`activities/+page.svelte:220`)의 경계 확인.
5-1. **'오늘' 기준일 헬퍼(2.4, TZ-1 추가 결정)**: race-calendar·조정 신호 구현보다 먼저 `reference_day.py` + 테스트 → `pytest tests/test_reference_day.py`. 검증: 활동 0건 → 서버 로컬 날짜·`basis="server_local"`, 최근 활동 오프셋 +7에서 UTC 17:30 → 다음 날, KST 사용자는 서버 로컬(KST)과 같은 값, 외부 호출 0회.
6. `python3 scripts/check_docs.py`, `npm run check`(타입).

## 5. 대안 비교

| 안 | 내용 | 장점 | 단점 |
|---|---|---|---|
| **A (추천)** | 저장/직렬화 계약 분리: instant는 오프셋 ISO, 활동은 무접미사 현지 시각 | 근본 해결. 프론트 추측 제거, 소스별 차이 소멸, v1도 함께 교정 | 기존 행 교정 스크립트와 dedup 회귀 검증 필요 |
| B | 프론트만 수정: `stamp()`에 `parseDbTimestamp` 적용, 활동 날짜는 `Z`면 로컬 변환 | 변경 작음(프론트 2파일) | Strava API 가짜 `Z` 행을 9시간 밀어 정상 데이터를 깨뜨림. 소스별 의미 차이가 남아 재발 |

## 6. 결정 필요

- 결정 완료(표 참조: `decisions-table.md` TZ-1~16, 본문 D번호 = TZ번호). 남은 것: TZ-3 적용 범위(dry-run 결과 확인 후 확정, 단계 5).

## 7. 범위 밖 메모

- `format.ts`의 `formatDate()`는 사용처 0 — 제거 후보.
- `replanBanner.ts`, `wellnessDay.ts`, `onboarding.ts`, `RangeSyncForm.svelte` 등의 `new Date().toISOString().slice(0,10)`은 "오늘" 날짜를 UTC로 구해 KST 00~09시에 하루 전이 된다(별도 묶음 권장, coach plan 페이지는 이미 보정). TZ-1 추가 결정의 대상(날짜 전용 대회 필드)은 2.4 헬퍼가 맡고, 이 화면들의 전환 여부는 별도 묶음에서.
- `metrics/base.py:227,268`의 `datetime.now(timezone.utc)` 기본 종료일도 같은 경계 문제 가능성.

### 동기화 중 발견한 모호점
- TZ-14 동률(앞뒤 후보의 UTC 순시 차가 같음) 처리는 표에 없다. 본문은 규칙을 정하지 않았다.
- TZ-9 표 문구는 "폴백 행 재계산"이나, 본문 2.2.3 대상은 `fallback`·`neighbor:*`·`peer_derived:*`다(TZ-9 이후 추가된 등급 포함). 표 문구와 범위가 다르다.
- TZ-7·TZ-9 표 선택지 문구는 `tz_source='fallback_fixed'`를 쓰나 본문 값은 `fallback`이다(명칭 차이).
- TZ-2 결정에 "해외 사용자 폴백 정확도는 TZ-1 기록 결정과 함께 재검토"가 남아 있다. 본문 5b는 KST 고정 그대로다.
- TZ-13 자동 적용으로 `held` 보류가 사라졌으나 `tz_pinned`(되돌린 행 재교정 제외)는 TZ-9 안전장치로 유지했다. 표에는 `tz_pinned` 언급이 없다.
- TZ-4 상대시각의 기준 시점(렌더 시각, 갱신 주기)은 표에 없다.
- TZ-1 추가 결정 "최근 활동의 현지 날짜(시간대)"를 2.4는 "최근 활동의 시간대를 현재 순시에 적용한 날짜"로 해석했다(활동 날짜 자체를 오늘로 쓰는 해석이 아님) — 확인 필요.
- 2.4 '최근 활동'에 시간대 추정 행(`fallback`·`neighbor:*`·`peer_derived:*`)·오프셋 없는 활동을 포함할지, 건너뛰고 그 이전 활동을 볼지 표에 없다.
- 마지막 활동이 오래전(예: 여행 후 활동 없음)이면 그 시간대가 계속 쓰인다. 오래된 활동을 무시하고 서버 로컬로 폴백할 기한은 표에 없다.
- 체크인 `user_inputs.input_date` 등 '오늘'로 저장되는 기존 날짜 값이 같은 헬퍼를 쓸지(TZ-1 추가 결정의 열거 대상 밖)는 정해지지 않았다.
