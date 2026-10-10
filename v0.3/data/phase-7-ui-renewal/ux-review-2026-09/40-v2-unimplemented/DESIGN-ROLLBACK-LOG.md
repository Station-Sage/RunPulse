# G5 v1 복귀 로그 — 설계 (ADR-046 제안)

상태: 설계 초안(미확정). 근거: `design.md` §9.1 G5 행 "2주 운용: v1 복귀 클릭 수·사유(1문항) 로그 수집, 복귀율 <10%".
코드 변경 없음. 확정은 사용자 승인 후.

## 1. 배경과 문제

- G5 통과 기준은 "복귀율 <10%"인데, 현재 복귀(`MenuDrawer.svelte` `backToV1` → `PATCH /me/preferences {ui_default:'v1'}` → `/dashboard`)는 어떤 기록도 남기지 않는다. 설정값만 바뀌므로 복귀 횟수도 사유도 알 수 없다.
- 분모(활성 사용자)도 기록이 없다. `user_settings.ui_default`는 "선호"이지 "v2를 실제 썼는가"가 아니다.
- 사용자별 DB 구조(`data/users/<uid>/running.db`, `get_db_path`)라 집계는 DB 여러 개를 가로질러야 한다.
- 목적은 게이트 판정 하나다. 분석 시스템으로 키우지 않는다(최소안).

## 2. 제안 설계

### 2.1 저장소 — 새 테이블 `ui_events` (스키마 v36, `src/db_schema_v36.py`, `ensure_v36`)

기존 `user_settings`는 화이트리스트 key-value(마지막 값만 보존)라 이벤트 이력에 부적합하다.
`sync_jobs` 원장은 동기화 전용 의미라 재사용하지 않는다. 범용 이름으로 하되 용도는 UI 전환 이벤트로 한정한다.
관례는 `user_settings`(v25)와 같다: 사용자 DB 안, `ensure_vNN` 멱등 DDL, `db_setup.py` 체인에 1줄 추가.

```sql
CREATE TABLE IF NOT EXISTS ui_events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    kind        TEXT NOT NULL CHECK (kind IN ('v2_visit','v1_rollback')),
    reason      TEXT CHECK (reason IS NULL OR reason IN
                  ('missing_feature','hard_to_use','slow_or_error','just_looking')),
    reason_note TEXT CHECK (reason_note IS NULL OR length(reason_note) <= 200),
    day         TEXT NOT NULL,                       -- 로컬 날짜 YYYY-MM-DD (dedupe·창 계산용)
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS uq_ui_events_visit_day
    ON ui_events(day) WHERE kind='v2_visit';          -- 하루 1회
CREATE INDEX IF NOT EXISTS idx_ui_events_kind_day ON ui_events(kind, day);
```

- 분모용 `v2_visit`: v2 셸 최초 마운트 시 하루 1행(`INSERT OR IGNORE`). 활성 사용자 = 창 내 `v2_visit`가 1일 이상인 사용자.
- 분자용 `v1_rollback`: 복귀 클릭 1회 = 1행. 사용자 단위 집계는 `DISTINCT`로 중복 제거(여러 번 눌러도 1명).
- 개인정보: 사용자 ID·IP·UA를 저장하지 않는다(사용자별 DB 자체가 식별자). 자유입력은 선택·200자·'other' 선택 시에만.
- `SCHEMA_VERSION` 35 → 36, `phase_summary.md`/`architecture.md` 테이블 목록 갱신 필요(체크리스트).

### 2.2 이벤트 정의

| 이벤트 | 발생 시점 | 기록 필드 |
|---|---|---|
| `v2_visit` | v2 레이아웃 첫 마운트(세션당 1회 호출, 서버가 일 단위 dedupe) | kind, day |
| `v1_rollback` | 드로어 '이전 화면으로(v1)' 클릭 직후 시트에서 확정(답변 또는 건너뛰기) | kind, reason?, reason_note?, day |

사유 1문항 — "이전 화면으로 돌아가는 이유가 무엇인가요?" (단일 선택, 선택 사항):

1. `missing_feature` — 필요한 기능이 없어요
2. `hard_to_use` — 사용하기 어려워요
3. `slow_or_error` — 느리거나 오류가 났어요
4. `just_looking` — 그냥 둘러봤어요

- 자유입력: 선택지 4개 아래 "직접 쓰기(선택)" 한 줄 입력을 접어 둔다(펼침 시에만 `reason_note`, 200자). 필수 아님. `missing_feature` 선택 시 어떤 기능인지가 G3/G6 판단에 가장 가치가 커서 허용한다. 서버는 note만 있고 reason이 NULL이면 거부하지 않고 저장한다.
- 건너뛰기 허용: `reason=NULL`로 기록. 복귀 클릭 수는 사유와 무관하게 센다. 건너뛰기 비율도 집계에 포함한다.
- 이벤트 손실 허용: 기록 실패(오프라인 등)는 이동을 막지 않는다. 손실은 복귀율을 과소평가하므로 §5에서 점검 항목으로 둔다.

### 2.3 API (`src/api/routes_me.py` 확장 또는 `routes_ui_events.py` 신설; 300줄 규칙상 신설 권장)

서비스: `src/services/ui_events_service.py` — `record_visit(conn)`, `record_rollback(conn, reason, note)`, `summarize(conn, days=14, today=None)`, `summarize_all_users(root, days=14)`.

| 메서드·경로 | 본문 | 응답 |
|---|---|---|
| `POST /api/v1/me/ui-events` | `{kind:'v2_visit'}` 또는 `{kind:'v1_rollback', reason?, reason_note?}` | `{recorded:bool}` (visit 중복은 `false`, 200) |
| `GET /api/v1/me/ui-events/summary?days=14` | — | 현재 사용자 기준 집계 |

- 검증: kind·reason 화이트리스트(`ALLOWED` 관례, 위반 시 `api_error('VALIDATION', …, 400)`), `reason_note`는 trim·200자 절단.
- 쓰기는 POST만(design.md §7.3 계약 준수). GET 부작용 없음.
- 집계 응답(현재 사용자): `{window_days, from, to, v2_visit_days, rollback_count, rollback_by_reason:{missing_feature,…,skipped}, rolled_back:bool}`.
- 전체 복귀율은 사용자별 DB 구조상 요청 단위 API로 계산하지 않는다(타 사용자 DB 접근은 권한 경계 문제). 전체 집계는 §2.5 CLI가 맡는다.
- 복귀율 정의: `복귀 사용자 수 / 활성 사용자 수`, 14일 창(`day >= today-13`).
  - 활성 사용자 = 창 내 `v2_visit` 1행 이상. 복귀 사용자 = 창 내 `v1_rollback` 1행 이상(활성 중 복귀한 사용자만 분자에 넣기 위해, 복귀했지만 활성이 아닌 경우는 `v2_visit`가 복귀 직전 세션에서 이미 기록되므로 자연히 포함됨).
  - 활성 0명이면 `rate=null`(데이터 수집 중), 판정은 "미판정".
  - 창은 G5 개시일(`ui_default_global=v2` 전환일) 이후로 클립할 수 있도록 `--since` 옵션을 둔다.
  - 판정: `rate < 0.10` 통과. 표본이 작을 때(활성 <10명)는 CLI가 "표본 부족 경고"를 함께 출력.

### 2.4 v2 드로어 UI 흐름 (구성만, 시각 규격은 product-architect/ui.md)

```
[이전 화면으로(v1)] 탭
 → 바텀시트(기존 시트 패턴, ActivityFeedbackSheet 참조) 열림: 선택지 4개 + [건너뛰고 이동] + 직접 쓰기(접힘)
 → 선택 시: 선택지 탭 = 즉시 확정 (별도 제출 버튼 없음)
 → 확정/건너뛰기 → POST ui-events(v1_rollback) 와 PATCH preferences(ui_default:'v1') 를 병행 전송
 → 둘 중 하나가 1.5초 내 끝나지 않아도 location.assign('/dashboard') 수행
```

- `MenuDrawer.svelte`의 `backToV1`을 "시트 열기"로 바꾸고, 이동 로직은 신규 `RollbackReasonSheet.svelte`(≤300줄)가 소유한다. 드로어는 열기만 한다.
- 이동을 막지 않는 규칙: 시트 닫기(스크림·Esc)도 "건너뛰고 이동"이 아니라 "취소(v2 잔류)"로 처리하지 않는다. 이미 복귀 의사를 밝혔으므로 닫기 = 건너뛰기 이동으로 통일한다. (대안은 §4)
- 요청 실패는 무시하고 이동(`Promise.allSettled` + 타임아웃 1.5초). 이때 `PATCH`가 실패하면 `ui_default`가 v2로 남아 `/` 진입이 v2로 되돌아올 수 있으므로, 이동 경로는 `/dashboard` 직접 이동 유지(현행과 동일).
- `v2_visit`: `routes/+layout.svelte`에서 `onMount` 1회 `fetch POST`(실패 무시). 비로그인·데모 모드는 호출하지 않음(`DemoBanner` 상태 확인).
- v1 헤더 '새 화면 사용해 보기'는 변경 없음. 재진입은 `v2_visit`로 자연 집계된다.
- G5 첫 진입 안내(`이전 화면으로 [↩]`)의 [↩]도 같은 시트를 연다(경로 1개로 통일, 미통일 시 복귀 누락).

### 2.5 집계 확인 — 최소안: CLI `scripts/ui_rollback_report.py`

`/data` 화면 노출은 G5 판정 이후로 미룬다(UI 변경 범위를 늘리지 않음).

```
python3 scripts/ui_rollback_report.py [--days 14] [--since YYYY-MM-DD] [--users-root data/users] [--json]
```

- `data/users/*/running.db`를 읽기 전용(`file:...?mode=ro`)으로 순회, `ui_events` 없는 DB(v36 이전)는 건너뜀.
- 출력: 활성 사용자 수, 복귀 사용자 수, 복귀율, 판정(통과/미달/표본 부족), 사유별 건수(건너뜀 포함), `reason_note` 최근 20건(사용자 식별 없이).
- 로직은 `ui_events_service.summarize_all_users`에 두고 스크립트는 인자 파싱·출력만 맡는다(테스트 용이).

## 3. 기존 시스템과의 호환성

- `user_settings`·`PATCH /me/preferences`·`resolve_ui_default`·`entry_path`는 변경 없음. 복귀 동작(설정값 v1)은 그대로이며 로그만 추가.
- 파이프라인 테이블 11 + App 테이블 5 구분에서 `ui_events`는 App 테이블로 분류(총 App 6). metric_store·CalcContext 영향 없음(ADR-009 무관).
- `ensure_v36` 체인 추가로 `SCHEMA_VERSION=36`. 기존 스키마 버전 테스트(버전 숫자 단언) 갱신 필요.
- 전역 롤백(`ui_default_global` 1줄)은 이벤트 테이블과 독립이므로 롤백 절차 영향 없음.
- `design.md` §9.1 G6("v1 복귀 0건이 2주 지속")도 같은 테이블로 판정 가능 → 재사용.
- 권한: 사용자 본인 DB만 기록. 다중 사용자 집계는 서버 운영자의 CLI(컨테이너 내부 실행)에서만.

## 4. 대안과 트레이드오프

| 대안 | 미채택 사유 |
|---|---|
| `user_settings`에 `rollback_count` 키 | 사유·시각 이력 없음, 분모 불가, 화이트리스트 의미 훼손 |
| 서버 로그(access log) 파싱 | 사유 수집 불가, 사용자 식별 어려움, 로그 보존 정책 의존 |
| 전역 단일 DB(`data/ui_events.db`) | 사용자별 DB 관례와 다름. 단점: 계정 삭제 시 이벤트 잔존. 장점: 집계 단순 — 사용자 수가 매우 많아지면 재검토 |
| 필수 사유(응답 전 이동 차단) | 요구사항(이동 막지 말 것) 위반, 응답 왜곡 |
| 시트 닫기 = v2 잔류 | 복귀 의도 클릭이 로그에서 사라져 복귀율 과소평가. 단 오탭 구제 이점이 있음 → 사용자 결정 사항 |
| 외부 분석 도구 | 자체 호스팅 개인정보 원칙에 반함, 과설계 |
| `v2_visit`를 매 페이지 기록 | 쓰기 폭증. 일 1행이면 분모 목적 충분 |

미결 결정(사용자 확인 필요): (a) 시트 닫기의 의미 (b) 자유입력 허용 여부 (c) 활성 정의의 최소 방문 일수(현안 1일).

## 5. 검증 항목

- 복귀 클릭 후 `ui_events`에 `v1_rollback` 1행, `ui_default='v1'`, `/dashboard` 도달이 모두 성립.
- 사유 미응답·네트워크 차단 상태에서도 v1로 이동한다(이동 지연 ≤1.5초).
- `v2_visit` 하루 1행 보장(중복 POST, 자정 경계는 로컬 날짜 기준).
- 분모 정합: 복귀 사용자가 활성 집합에 항상 포함되는가(복귀 전 `v2_visit` 선행 보장). 포함되지 않는 사례가 있으면 분모 정의 수정.
- 이벤트 손실 추정: `v2_visit` 없는 `v1_rollback` 비율을 CLI가 경고로 출력.
- 14일 창 경계(13일 전 포함, 14일 전 제외).
- 구 DB(v35)에서 `ensure_v36` 멱등, 신규 DB 스키마 동일.
- 문서: `check_docs.py`, `gen_files_index.py`, `decisions.md` ADR-046, `phase_summary.md`/`architecture.md` 테이블 수.

## 6. 테스트 목록

백엔드 (`tests/`)

1. `test_db_schema_v36.py` — ensure_v36 멱등, CHECK 위반(잘못된 kind/reason, note 201자), visit 일 1행 유니크, SCHEMA_VERSION=36
2. `test_ui_events_service.py` — record_rollback(사유 있음/없음/note), record_visit dedupe, summarize 창 경계, 활성 0명 `rate=None`, 한 사용자 복수 복귀=1명, 사유별 집계(건너뜀 포함)
3. `test_ui_events_service.py::test_summarize_all_users` — 임시 users 디렉터리 3개 DB(v35 DB 1개 포함) 집계, 읽기 전용 열기 확인
4. `test_routes_ui_events.py` — POST 200/400(잘못된 kind·reason), visit 중복 `recorded:false`, GET summary 형태, DB 없음 503
5. `test_ui_rollback_report.py` — CLI 출력(통과/미달/표본 부족), `--json`, `--since`

프런트엔드 (frontend 기존 테스트 러너 사용)

6. `RollbackReasonSheet` — 선택지 4개 렌더, 선택 시 POST 후 이동, 건너뛰기 시 reason 없이 POST, POST 실패/지연에도 `location.assign('/dashboard')` 호출, 직접 쓰기는 접힘 기본·200자 제한
7. `MenuDrawer` — `back-to-v1` 클릭이 이동 대신 시트를 연다(기존 `data-testid` 유지)
8. 레이아웃 `v2_visit` — 마운트 1회 호출, 데모 모드 미호출, 실패 무시

수동/브라우저 스모크: 모바일 폭에서 드로어 → 시트 → v1 도달, 사유 없이 이동, 데스크톱 팝오버 동일 경로.

## 7. 구현 순서·DoD (제안)

1. v36 DDL + 서비스 + API + 테스트 1~4
2. CLI + 테스트 5
3. v2 시트·드로어·레이아웃 + 테스트 6~8
4. 문서(ADR-046, architecture, phase_summary, files_index) + `check_docs.py`

DoD: 위 테스트 전부 통과 + 전체 `pytest tests/` 통과 + 브라우저 스모크 + G5 개시 전 CLI가 빈 데이터에서 "미판정"을 출력.

## 8. ADR-046 초안 (decisions.md 기록용)

결정: v1 복귀는 사용자 DB `ui_events`(kind=`v1_rollback`, 사유 1문항 선택·건너뛰기 허용)로 기록하고, 분모는 `v2_visit`(일 1행)로 둔다. 복귀율 = 14일 창 복귀 사용자 / 활성 사용자, 전체 집계는 운영자 CLI. 사유 응답은 v1 이동을 절대 지연·차단하지 않는다. 대안(user_settings 카운터, 서버 로그, 전역 DB)은 §4 사유로 기각.
