# 설계: 시간대 표기 (UTC 표기·날짜 절단)

- 대상 ID: C-06 (코치 답변 근거 시트 "계산 시각" 9시간 어긋남), S-17 (Strava 단독 활동 상세 헤더 날짜가 KST 자정 경계에서 틀림)
- 상태: 설계 초안 (구현 전. TZ-1·2·5·6 결정, TZ-3 부분 결정, D4·D6~D12 결정 필요)
- 관련 ADR: ADR-006 (Strava `start_date_local` 우선 — 활동 시각은 "현지 벽시계"가 기준이라는 기존 결정), ADR-009 (Calculator 무변경, 해당 없음)
- 결정 번호 대응: 본문 D1~D5 = `decisions-table.md`의 TZ-1~TZ-5. D6 이후는 이 문서에서 새로 생긴 결정 필요 항목(아직 표에 없음). TZ-6(교차 소스 참조)은 사용자 지시로 D6 일부를 확정한 것이며 `decisions-table.md`에는 아직 반영 전.

### 변경 이력
- 2026-10-11 TZ-5 결정 반영 (Strava CSV 고정 오프셋 → 활동별 timezone, Strava 연결 무효 시 폴백. 2.2.1 신설, 표·단계·검증·결정 필요 갱신, D6~D9 추가)
- 2026-10-11 TZ-6 교차 소스 참조 반영 (Strava 연결 무효여도 같은 활동의 다른 소스 현지 시각/오프셋을 우선 폴백으로 사용. 2.2.2 신설, 체인 5단계로 재배치, D6 범위 축소, D7~D9 영향 기술, D10~D12 추가)

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

**우선순위 체인 (TZ-6 반영, 5단계)** — 신규 `src/import_export/strava_tz.py`의 `resolve_strava_start(conn, source_id, utc_naive, distance_m, *, api=None, fit_local=None, peers=None) -> tuple[str, str]` (반환: 무접미사 현지 벽시계, `tz_source`). `peers`는 2.2.2의 `PeerTzIndex`(없으면 체인 3 생략).

| 순서 | 출처 | 방법 | 네트워크 | `tz_source` |
|---|---|---|---|---|
| 1 | 저장된 Strava API payload | 같은 `source_id`의 `source_payloads`(`activity_detail` → `activity_summary`)에서 `start_date_local`(가짜 `Z` 제거) 사용. 없으면 `start_date`+`utc_offset` | 없음 | `api_payload` |
| 2 | CSV/ZIP 내 단서 | ZIP 가져오기에 FIT 원본이 있으면 `local_timestamp`(TZ-2 규칙 재사용). 단독 CSV에는 시간대 컬럼이 없으므로 이 단계 없음 | 없음 | `fit_local` |
| 3 | **다른 소스의 같은 활동 (TZ-6)** | 2.2.2. Garmin·Intervals·Runalyze 행 중 UTC 순시가 허용오차 안이고 거리가 맞는 활동의 오프셋(현지 벽시계 − UTC)을 빌림 | 없음(DB 내부만) | `peer_direct:{source}` / `peer_derived:{source}` |
| 4 | Strava API 조회 (연결 유효 시만) | `GET /activities/{id}` 결과를 `upsert_raw_payload(..., "activity_detail", ...)`로 저장한 뒤 1과 같은 규칙. 조회 시점은 D7 | 있음 | `api_fetch` |
| 5 | 최종 폴백 | 값은 D6(선택지 유지) | 없음 | `fallback_fixed` (D6 결과에 따라 `fallback_user`/`fallback_neighbor` 등) |

**순서 변경 이유 (TZ-5 대비)**
- 기존 순서는 "payload → API → FIT → 고정 오프셋"이었다. TZ-6로 **오프라인 단계를 모두 외부 호출 앞에** 둔다. 근거: (1) coding-rules의 "sync 중단 금지"와 Strava 한도(15분 100회·일 1,000회)를 고려하면 DB 안에서 풀리는 행은 API를 쓰지 않는 편이 낫다. (2) 사용자 지시의 핵심 상황이 "Strava 연결 무효"이므로 교차 소스는 연결 상태와 무관하게 항상 실행돼야 한다.
- FIT(2)를 교차 소스(3)보다 앞에 둔 이유: FIT `local_timestamp`는 **같은 활동의 원본 파일**이라 매칭 불확실성이 없다. 교차 소스는 "같은 활동인가"를 추정하는 단계라 한 단계 아래다.
- API 조회(4)를 교차 소스 뒤에 둔 이유: 교차 소스 중 `peer_direct`(소스가 현지 시각과 UTC를 둘 다 직접 준 값)는 정확도가 API와 사실상 같다(대개 같은 기기 기록이 각 플랫폼으로 전파된 것). 단 `peer_derived`(추정)만 얻었을 때는 API 조회로 덮어쓸 가치가 있으므로, **체인 3 결과가 `peer_derived`이고 연결이 유효하면 체인 4를 계속 시도**한다(성공 시 `api_fetch`가 이김).

규칙:
1. 체인 1·2·3·5는 네트워크 없이 끝난다. 4만 외부 호출이며 실패(401/403/429/네트워크)는 coding-rules대로 재시도 1회 → 로그 → 폴백으로 계속 진행(가져오기 중단 금지). 401은 그 가져오기 세션에서 `api_unavailable`로 표시하고 남은 행은 4단계를 건너뛴다.
2. CSV payload(`csv_export`)에 `start_date_utc`(CSV 원본 UTC)와 `tz_source`, 교차 소스로 풀린 경우 `tz_peer`(`{"source", "source_id", "offset_sec", "delta_sec"}`)를 추가 저장한다. DDL 변경 없음(JSON 필드 추가). 이 값들이 나중 재교정·감사의 입력이 된다.
3. `tz_source`가 `fallback_*` 또는 `peer_derived:*`인 행은 "시간대 추정" 상태다. 사용자 노출(가져오기 결과 요약·활동 상세 표시 여부·문구)은 D8.
4. 기존 행 갱신 규칙: CSV가 기존 행의 `start_time`을 바꾸는 것은 새 값의 `tz_source` 신뢰 등급이 기존 값보다 **같거나 높을 때만** 허용한다. 등급(높음→낮음): `api_payload` = `api_fetch` = `fit_local` > `peer_direct:*` > `peer_derived:*` > `fallback_*`. 즉 API 경로로 들어온 행은 CSV의 교차 소스·폴백값으로 덮어쓰지 않는다. `_fill_null_fields`의 강제 갱신도 같은 규칙을 따른다. 등급 표는 `strava_tz.TZ_SOURCE_RANK` 상수 1곳에 둔다.

**연결 유효성 인터페이스** — 기존 판정을 재사용하고 새 판정 로직은 만들지 않는다.
- `strava_tz.StravaTzLookup` (얇은 래퍼): `available: bool`, `status: str`, `fetch(source_id) -> dict | None`.
  - 생성 시 `config`가 없으면(가져오기 호출자가 안 넘김) `available=False, status="config 없음"`.
  - `check_strava_connection(config)["ok"]`가 False면 `available=False`, `status`는 그 반환값(`"설정 누락"`/`"재연동 필요"`).
  - `ok=True`면 `refresh_token(config)`를 1회 호출. 실패 시 `classify_exception()` 코드가 `auth_expired`면 `available=False, status="auth_expired"`.
  - `fetch()`는 `rate_limiter.py`를 거친다. 실행 중 401이 나오면 `available=False`로 전환.
- `import_strava_activities(conn, path, ..., config: dict | None = None)`와 `import_strava_archive(...)`에 선택 인자 `config` 추가. 기본값 None이라 기존 호출자(v1 `views_export_import.py` 포함)는 수정 없이 "저장 payload → FIT → 폴백" 체인으로 동작한다. v2 `import_service.apply_import()`만 config를 넘긴다.
- 반환 dict에 `tz_resolved: {"api_payload": n, "fit_local": n, "peer_direct": n, "peer_derived": n, "api_fetch": n, "fallback": n}`, `tz_lookup_status: str`, `tz_peer_conflicts: n` 추가. 로그는 `[strava_csv] 시간대 교차소스 N건·폴백 M건 (Strava 연결: {status})` 한 줄(행별 로그 금지).

**연결 무효 시 동작 요약 (TZ-6 반영)**: API 조회 생략 → 저장된 payload가 있는 행은 정확 → 없는 행은 Garmin·Intervals·Runalyze에 같은 활동이 있으면 그 오프셋으로 교정 → 어느 소스에도 없는 "Strava 단독" 활동만 최종 폴백 → 결과 요약에 교차소스/폴백 건수·연결 상태 → 재교정은 D9(수동 스크립트 `normalize_start_time.py --source strava --tz-source fallback` 또는 동기화 후 자동).

**dedup 영향 (TZ-3 dry-run과 연결)**
- KST 활동은 체인 어느 단계든 결과가 지금(+9h)과 같다 → `start_time`·`group_id` 무변화.
- KST 밖에서 한 활동만 바뀐다(예: 도쿄 +9는 동일, 방콕 +7은 −2h, 유럽은 −7~−8h). 이 행들은 지금 Garmin `startTimeLocal`과 시간 차가 커서 `dedup._TIME_TOLERANCE`(7분)를 넘어 **매칭이 안 되던** 행이다. 교정 후 새로 매칭되어 group 병합이 생길 수 있다(분리는 드묾).
- `normalize_start_time.py --dry-run` 출력에 Strava CSV 행용 항목을 추가: `source_id`, 기존/신규 `start_time`, `tz_source`, 기존/예상 `group_id`. 예상 group은 `dedup.is_duplicate` 재평가로 산출하고 DB에 쓰지 않는다. 사용자가 이 목록을 보고 TZ-3 일괄 교정 여부를 정한다.
- "다른 시간대에서 한 활동"은 체인 1~4 중 하나가 있으면 정확, 최종 폴백이면 D6 값으로 남는다 — TZ-6 이후 연결 무효 사용자에게 남는 오차는 "Strava에만 있는 해외 활동"뿐이며 `tz_source`로 식별 가능하다.
- 교차 소스(체인 3)는 dedup 결과에 **의존하지 않는다**(2.2.2 순환 방지). 교정된 `start_time`으로 dedup이 다시 판정되는 것은 한 방향(시간대 → dedup)뿐이다.

**호환성**: v1(`src/web/views_export_import.py`)은 config 없이 호출하므로 API 조회 없이 동작, 수정하지 않는다(v1 제거 예정). v1 경로도 `peers`는 내부에서 기본 생성하므로 교차 소스 교정은 함께 받는다(외부 호출 없음). 저장 형식은 무접미사 현지 시각 그대로라 v1 `[:10]` 절단과 충돌 없음. `_LOCAL_UTC_OFFSET` 상수는 폴백 값으로 남기되(D6 결과로 값/이름 변경 가능) 모듈 주석의 "dedup 기준" 설명을 "체인 5단계 최종 폴백"으로 바꾼다.

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
2. **UTC 순시 경로 (기본)** — `PeerTzIndex`가 제공자 소스들의 `activity_summary` payload를 한 번에 읽어 `(utc_instant, local_wallclock|None, distance_m, source, source_id, grade)` 목록을 UTC 순으로 정렬해 둔다. 대상마다 `bisect`로 `|utc_peer − utc_target| ≤ 허용오차(D10)` 후보를 찾고, 거리 조건은 `dedup.is_duplicate`의 거리 규칙을 재사용한다(시간 비교는 이 경로가 대신하므로 거리 함수만 분리 호출. dedup 모듈 변경은 거리 판정 헬퍼를 공개 함수로 꺼내는 정도).
   - 수천 건 CSV에서도 payload 조회는 제공자 소스별 1회 쿼리 + 메모리 이분 탐색이라 O((N+M) log M). 행마다 SQL을 날리지 않는다.
   - derived 제공자(Runalyze 현지만)는 UTC가 없어 순시 비교가 불가하다. 대신 `local_peer − utc_target`이 −12h~+14h 안이고 15분 배수 ± 허용오차(D10)인 후보를 찾되, 그 창 안에서 거리 조건까지 통과하는 Runalyze 활동이 **정확히 1건일 때만** 채택한다(같은 날 비슷한 거리 활동이 2건 이상이면 오프셋이 달라질 수 있어 포기). 단순 경로(그룹)에서 후보가 Runalyze뿐일 때도 같은 규칙.

**오프셋 계산**
- `offset_sec = local_wallclock − utc_instant`(초). 실제 시간대는 15분 단위이므로 가장 가까운 900초 배수로 반올림하고, 반올림 오차가 120초를 넘거나 범위(−12h~+14h)를 벗어나면 그 후보를 버린다(기록 지연·파싱 오류 방지).
- 대상의 현지 벽시계 = `utc_target + offset_sec`. 제공자의 현지 시각을 그대로 복사하지 **않는다**(소스 간 시작 시각이 수 초~수십 초 다를 수 있으므로 대상 자신의 UTC를 기준으로 한다).

**소스 간 오프셋 충돌 시 우선순위**
1. 등급: `direct`(소스가 현지 시각과 UTC를 함께 줌: Garmin, Intervals, 접미사 있는 Runalyze, `local_timestamp` 있는 FIT) > `derived`(현지만 있어 역산).
2. 같은 등급 안에서 오프셋이 모두 같으면 채택, `tz_source`에는 순시 차가 가장 작은 제공자를 기록.
3. 같은 등급 안에서 오프셋이 다르면 처리 방식은 **D11**(선택지: 소스 우선순위 고정 / 순시 차 최소 / 충돌로 보고 다음 단계로). 충돌 건수는 `tz_peer_conflicts`로 집계하고 payload `tz_peer`에 후보 전부를 남긴다.
4. 상위 등급 결과가 있으면 하위 등급 후보는 비교하지 않는다(충돌로 세지 않음).

**인터페이스 (삼성헬스 등 향후 소스 흡수 방식)** — 신규 `src/utils/tz_peers.py`
- `PeerTime` (dataclass): `source, source_id, utc: datetime | None, local: datetime | None, distance_m: float | None, grade: Literal["direct","derived"]`.
- `_PEER_READERS: dict[str, Callable[[dict], PeerTime | None]]` — 소스별 **payload → PeerTime** 순수 함수 등록표. 현재 `garmin`(startTimeGMT/startTimeLocal), `intervals`(start_date/start_date_local), `runalyze`(datetime, 접미사 판별). 새 소스(예: 삼성헬스)가 생기면 해당 sync가 `source_payloads`에 `activity_summary`를 저장하고 reader 1개를 등록하는 것만으로 체인 3에 합류한다. Strava는 대상 자신이므로 등록하지 않되, 다른 대상(예: FIT 가져오기)을 위해 `strava` reader를 등록할지는 D12.
- `PeerTzIndex.build(conn, exclude_sources: set[str]) -> PeerTzIndex` / `lookup(utc_target, distance_m, group_id=None) -> PeerMatch | None` (`PeerMatch`: `offset_sec, grade, source, source_id, delta_sec, conflicts: list`).
- DB 접근은 `source_payloads` 읽기 전용, 외부 호출 없음. 데이터가 없으면 `None`(에러 없음).
- `strava_tz.py`는 이를 호출만 한다. 파일 300줄 규칙상 매칭 로직을 `strava_tz.py`에 넣지 않는다.

**적용 범위**: 이번 범위는 Strava CSV/ZIP(체인 3). 같은 인덱스를 FIT 가져오기(TZ-2의 "FIT 현지 시각 없음 → KST" 사이)에도 끼워 넣을 수 있으나 범위 확장 여부는 D12.

**다른 결정에 미치는 영향**
- D6: 최종 폴백이 적용되는 행이 "어느 소스에도 같은 활동이 없는 Strava 단독 활동"으로 줄어든다. 폴백 값 선택의 영향 범위가 작아진다.
- D7: 교차 소스는 연결 상태와 무관하게 DB 안에서 끝나므로, Garmin/Intervals를 함께 쓰는 사용자는 API 조회 대상이 크게 준다. (a) 동기 조회의 한도 위험이 줄고, (c) "조회하지 않음"을 택해도 정확도 손실이 작아진다.
- D8: "시간대 추정" 표시 대상이 `fallback_*`와 `peer_derived:*`로 한정된다. `peer_direct`는 확정으로 취급할지, "Garmin 기록 기준" 같은 출처 표시를 둘지가 D8 문구에 추가된다.
- D9: 재교정 계기에 "Strava 재연결" 외에 **"다른 소스 동기화로 같은 활동이 새로 들어옴"**이 생긴다. 이 계기는 외부 호출 없이 재계산 가능하므로 (a) 자동을 택해도 비용이 작다. 대신 날짜·dedup 그룹이 예고 없이 바뀌는 위험은 같다.

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
| 신규 | `tests/test_strava_tz.py` | 체인 5단계 각각(교차 소스 포함), 연결 무효(설정 누락/재연동 필요/401), 가져오기 중 401 전환, 우선순위 낮은 값의 덮어쓰기 금지 | ~120 |
| 수정 | `src/import_export/strava_csv.py` (488줄, 이미 300줄 초과) | `_parse_strava_date`가 UTC를 반환하고 현지화는 `strava_tz`에 위임, payload에 `start_date_utc`·`tz_source`, 기존 행 갱신 규칙, `config` 인자, 반환 dict 확장. 새 로직은 `strava_tz.py`로 빼서 순증을 막음 | −10/+25 |
| 수정 | `src/import_export/strava_archive.py` | `config` 전달, FIT `local_timestamp`를 체인 3에 전달 | +10 |
| 수정 | `src/services/import_service.py` | Strava 가져오기에 config 전달, 결과의 `tz_resolved`·`tz_lookup_status` 노출 | +5 |
| 수정 | `scripts/normalize_start_time.py` (신규 파일에 포함) | `--source strava --tz-source` 필터, CSV 행의 예상 group_id 출력, 교차 소스 결과(`tz_peer` 제공자·순시 차·충돌) 열 | +40 |
| 신규 | `src/utils/tz_peers.py` | TZ-6: `PeerTime`, `_PEER_READERS`(garmin/intervals/runalyze), `PeerTzIndex.build/lookup`, 오프셋 반올림·범위 검증, 충돌 처리(D11) | ~150 |
| 신규 | `tests/test_tz_peers.py` | TZ-6 교차 소스 매칭 단위 테스트(4단계 검증 목록) | ~150 |
| 수정 | `src/utils/dedup.py` | `is_duplicate`의 거리 판정을 공개 헬퍼(`distance_matches`)로 분리, 기존 동작 무변화 | ±10 |
| 수정 | `src/import_export/strava_tz.py` (위 신규에 포함) | 체인 5단계 재배치, `peers` 인자, `TZ_SOURCE_RANK` | +30 |
| 수정 | 프론트 가져오기 결과 화면(v2, 구현 시 grep) | 폴백 건수·연결 상태 안내 (문구는 D8) | +10 |
| 수정 | `tests/test_strava_csv*.py` | 기존 +9h 단언을 "저장 payload 없음+config 없음 → 폴백" 케이스로 이동, API 행 보존 케이스 추가 | +40 |

v1 의존: `src/web/`(v1) 7개 파일이 `[:10]` 절단을 쓴다. 2.2로 저장값이 무접미사 현지 시각이 되면 v1도 같이 맞아지고 깨지는 부분은 없다. 2.1의 `computed_at` 형식 변경은 v1이 이 필드를 직접 잘라 쓰는지 구현 시 grep으로 확인한다(v1 제거 예정이므로 수정은 하지 않고 깨지면 기록만).

## 4. 단계와 검증

1. **조사(코드 무변경)**: 로컬 개발 DB 사본에서 `start_time LIKE '%Z' OR LIKE '%+00:00'` 행 수를 소스별로 집계하고, 1327의 `source_payloads` 원본과 대조해 RC-2 경로를 확정한다. 운영 DB는 쓰지 않는다.
2. **`timefmt.py` + 단위 테스트** → `pytest tests/test_timefmt.py`.
3. **C-06 적용**(2.1 + 2.3) → `pytest tests/`. 브라우저: `/coach`에서 근거 시트를 열고 "계산" 시각이 `metric_store.updated_at`+9h와 같은지 확인. `/today` 동기화 시각이 회귀하지 않았는지 확인.
4. **S-17 신규 수집 경로 적용**(extractor·FIT) → extractor 테스트에 `start_date_local`(가짜 Z)과 `start_date`만 있는 픽스처를 둘 다 둔다. dedup 테스트 전체 통과 확인.
4-1. **Strava CSV 활동별 timezone(2.2.1)**: 단계 1 조사에 "같은 `source_id`에 API payload가 있는 CSV 행 수 / 없는 행 수", `activity_summary` payload의 `timezone`·`utc_offset` 채움률을 추가한다. `strava_tz.py` + 테스트 → `pytest tests/test_strava_tz.py tests/test_strava_csv*.py`. 검증: (a) config 없고 다른 소스도 없음 → 결과가 지금과 같음(폴백), (b) API payload가 있는 해외 활동 픽스처 → `start_date_local` 사용, (c) 연결 무효 config(`refresh_token` 없음, 401 모의) → 네트워크 호출 0회·가져오기 완료·`tz_lookup_status` 기록, (d) API로 들어온 행에 CSV 재가져오기 → `start_time` 유지, (e) 연결 무효 + 같은 활동의 Garmin payload 있음(방콕 +7) → 네트워크 호출 0회로 `peer_direct:garmin`, (f) 체인 3이 `peer_derived`이고 연결 유효 → 체인 4 시도·성공 시 `api_fetch`로 교체.
4-2. **교차 소스 인덱스(2.2.2, TZ-6)**: 단계 1 조사에 추가 — Garmin `activity_summary`의 `startTimeGMT` 채움률, Intervals 원본의 `start_date`·`timezone` 키 유무, Runalyze `datetime`의 오프셋 접미사 유무, Strava CSV 행 중 UTC 순시로 다른 소스와 매칭되는 비율(허용오차 30/60/120/420초별 집계 — D10 판단 자료). `tz_peers.py` + 테스트 → `pytest tests/test_tz_peers.py tests/test_dedup*.py`. 단위 테스트:
   - Garmin 있음: Strava CSV UTC 01:00Z, Garmin GMT 01:00:20/Local 08:00:20(+7) → 오프셋 +25200, 대상 현지 = 08:00:00(제공자 시각 복사 아님).
   - Garmin 없음: Intervals만 있음 → `peer_direct:intervals` / 아무 소스 없음 → `None`(에러 없음) → 체인 다음 단계.
   - 허용오차 경계: 순시 차 = 허용오차 → 채택, 허용오차 + 1초 → 미채택. 거리 불일치(규칙 밖) → 미채택.
   - 소스 간 오프셋 충돌: Garmin +9 / Intervals +8 → D11 정책별 기대값(정책을 파라미터로 둬 세 선택지 모두 테스트), `conflicts`에 두 후보 기록.
   - 등급: Garmin direct +9와 Runalyze derived +7 → direct 채택, 충돌로 세지 않음. Runalyze만 있고 창 안 후보 2건 → 포기.
   - 오프셋 검증: local−GMT가 +9h 03분(반올림 오차 > 120초) → 후보 제외, +15h → 제외.
   - 순환 방지: 대상과 같은 `matched_group_id`지만 UTC 순시가 허용오차 밖인 행 → 채택 안 함. 그룹 없는 행도 순시로 매칭됨.
   - 외부 호출 0: `PeerTzIndex`는 `conn` 외 의존성 없음(네트워크 모의 객체 호출 0회 단언).
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

- **D6. 최종 폴백 오프셋 값(체인 5단계)** — TZ-6(2026-10-11)으로 "다른 소스의 같은 활동"이 체인 3단계 폴백으로 확정됐다(2.2.2). D6에는 **교차 소스로도 못 찾은 Strava 단독 활동**에 쓸 최종 값만 남는다(적용 행 수가 크게 줄어 영향 범위도 작다): (a) KST +9 고정 — 현재 동작·TZ-2 폴백과 같아 dedup 결과 무변화, 해외 거주 사용자는 전부 틀림 / (b) 서버 프로세스 로컬 시간대 — 설정 불필요, 컨테이너 TZ(대개 UTC)에 따라 오히려 나빠질 수 있음 / (c) 사용자 설정 시간대 — 가장 정확, 설정 항목 신설 필요(TZ-1에서 사용자 설정은 채택 안 됨) / (d) 같은 날 앞뒤 활동 중 timezone이 확인된 활동의 값을 빌림 — 여행 중 정확도가 높지만 추론 규칙이 복잡하고 설명하기 어려움. TZ-6 이후에는 `PeerTzIndex`가 이미 다른 소스 활동의 오프셋을 메모리에 들고 있어 구현 비용은 줄지만, "같은 활동"이 아닌 "근처 활동"이라 이동일(출국·귀국일)에 틀릴 수 있다.
- **D7. API 조회(체인 4단계, TZ-6 재배치) 시점**: (a) 가져오기 요청 안에서 동기 조회 — 즉시 정확, 수천 건 CSV면 Strava 한도(15분 100회·일 1,000회)에 걸려 가져오기가 길어지거나 대부분 폴백 / (b) 가져오기는 폴백으로 끝내고 별도 백필 작업이 `tz_source`가 `fallback_*`·`peer_derived:*`인 행을 한도 안에서 점진 조회 — 응답 빠르고 한도 안전, 교정이 늦게 반영되고 그 사이 날짜가 바뀌어 보일 수 있음 / (c) 조회하지 않음(저장 payload만) — 외부 호출 0, Strava API 동기화로 이미 들어온 활동만 정확.
- **D8. 연결 무효 시 사용자 안내**: 노출 위치 (a) 가져오기 결과 요약에만 "N건은 시간대를 확인하지 못해 한국 시간으로 저장했어요" / (b) (a) + 해당 활동 상세 헤더에 "시간대 추정" 표시 / (c) 로그만(UI 없음). (b)는 정직하지만 KST 사용자에겐 대부분 불필요한 표시가 늘고, (c)는 해외 활동 날짜 오류를 사용자가 알 수 없다. 문구와 "Strava 다시 연결" 링크 동반 여부도 함께.
- **D9. 연결 복구 후 재교정**: (a) 자동 — 재연결 후 첫 동기화(또는 D7-b 백필)가 `fallback_fixed` 행을 재계산 — 사용자 수고 없음, 과거 활동 날짜·dedup 그룹이 예고 없이 바뀔 수 있음 / (b) 수동 — 데이터 화면이나 스크립트에서 dry-run 확인 후 적용(TZ-3 원칙과 일관) — 안전, 사용자가 기능을 모르면 영구 미교정 / (c) 자동이되 KST와 결과가 같은 행은 조용히 확정, 바뀌는 행만 확인 요청 — 절충, 구현 범위 가장 큼.

D7~D9에 대한 TZ-6 영향: D7 — 교차 소스는 연결 무효에서도 외부 호출 없이 끝나므로 API 조회 대상이 줄고 (c)의 손실이 작아짐. D8 — 추정 표시 대상이 `fallback_*`·`peer_derived:*`로 한정, `peer_direct` 출처 표시 여부가 문구 결정에 추가. D9 — 재교정 계기에 "다른 소스 동기화로 같은 활동 유입"이 추가(외부 호출 없음). 상세는 2.2.2 "다른 결정에 미치는 영향".

아래 D10~D12는 TZ-6 설계로 새로 생긴 항목이다.

- **D10. 교차 소스 매칭 허용오차(UTC 순시 차)**: (a) 60초 — 같은 기기 기록이 여러 플랫폼으로 전파된 경우(대부분) 충분, 오매칭 거의 없음, 기기 2대 동시 기록(시계+폰)은 놓칠 수 있음 / (b) 120초 — 수동 시작 차이까지 흡수, 오매칭 위험 여전히 낮음 / (c) 420초(dedup `_TIME_TOLERANCE` 7분과 동일) — 개념 하나로 통일·설명 쉬움, 짧은 간격 연속 활동(워밍업→본운동)을 잘못 잡을 위험이 가장 큼(거리 조건이 일부 막음). 단계 4-2의 허용오차별 매칭률 집계를 보고 정하는 것을 권장.
- **D11. 같은 등급 소스 간 오프셋 충돌 처리**: (a) 소스 우선순위 고정 — `dedup._SOURCE_PRIORITY`(garmin 1 > intervals 2 > runalyze 4) 재사용, 결정적·단순, Garmin 기기 시간대 설정이 틀린 경우 그대로 따라감 / (b) 대상과 UTC 순시 차가 가장 작은 제공자 — "가장 같은 기록"을 고름, 동률·초 단위 차이는 우연일 수 있어 근거가 약함 / (c) 충돌로 간주해 체인 3을 포기하고 다음 단계(API 조회→최종 폴백)로 — 가장 보수적, 충돌 행은 연결 무효 시 폴백값이 되어 TZ-6 효과가 줄어듦. 어느 쪽이든 후보 전체를 payload `tz_peer`에 남겨 사후 확인 가능.
- **D12. 교차 소스 적용 범위**: (a) Strava CSV/ZIP만 — 이번 문제(S-17·TZ-5)에 한정, 변경 최소 / (b) + FIT 가져오기(`import_history.py`, `local_timestamp` 없을 때 KST 폴백 앞) — TZ-2 폴백 행도 줄어듦, FIT 대상 시 Strava API payload도 제공자로 등록해야 해서 reader 1개 추가 / (c) + Runalyze 등 활동 소스 전반(자기 payload에 오프셋이 없는 경우) — 일관되지만 sync 경로(extractor 이후 단계)에 교차 조회가 들어가 동기화 순서 의존성이 생김(나중 소스가 들어오면 D9 재교정 필요).

## 7. 범위 밖 메모

- `format.ts`의 `formatDate()`는 사용처 0 — 제거 후보.
- `replanBanner.ts`, `wellnessDay.ts`, `onboarding.ts`, `RangeSyncForm.svelte` 등의 `new Date().toISOString().slice(0,10)`은 "오늘" 날짜를 UTC로 구해 KST 00~09시에 하루 전이 된다(별도 묶음 권장, coach plan 페이지는 이미 보정).
- `metrics/base.py:227,268`의 `datetime.now(timezone.utc)` 기본 종료일도 같은 경계 문제 가능성.
