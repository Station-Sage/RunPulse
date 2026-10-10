# 설계: 시간대 표기 (UTC 표기·날짜 절단)

- 대상 ID: C-06 (코치 답변 근거 시트 "계산 시각" 9시간 어긋남), S-17 (Strava 단독 활동 상세 헤더 날짜가 KST 자정 경계에서 틀림)
- 상태: 설계 초안 (구현 전, 사용자 결정 필요 항목 있음)
- 관련 ADR: ADR-006 (Strava `start_date_local` 우선 — 활동 시각은 "현지 벽시계"가 기준이라는 기존 결정), ADR-009 (Calculator 무변경, 해당 없음)

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
- `src/utils/timefmt.py`에 `to_local_wallclock(local: str | None, utc: str | None, offset_sec: int | None) -> str | None` 추가. 우선순위: 소스가 준 현지 시각(가짜 `Z` 제거) → `utc + offset` → (offset 미상) 결정 필요 D2.
- 적용: `strava_extractor.py:30`, `intervals_extractor.py:34`, `garmin_extractor.py:42`, `import_history.py:107`(FIT: `timestamp`+`local_timestamp` 메시지 활용 가능 여부 확인).
- 기존 행 교정: `source_payloads` 원본에서 재추출하는 1회성 스크립트(`scripts/normalize_start_time.py`, dry-run 기본). dedup 매칭 키에 영향이 있으므로 실행 여부·범위는 결정 필요 D3.

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

v1 의존: `src/web/`(v1) 7개 파일이 `[:10]` 절단을 쓴다. 2.2로 저장값이 무접미사 현지 시각이 되면 v1도 같이 맞아지고 깨지는 부분은 없다. 2.1의 `computed_at` 형식 변경은 v1이 이 필드를 직접 잘라 쓰는지 구현 시 grep으로 확인한다(v1 제거 예정이므로 수정은 하지 않고 깨지면 기록만).

## 4. 단계와 검증

1. **조사(코드 무변경)**: 로컬 개발 DB 사본에서 `start_time LIKE '%Z' OR LIKE '%+00:00'` 행 수를 소스별로 집계하고, 1327의 `source_payloads` 원본과 대조해 RC-2 경로를 확정한다. 운영 DB는 쓰지 않는다.
2. **`timefmt.py` + 단위 테스트** → `pytest tests/test_timefmt.py`.
3. **C-06 적용**(2.1 + 2.3) → `pytest tests/`. 브라우저: `/coach`에서 근거 시트를 열고 "계산" 시각이 `metric_store.updated_at`+9h와 같은지 확인. `/today` 동기화 시각이 회귀하지 않았는지 확인.
4. **S-17 신규 수집 경로 적용**(extractor·FIT) → extractor 테스트에 `start_date_local`(가짜 Z)과 `start_date`만 있는 픽스처를 둘 다 둔다. dedup 테스트 전체 통과 확인.
5. **기존 행 교정**(D3 승인 시) → 스크립트 dry-run 출력 검토 후 적용. 브라우저: `/library/1327` 헤더가 "7/1(월)"인지, Garmin/Intervals 활동 날짜가 그대로인지, 목록 월 그룹(`activities/+page.svelte:220`)의 경계 확인.
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
- **D5. Strava CSV의 고정 오프셋(`_LOCAL_UTC_OFFSET`)**: 유지(현재 dedup 기준) vs 활동별 `timezone` 기반으로 교체(정확하나 CSV에 시간대 컬럼이 없어 API payload 조인 필요).

## 7. 범위 밖 메모

- `format.ts`의 `formatDate()`는 사용처 0 — 제거 후보.
- `replanBanner.ts`, `wellnessDay.ts`, `onboarding.ts`, `RangeSyncForm.svelte` 등의 `new Date().toISOString().slice(0,10)`은 "오늘" 날짜를 UTC로 구해 KST 00~09시에 하루 전이 된다(별도 묶음 권장, coach plan 페이지는 이미 보정).
- `metrics/base.py:227,268`의 `datetime.now(timezone.utc)` 기본 종료일도 같은 경계 문제 가능성.
