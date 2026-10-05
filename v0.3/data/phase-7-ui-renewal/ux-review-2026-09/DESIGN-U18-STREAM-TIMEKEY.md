# DESIGN-U18 — 활동 스트림 시간키 (P7-DATA-STREAM-ELAPSED 후속)

상태: 설계 초안 · 2026-10-05 · system-architect · **(판단 필요) — 승인 전 구현 금지**
대상 백로그: `phase-7-ui-renewal/BACKLOG.md` `[P7-DATA-STREAM-ELAPSED]`(3104행)

## 0. 이미 설계·구현된 것 (재설계하지 않음, 인용만)

| 항목 | 내용 | 상태 |
|------|------|------|
| `P7-PRED-12` (`specs/PRED-1x-data-integrity.md` §P7-PRED-12) | Garmin 추출기가 `sumElapsedDuration` → `directElapsedDuration` 순으로 시간키를 고름(`STREAM_KEY_ALIASES`) | done (946639e) |
| `P7-PRED-13` (`src/sync/reextract.py`) | 활동 id 유지 제자리 재추출(스트림 DELETE+INSERT) | done (b71b0d4) |
| `P7-IMPL-STREAMS-TRUTH` | 프론트 `streamSeconds()` — 저장값 불신 시 총 시간 비례 환산 | done |

즉 백로그 원문의 "원인(샘플 인덱스 저장)"은 **이미 고쳐졌고 기존 행도 재추출됐다.** U18이 다루는 것은 그 뒤에 남은
문제 — 시간축의 **출처(provenance)가 저장되지 않아** 세 곳의 추정 휴리스틱이 지금은 *정상 데이터를 망가뜨리는* 상태 — 이다.

## 1. 현재 문제와 실측 근거

실측: 운영 DB 사본 `/tmp/real_u9.db`(2026-10-05 10:39) → `/tmp/u18_ro.db` 복사, `mode=ro` URI로만 읽음. 쓰기 없음.

### 1-1. 원 버그는 해소됨
- 활동 15302: 1692점, elapsed 0..8767, summary `elapsed_time_sec`=8767 → 정상(백로그 기록 시점 0..1691).
- Garmin 스트림 payload 594건 전부 시간키 4종 보유: `sumElapsedDuration, directTimestamp, sumDuration, sumMovingDuration`.
  `sumElapsedDuration`/`directElapsedDuration` 둘 다 없는 payload **0건** → 추출기 `else i`(인덱스) 분기는 현재 미발동.
- payload 내 시간 단조 감소 0건. 샘플 간격(Garmin 60활동): 1s 34k, 2s 45k, 3s 7.6k, 4s 4.8k, 5s+ 소수 → **비균등 1~4초**.
- 활동별 비교(최대 elapsed vs summary 시간, ±max(10s,2%)): Garmin 584/594 일치, Strava 98/98 일치.

### 1-2. 남은 문제 P1 — 휴리스틱 3중 복제가 정상 활동을 오변환 (실해)
같은 규칙("마지막 elapsed < 총시간×0.9 이면 인덱스로 보고 균등 재환산")이 세 곳에 있다:

| 위치 | 총시간 인자 |
|------|------------|
| `src/metrics/stream_utils.py` `sample_times()` → `moving_segments()` (decoupling·gap·relative_effort) | `elapsed_time_sec` 우선 |
| `src/metrics/segments.py` `repair_time_axis()` (classifier) | `elapsed_time_sec` 우선 |
| `frontend/src/lib/streamAxis.ts` `streamSeconds()` (스트림 탭) | `core.duration_sec` |

실측 오탐 6건(시간축은 정확한데 기록이 summary보다 짧음):
- **692 running**: 스트림 0..3215(payload `sumDuration`=3215, `directTimestamp` 폭 3215s), summary elapsed 4508 →
  dt가 ×1.40로 늘어나 **relative_effort 존 체류시간 1.4배 과대**, 스트림 탭 x축 왜곡.
- 수영 5건(737·743·748·819·17445): 풀 수영 휴식 구간이 스트림에 없음 → 같은 오변환(현재 수영 계산 영향은 U18c에서 확인).

원인 본질: 행에 "이 시간이 측정값인가"가 없어서 소비자가 매번 추측한다. 원 버그가 고쳐진 지금은 추측이 득보다 해.

### 1-3. 남은 문제 P2 — 출처 없는 조용한 폴백 (잠재)
`garmin_extractor.py:340` `elapsed = int(round(elapsed_raw)) if elapsed_raw is not None else i` — 키가 없는 기기/포맷이
오면 다시 인덱스가 저장되고 아무 표시도 남지 않는다. 같은 활동 안에서 일부 샘플만 None이면 시간축이 섞인다.

### 1-4. 남은 문제 P3 — 같은 초 중복 샘플 무표시 탈락 (경미)
`UNIQUE(activity_id, source, elapsed_sec)` + `upsert_streams_batch`의 `INSERT OR IGNORE` → 같은 초의 두 번째 샘플 버림.
594건 중 **101건**에서 발생(예 633: payload 1980점 → 저장 1675, 동일 초 Δt=0 샘플 305개; 랩 경계 이벤트로 추정).
값은 정수 초(소수 간격 없음)라 반올림 문제가 아니라 payload 자체 중복. 첫 샘플 유지는 수용 가능 — 다만 개수가 기록되지 않음.

## 2. 선택지 비교와 확정안

| 안 | 내용 | 장점 | 단점 |
|----|------|------|------|
| A | 스키마 무변경, 휴리스틱 3곳 삭제 + 추출기 폴백 제거 | 최소 변경 | 미래 비정상 payload 방어 수단 소실, 출처 불명 그대로 |
| **B (확정 제안)** | **신규 테이블 `activity_stream_meta`(활동×소스 1행)에 시간 기준·통계 기록, 소비자는 meta만 신뢰** | 추가형·롤백 쉬움, 휴리스틱을 "meta 없을 때만" 폴백으로 격하, 진단 가능 | 테이블 1개 추가, 쓰기 경로 1곳 수정 |
| C | `activity_streams`에 `time_basis` 행 컬럼 추가 | 조인 없음 | 100만 행에 같은 값 반복, 활동 단위 속성을 행에 둠 |
| D | `elapsed_sec`를 REAL/ms로 바꾸고 UNIQUE 재정의 | 서브초 보존 | 테이블 재생성(비추가형), 실측상 서브초 없음 → 이득 없음 |
| E | `ts_ms`(절대 시각) 컬럼 추가 | 날씨·랩 시각 정렬 | 이번 문제와 무관, Strava는 파생값 — LATER 후보 |

확정안 B의 원칙:
1. 시간축 결정은 **추출 시점 1회**, 결과를 meta에 저장. 소비자(계산기·API·프론트)는 추측하지 않는다.
2. 인덱스는 절대 `elapsed_sec`에 저장하지 않는다. 시간키가 없으면 summary 시간으로 비례 환산한 값을 쓰고 `time_basis='scaled'`.
3. 휴리스틱은 meta가 없는 행(구 서버·미백필)에만 적용되는 폴백으로 남긴다(제거는 U18e 이후 별도 판단).

## 3. 스키마 / 마이그레이션

### 3-1. DDL (스키마 v26 — v25는 `db_schema_v25.py`(U15 activity_feedback)가 선점, 미연결 상태이므로 순서 확인 필요)
```sql
CREATE TABLE IF NOT EXISTS activity_stream_meta (
    activity_id     INTEGER NOT NULL,
    source          TEXT    NOT NULL,
    time_basis      TEXT    NOT NULL CHECK (time_basis IN ('measured','derived','scaled','unknown')),
    time_key        TEXT,            -- 'sumElapsedDuration' | 'directTimestamp' | 'time'(strava) | NULL
    sample_count    INTEGER NOT NULL, -- payload 샘플 수
    stored_count    INTEGER NOT NULL, -- 저장 행 수(차이 = 동일 초 중복 탈락)
    span_sec        REAL,            -- 마지막 - 첫 시간
    median_dt_sec   REAL,            -- 샘플 간격 중앙값(1Hz 가정 금지용)
    extracted_at    TEXT DEFAULT (datetime('now')),
    PRIMARY KEY (activity_id, source)
);
```
`time_basis` 의미: `measured`=경과시간 키 직접, `derived`=`directTimestamp` 차이로 계산, `scaled`=키 없음→summary 시간 비례,
`unknown`=백필 시 payload 없음(현 행 유지·폴백 휴리스틱 적용).

### 3-2. 파일
- `src/db_schema_v26.py` 신규(`ensure_v26`, `CREATE TABLE IF NOT EXISTS`만 — v20~v25 패턴), `db_setup.py` `SCHEMA_VERSION=26` + 호출 1줄.
- `activity_streams` DDL·UNIQUE·데이터 **무변경**.

### 3-3. 백업 → 적용 → 롤백 절차
1. 백업: 컨테이너 내부에서 `sqlite3 <db> ".backup /data/backup/running-pre-u18-$(date +%F).db"` 후 `PRAGMA integrity_check` = ok 확인. 호스트로 `docker cp` 사본 1부.
2. 사본 리허설: 백업 사본에 `ensure_v26` → 백필(U18e) → 1-1·1-2 측정 스크립트 재실행해 기대값 비교.
3. 운영 적용: 앱 정지 없이 가능(신규 테이블, 기존 쓰기 경로와 잠금 충돌은 백필 트랜잭션을 활동 50건 단위로 끊어 최소화).
4. 롤백: `DROP TABLE activity_stream_meta;` + `schema_version`을 25로 되돌림 + 코드 revert. meta가 없으면 소비자는 폴백
   휴리스틱으로 동작하므로 **코드만 되돌려도 데이터 손상 없음**. 스트림 행을 바꾼 경우(U18e 재추출)는 1의 백업으로 복원.

## 4. API · 프론트 영향

- 서비스: `activity_service.get_activity_streams()`가 meta 1행을 함께 읽음(서비스 계층 SQL — ADR-009 대상 아님).
- `GET /api/v1/library/activities/:id/streams` 응답 `{streams:[...]}` → `{streams:[...], time_basis, median_dt_sec}` **필드 추가만**(하위호환).
  활동 상세 번들(`streams` 포함 응답)도 같은 두 필드를 `streams_meta`로 추가.
- 프론트 `streamAxis.ts` `streamSeconds(elapsed, totalSec, basis?)`: `basis`가 `measured|derived|scaled`면 원본 그대로,
  `unknown`/미전달일 때만 기존 0.9 규칙. 스트림 탭 `+page.ts`가 응답의 `time_basis` 전달. 요약 탭 Sparkline은 인덱스 기반 그대로(영향 없음).
- MCP/AI 도구(`tool_exec_activity.py`)는 스트림을 시간 해석 없이 요약 → 영향 없음(U18c에서 grep 확인).

## 5. 구현 단위와 테스트

공통: 파일 300줄 규칙 — `base.py`(551줄)·`garmin_extractor.py`(686줄)·`db_helpers.py`(754줄)는 이미 초과이므로 **새 로직은 신규
모듈에 두고 기존 파일은 호출 1~3줄만** 추가한다.

### U18a — 시간축 결정 모듈 + 추출기 연결
- 신규 `src/sync/extractors/stream_time.py`: `resolve_time_axis(metrics_rows, idx_map) -> (times: list[float|None], basis, time_key)`.
  우선순위 `sumElapsedDuration` → `directElapsedDuration`(measured) → `directTimestamp - 첫값`/1000(derived) → 없음(None 목록, scaled 대기).
  샘플 일부만 None이면 앞뒤 측정값 선형 보간(보간 비율 >5%면 basis를 한 단계 낮춤).
- `garmin_extractor.extract_activity_streams`: `else i` 삭제, 위 함수 사용. 반환 형식 유지 + 마지막에 `self.last_stream_meta` 대신
  **순수 함수 `stream_meta(rows, basis, key, sample_count)`를 `stream_time.py`에 두고 저장 경로에서 호출**(추출기 인터페이스 불변).
- Strava: `time` 스트림 → `measured`, key `time`.
- 테스트 `tests/test_stream_time.py`(~8): sumElapsed 우선 / directTimestamp만 → derived / 키 없음 → basis scaled·times None /
  부분 None 보간 / 단조 아님 → 정렬 안 하고 basis 낮춤 / Strava time / 중복 초 개수 / 빈 입력 [].

### U18b — 스키마 v26 + 저장 경로
- `db_schema_v26.py`, `db_setup.py` 연결. 신규 `src/sync/stream_meta_store.py`: `save_stream_meta(conn, aid, source, meta)` UPSERT,
  `scaled`면 summary(`elapsed_time_sec`→`duration_sec`→`moving_time_sec`)로 times 채운 뒤 저장, summary도 없으면 스트림 저장 생략+log.
- `_helpers.save_streams`·`reextract`·`reprocess._reprocess_activity_streams`·garmin/strava 동기화 저장부가 meta도 기록.
- 테스트 `tests/test_stream_meta_store.py`(~6): 테이블 생성 멱등 / UPSERT / stored_count=중복 탈락 반영 / scaled 환산 / summary 없음 → 미저장 / 롤백(DROP 후 소비자 폴백) .

### U18c — CalcContext API + 계산기 소비
- `CalcContext.get_stream_meta(activity_id=None) -> dict | None` — 구현은 신규 `src/metrics/stream_meta_access.py` 함수, base.py엔 위임 1메서드
  (ADR-009: 계산기는 이 API만 사용, SQL은 base 계층).
- `stream_utils.sample_times(streams, total_sec, meta=None)`·`segments.repair_time_axis(elapsed, dur, basis=None)`: basis가
  `measured|derived|scaled`면 원본 반환, 아니면 기존 규칙. decoupling·gap·relative_effort·classifier가 `ctx.get_stream_meta()` 전달.
- 테스트(~6, 기존 파일에 추가): 692 모양(3215 측정, summary 4508) → 재환산 안 함 / meta 없음 → 기존 동작 / RE 존 체류시간 합 = 실제 이동 시간 / 수영 basis measured.

### U18d — API·프론트
- 서비스·라우트 필드 추가, `streamAxis.ts` basis 인자, `streams/+page.ts` 전달, 타입 `ActivityStreamsResponse`.
- 테스트: `tests/test_routes_library*.py`에 필드 존재·meta 없음 시 `time_basis:'unknown'`(~2), `frontend/tests/streamAxis.test.mjs`(~3).
  브라우저 확인: 활동 692·15302 스트림 탭 x축 끝 = 3215s·8767s.

### U18e — 백필·재계산 (실데이터 쓰기, 사용자 승인 필수)
- 신규 `scripts/backfill_stream_meta.py --db <path> [--dry-run]`: Garmin은 `reextract_laps_streams`(meta 포함)로, Strava는 행만 보고
  meta 기록(measured), payload 없는 활동은 `unknown`.
- 이후 영향 활동만 재계산: `metric_store`에서 해당 activity의 `provider LIKE 'runpulse%'` 중 relative_effort·decoupling·gap·
  분류 결과 삭제 → 엔진 재실행(활동 scope + 의존 daily). 대상 목록은 dry-run이 출력(현 사본 기준 6건).
- 검증: dry-run 수치 = 1-1 실측(594/98, 중복 101건), 재계산 전후 692 RE 비율 ≈ 1/1.40.

## 6. 위험

| 위험 | 대응 |
|------|------|
| 운영 DB가 사본(10:39)과 다름 — 새로 동기화된 활동 | U18e dry-run을 운영 직전 백업 사본으로 다시 실행 |
| 스키마 번호 충돌(v25 미연결 파일 존재, U15/U16 진행 중) | 구현 착수 시 최신 `SCHEMA_VERSION` 확인 후 다음 번호 사용 |
| 재추출이 스트림 행 id를 바꿈 — 행 id 참조 테이블 존재 여부 | `grep -rn "activity_streams.id\|stream_id"`로 확인(현 조사 범위에서 없음), 있으면 U18e 중단 |
| 휴리스틱 폴백 잔존으로 혼선 | `unknown` 비율 0 확인 후 폴백 제거를 별도 백로그로 |
| 비균등 간격(1~4s)을 1Hz로 가정하는 숨은 소비자 | U18c에서 `len(streams)`를 시간으로 쓰는 코드 grep, `median_dt_sec` 노출로 차단 |
| 같은 초 중복 탈락으로 랩 경계 값 소실 | 수용(첫 샘플 유지), `stored_count`로 가시화만 — 평균 병합은 LATER |
