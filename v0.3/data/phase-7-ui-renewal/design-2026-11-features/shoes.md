# 설계: 신발 관리 v2 (`[V2-SHOES]`)

- 작성일: 2026-11-06 · 상태: **구현 완료(T1~T11)** — 미결 Q1~Q9 는 §9 추천안으로 확정(사용자 위임). 구현 중 확정 사항은 §1.1
- 범위: SvelteKit v2(`frontend/`) + Flask API(`src/api/`) + 서비스(`src/services/`) + sync 보강 + 스키마 v42
- 관련 패턴: `design-2026-10/patterns/` 의 `error-retry-common.md`(LoadResult·ErrorState), `server-input-origin-validation.md`(Origin 관문·`validation.py`), `non-running-activities.md`(`sport_family` SSOT), `overlay-common-behavior.md`(시트), `accessibility-common.md`

## 1. 현황 조사 (v1 backup·현행 코드)

| 대상 | 사실 | 판정 |
|------|------|------|
| `v1_backup/src_web/views_shoes.py` (86줄) | `/shoes` 읽기 전용 HTML 표. `shoes` 테이블(brand·model·name·default_sport_types) 조회. 마일리지·배정·알림 없음 | **버림** (화면·쿼리). 열 목록(브랜드·모델·이름)만 참고 |
| `shoes` 테이블 | v0.3 DDL(`src/db_setup.py`)에 **없음**. v1 잔재 | **버림**. 이름 충돌 회피 위해 새 테이블은 `user_shoes` |
| `src/import_export/strava_shoes.py` | Strava export `shoes.csv` → `INSERT INTO shoes` — 테이블이 없어 `sqlite3.Error` 를 잡고 전부 skipped 로 **조용히 실패** 중 | **수정 재사용** (T3: `gear` 로 적재) |
| `strava_row.py:144` `"gear": Activity Gear` | CSV 활동의 신발 이름을 파싱하지만 저장 경로 없음 | **재사용** (T3) |
| `gear` 테이블 (Layer 4) | `source, source_gear_id, name, brand, model, gear_type, total_distance_m, status`, `UNIQUE(source, source_gear_id)` | **재사용** — 소스 미러로 유지 |
| `activity_summaries.gear_id` (TEXT, 인덱스 있음) | 소스별 gear id 원문 (Strava `g123`, Garmin `gearPk`). Strava·Intervals extractor 가 채움 | **재사용** — 자동 배정 1순위 입력 |
| Strava `sync_gear` / `sync_athlete_and_gear` | 미수집 gear 상세 저장. `gear_type='shoes'` 하드코딩 → 자전거(`b…`)도 shoes 로 저장됨 | **수정 재사용** (T3) |
| Garmin `sync_activity_gear` (`garmin_api_extensions.py`) | 구현돼 있으나 **호출처 없음**(dead code) | **배선 재사용** (T3) |
| Intervals `gear_id` | extractor 가 `raw.get("gear_id")` 를 읽음. 실제 payload 키(`gear` 객체 여부) **미확인** | T1 에서 payload 확인 후 결정 |
| `export_groups.py` | 내보내기 그룹에 `gear` 포함 | 새 테이블 2개 추가 (T2) |

### 1.1 T1 조사 결과(운영 DB 읽기 전용, 2026-11-06) 및 구현 확정 사항

| 항목 | 확인된 사실 | 반영 |
|------|------------|------|
| `activity_summaries.gear_id` 채움률 | strava 152/202(75%, 러닝 155건 중 152), garmin 0/615, intervals 0/664 | Garmin 은 신규 러닝에 `sync_activity_gear` 배선, Intervals 는 extractor 수정 |
| Intervals payload | 키는 `gear_id` 가 아니라 **`gear: {id, name, distance, primary}` 객체**. 활동 payload 407/664 에 존재, `name` 은 전부 null. id 는 Strava id(`g18611020` 등)와 Intervals 자체 숫자 id(`34377` 등)가 섞임 | extractor `_gear_id()` 가 `gear.id` 우선. `g…` 는 Strava gear 로 조회(`gear_lookup_sources`), Strava gear 수집 대상에도 포함. 숫자 id 는 이름 출처가 없어 미연결(남은 과제) |
| Garmin `get_activity_gear` | 운영 DB 에 응답 사례 없음(배선 안 돼 있었음). garminconnect 코드상 `/gear-service/gear/filterGear?activityId=` → gear dict 목록(`gearPk`·`gearTypeName`·`customMakeModel`·`gearMakeName`…) | 목록 처리, `gearTypeName` 으로 shoes/bike 구분, 신발 우선 링크. 실패 시 1회 재시도 후 계속 |
| 러닝 raw type | Garmin typeKey: running 443·treadmill_running 36·indoor_running 16·track_running 3·trail_running 3. Intervals type: Run 445·VirtualRun 58·TrailRun 2. Strava sport_type: Run 96. `activity_type` 은 이미 `running` 으로 정규화돼 kind 를 알 수 없음 | kind 는 `source_payloads` 원본(typeKey·sport_type·activity_type_raw·type)에서 판정: trail_running·TrailRun→trail, treadmill_running·indoor_running·VirtualRun→treadmill, 나머지(track 포함)→road |
| `gear` 테이블 | strava 신발 7행(이름 한글 모델명). Intervals·Strava 활동이 참조하는 `g18611020` 등 일부 id 는 gear 에 없음 | 다음 Strava 동기화가 수집 |
| v1 `shoes` 테이블 | 운영 DB 에 없음 | Q9 정리 불필요 |

구현 중 확정(설계 대비 차이):
- `activity_shoe.activity_id` 에 FK 를 두지 않음 — activity_feedback 관례. 재처리(`DELETE FROM activity_summaries`)가 CASCADE 로 사용자 배정을 지우는 것을 막는다(재처리 후 id 변경 시 배정이 어긋나는 문제는 activity_feedback 과 같은 남은 과제).
- `activity_shoe.origin ('manual'|'rule')` 추가 — 기본 신발 교체·은퇴 시 기존 기본 신발의 규칙 배정을 `rule` 이력으로 고정해 과거 마일리지가 사라지지 않게 한다. 해석 순서: manual > source > rule 이력 > 기본 규칙 > none. 은퇴하면 기본 지정이 해제된다(활성 신발만 기본).
- `GET /shoes/unassigned`(일괄 배정 목록)·`GET /shoes/alert`(Today Q3 한 줄) 추가. 응답에 `method_source`/`source`(채택 소스) 추가.
- 서비스는 `shoe_query.py`(조회)·`shoe_service.py`(쓰기)로 분리. FK 동작은 연결 PRAGMA 에 의존하지 않고 서비스가 명시적으로 지운다.

## 2. 사용자 스토리

- US1 (첫 3초) 신발 화면을 열면 "어느 신발이 곧 은퇴인지"가 먼저 보인다. 숫자(612 km)보다 의미("교체를 준비할 때예요")가 앞선다.
- US2 Strava/Garmin 에 등록한 신발이 자동으로 들어오고, 같은 신발이 두 소스에 있으면 한 켤레로 합칠 수 있다.
- US3 소스에 gear 정보가 없는 러닝도 "기본 신발" 규칙으로 자동 배정된다(로드/트레일/트레드밀별).
- US4 활동 상세에서 신발을 확인·변경한다. 내가 직접 바꾼 배정은 다음 동기화가 덮어쓰지 않는다.
- US5 이미 300 km 신은 신발을 등록할 때 시작 거리를 넣을 수 있다.
- US6 마일리지 근거("왜 612 km?")를 누르면 시작 거리 + 배정된 활동 수·합계, 그리고 소스가 말하는 누적값과의 차이가 보인다(투명성).
- US7 은퇴시킨 신발은 목록 아래로 내려가고 기록은 남는다. 은퇴 이후 날짜 활동에는 자동 배정되지 않는다.
- US8 미배정 러닝이 쌓이면 한 번에 신발을 지정한다(일괄 배정).

## 3. 데이터 모델 — 스키마 v42 (`src/db_schema_v42.py`, `SCHEMA_VERSION = 42`)

원칙: `gear` = 소스가 말하는 장비(미러, 동기화가 덮어씀), `user_shoes` = 사용자가 소유한 신발(동기화가 건드리지 않음). 마일리지는 **저장하지 않고 읽기 시점 계산**(재계산·백필 불필요, 그룹 재매칭에 안전).

```sql
CREATE TABLE IF NOT EXISTS user_shoes (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    name                TEXT NOT NULL,                 -- 표시 이름(별명)
    brand               TEXT,
    model               TEXT,
    category            TEXT NOT NULL DEFAULT 'daily'
                        CHECK (category IN ('daily','tempo','race','trail','other')),
    start_date          TEXT,                          -- 개시일 YYYY-MM-DD (NULL=제한 없음)
    initial_distance_m  REAL NOT NULL DEFAULT 0 CHECK (initial_distance_m >= 0),
    retire_km           INTEGER CHECK (retire_km BETWEEN 100 AND 2000),  -- NULL=카테고리 기본값
    default_for         TEXT CHECK (default_for IN ('road','trail','treadmill')),
    default_since       TEXT,                          -- 기본 신발 지정일(이 날짜 이후 활동만 규칙 배정)
    retired_at          TEXT,                          -- 은퇴일 YYYY-MM-DD
    origin              TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual','gear')),
    notes               TEXT,
    created_at          TEXT DEFAULT (datetime('now')),
    updated_at          TEXT DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_user_shoes_default
    ON user_shoes(default_for) WHERE default_for IS NOT NULL AND retired_at IS NULL;

ALTER TABLE gear ADD COLUMN shoe_id INTEGER REFERENCES user_shoes(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_gear_shoe ON gear(shoe_id);

-- 수동 배정만 저장. shoe_id NULL = "신발 없음"을 사용자가 명시(자동 배정 차단)
CREATE TABLE IF NOT EXISTS activity_shoe (
    activity_id  INTEGER PRIMARY KEY,               -- FK 없음(§1.1)
    shoe_id      INTEGER REFERENCES user_shoes(id) ON DELETE CASCADE,
    origin       TEXT NOT NULL DEFAULT 'manual' CHECK (origin IN ('manual','rule')),  -- §1.1
    created_at   TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_activity_shoe_shoe ON activity_shoe(shoe_id);
```

- 마이그레이션: v41 패턴 그대로 — 멱등(`PRAGMA table_info(gear)` 에 `shoe_id` 있으면 skip), 실행 전 `integrity_check`, 백필 없음. `db_setup.py` 의 신규 DB DDL 에도 동일 반영.
- 기존 v1 `shoes` 테이블이 남은 DB 가 있어도 건드리지 않는다(삭제는 별도 정리 항목).
- `activity_shoe.activity_id` 는 배정 시점의 canonical 행 id. 해석은 **그룹 단위**: 같은 `matched_group_id` 의 어느 행에든 수동 배정이 있으면 그것을 쓴다(나중에 Garmin 행이 들어와 대표 행이 바뀌어도 유지).

## 4. 자동 배정 규칙 (`src/services/shoe_assignment.py`, 읽기 시점 해석)

대상: `sport_family(activity_type) == 'running'` 인 canonical 활동만(`non-running-activities.md` SSOT). 비러닝은 배정·마일리지에서 제외.

우선순위 (먼저 걸리는 것 채택, 결과에 `method` 기록):
1. **manual** — 그룹 내 `activity_shoe` 행. `shoe_id NULL` 이면 "신발 없음"으로 확정.
2. **source** — 그룹 내 행들의 `gear_id` → `gear(source, source_gear_id).shoe_id`. 행 우선순위는 canonical 과 같음(garmin > intervals > strava). 서로 다른 신발을 가리키면 우선순위 승자 채택 + `conflict=true`(Level 2 에 "Garmin 은 A, Strava 는 B" 표시).
3. **rule** — 활동 종류(kind) 의 기본 신발. kind 판정: trail 계열 raw type → `trail`, treadmill/virtualrun → `treadmill`, 그 외 → `road`. 조건: 활동 날짜 ≥ `default_since`, ≥ `start_date`, 은퇴 전.
4. **none** — 미배정. 목록에 "미배정 N건" 배지 → 일괄 배정.

공통 제약: 은퇴일 이후·개시일 이전 활동에는 source/rule 배정도 하지 않는다(manual 은 허용 — 사용자 의사 우선).
기본 신발을 바꿔도 과거 활동은 재배정되지 않는다(`default_since`). 과거분은 일괄 배정으로만 바꾼다.

## 5. 마일리지·교체 알림

- `mileage_km = initial_distance_m/1000 + Σ canonical distance_m(배정된 러닝)/1000`. 소스 `gear.total_distance_m` 은 합산에 쓰지 않고 Level 2 소스 비교로만 노출(소스 누적에는 RunPulse 밖 이력·다른 종목이 섞임).
- 기본 교체 임계값(추천값, `retire_km` 미지정 시):

| category | 라벨 | 기본 `retire_km` |
|----------|------|------------------|
| daily | 데일리 | 700 |
| tempo | 템포·경량 | 600 |
| race | 레이스(카본) | 400 |
| trail | 트레일 | 700 |
| other | 기타 | 700 |

- 상태 3단계(색 + 문구, 숫자는 괄호/보조):
  - `ok` (< 80%) 초록 — "아직 충분해요"
  - `soon` (80~99%) 노랑 — "교체를 준비할 때예요 (남은 약 N km)"
  - `replace` (≥ 100%) 빨강 — "교체를 권해요 (임계값 +N km)"
- 맥락 보조 문구: 활성 목표 대회가 21일 이내이고 `race` 신발이 `soon` 이상이면 "대회 전 새 레이스화 길들이기(최소 2~3회 주행) 시간을 확보하세요" 추가.
- 알림 노출 위치: Library 신발 블록·목록·활동 상세 칩. Today 노출은 §9 Q3.
- 은퇴 신발은 상태 계산·알림 제외.

## 6. API 명세 (`src/api/routes_shoes.py`, `api_bp` → `/api/v1`)

모든 응답은 `api_ok`/`api_error` 봉투. 쓰기는 Origin 관문 적용(테스트는 `headers={"Origin": "http://localhost"}`), 입력은 `validation.py` 필드(`str_field`·`enum_field`·`date_field`·`int_field`·`float_field`·`int_list_field`)로 검증, 위반 400 `INVALID_PARAM`.

| 메서드·경로 | 설명 | 응답 핵심 |
|------------|------|-----------|
| `GET /shoes?include_retired=0` | 목록 + 계산값 | `shoes[]: {id,name,brand,model,category,mileage_km,retire_km,status,remaining_km,default_for,retired_at,activity_count,last_used}`, `unassigned_count`, `suggestions[]`(미연결 gear) |
| `GET /shoes/<id>` | 상세 | 위 + `breakdown{initial_km, assigned_km, by_method{manual,source,rule}}`, `sources[]{source,name,total_km}`, `monthly_km[]` |
| `GET /shoes/<id>/activities?cursor=` | 배정 활동 목록 | `ActivityRow` 호환 행 + `method`, `conflict` |
| `POST /shoes` | 생성 | body: name(필수,≤60), brand·model(≤60), category, start_date, initial_distance_km(0~3000), retire_km, default_for, notes(≤500) → 201 |
| `PATCH /shoes/<id>` | 수정(부분) | 위 필드 + `retired_at`(은퇴/복귀). `default_for` 변경 시 기존 기본 신발 해제 + `default_since=오늘` (트랜잭션) |
| `DELETE /shoes/<id>` | 삭제 | 수동 배정 CASCADE, `gear.shoe_id` NULL. 확인 대화상자 필수 |
| `POST /shoes/<id>/merge` | body `{source_shoe_id}` — 다른 신발을 흡수 | gear 링크·수동 배정 이관 후 원본 삭제 |
| `POST /shoes/<id>/gear` / `DELETE /shoes/<id>/gear/<gear_id>` | 소스 gear 연결/해제 | 409 `GEAR_LINKED` (다른 신발에 연결됨) |
| `POST /shoes/import-gear` | 미연결 gear(`gear_type='shoes'`) → 신발 생성. 같은 정규화 이름(소문자·공백 제거)은 한 켤레로 묶음 | `{created, linked}` |
| `PUT /library/activities/<id>/shoe` | body `{shoe_id: int|null}` 수동 배정 | 404 활동 없음, 400 비러닝(`NOT_RUNNING`) |
| `DELETE /library/activities/<id>/shoe` | 수동 배정 해제(자동 규칙으로 복귀) | 해석 결과 재반환 |
| `POST /shoes/<id>/assign` | body `{activity_ids: int[≤200]}` 일괄 배정 | `{assigned, skipped_non_running}` |

- 활동 상세 응답(`activity_detail_service`)에 `shoe: {id,name,status,method,conflict}|null` 필드 추가(별도 호출 없이 칩 표시).
- 서비스: `src/services/shoe_service.py`(CRUD·merge·import-gear), `shoe_assignment.py`(해석·집계 SQL), `shoe_status.py`(임계값·상태·문구, 순수 함수). 각 300줄 이하.

## 7. 화면 구성 (한국어 UI)

배치: Library 홈에 **신발 블록**(`LibraryBlock`) 추가 + 1단 라우트. Library 상단 탭은 이미 6개라 탭은 늘리지 않는다(§9 Q1).

| 라우트 | 파일 | 내용 |
|--------|------|------|
| `/library/shoes` | `routes/library/shoes/+page.{ts,svelte}` | 목록 |
| `/library/shoes/[id]` | `routes/library/shoes/[id]/+page.{ts,svelte}` | 상세 |
| (시트) | `lib/components/ShoeFormSheet.svelte` | 추가·수정 폼 |
| (시트) | `lib/components/ShoeAssignSheet.svelte` | 활동 상세에서 신발 선택 |
| (부품) | `ShoeCard.svelte`, `ShoeWearBar.svelte` | 카드·마모 막대(`ProgressBar` 재사용) |
| API | `lib/api/shoes.ts` | `apiFetch` 래퍼, 타입 정의 |

정보 계층:
- **Level 0** (목록 상단 한 줄): 가장 급한 신발 1개의 의미 문구 — 예 "페가수스 40, 교체를 준비할 때예요". 없으면 "모든 신발이 충분히 남았어요".
- **Level 1** (카드): 이름 · 카테고리 · 마모 막대(색) · `612 / 700 km`(단위 작게) · 마지막 사용일 · 기본 신발 배지. 정렬: replace → soon → ok, 같은 상태는 최근 사용 순. 은퇴 신발은 접힌 "은퇴한 신발 N켤레" 섹션.
- **Level 2** (상세): 마일리지 구성(시작 거리 + 배정 합계, method 별 km), 소스 비교("Strava 기준 640 km — RunPulse 612 km, 차이는 RunPulse 에 없는 활동·비러닝 포함 가능"), 월별 km, 배정 활동 목록(`ActivityRow` + method 태그 "직접/Garmin/기본 규칙", 충돌 표시).

활동 상세(`/library/[id]`): 요약 아래 신발 칩 "신발 · 페가수스 40 (기본 규칙)"(아이콘은 `Icon.svelte`, 이모지 금지) → 탭 시 `ShoeAssignSheet`(활성 신발 목록, "신발 없음", "자동으로 되돌리기"). 비러닝 활동은 칩 미표시.

빈·오류 상태:
- 신발 0켤레 + 미연결 gear 있음: `EmptyState` "Strava·Garmin 에 신발 N켤레가 있어요" + [가져오기](`import-gear`) + [직접 추가].
- 신발 0켤레 + gear 없음: "신발을 등록하면 마일리지와 교체 시기를 알려드려요" + [신발 추가].
- 로드 실패: `LoadResult` + `ErrorState failure=` + `depends('app:shoes')` 재로드 키. 404 상세는 EmptyState "신발을 찾을 수 없어요" + "← 목록으로".
- 쓰기 실패: 시트 안 인라인 오류(문구는 `failureMessage`), 409 는 서버 메시지 표시.
- 접근성: 마모 막대 `role="meter"` + `aria-valuenow/max` + 상태 문구 텍스트(색만으로 전달 금지).

## 8. 구현 작업 분해

| ID | 작업 | 테스트 포인트 |
|----|------|---------------|
| T1 | 조사 마감: 운영 DB 사본에서 `activity_summaries.gear_id` 소스별 채움률, Intervals raw payload gear 키, Garmin `get_activity_gear` 응답 형태, running raw type 중 trail/treadmill 값 확인 → §4 kind 매핑 표 확정 | 결과를 이 문서 §1 에 기록(코드 없음) |
| T2 | 스키마 v42: `db_schema_v42.py`, `db_setup.py` DDL·`SCHEMA_VERSION=42`, `export_groups` 에 `user_shoes`·`activity_shoe` 추가 | v41 DB → v42 멱등 2회 실행, 신규 DB DDL 동일성, 부분 유니크(활성 기본 신발 1개/kind) 위반 시 IntegrityError, gear 행 삭제 없이 shoe 삭제 시 `shoe_id` NULL |
| T3 | sync 보강: Strava `sync_gear` 의 `b…` → `gear_type='bike'`; Garmin `sync_activity_gear` 를 러닝 신규 활동에만 배선(실패 시 1회 재시도 → 로그 → 계속); `strava_shoes.py` → `gear(source='strava_export', source_gear_id=정규화 이름)`, CSV `Activity Gear` → 해당 행 `gear_id` | 자전거 gear 분류, Garmin gear API 실패해도 sync 계속, CSV 임포트 inserted>0, 재임포트 멱등 |
| T4 | `shoe_status.py`: 기본 임계값 표, 상태·남은 km·문구, 대회 21일 보조 문구 | 경계값 79.9/80/99.9/100%, `retire_km` 우선, 은퇴 제외 |
| T5 | `shoe_assignment.py`: 그룹 단위 해석(manual > source > rule > none), 충돌, 날짜 제약, 마일리지 집계 | 우선순위 4종, 그룹 대표 행 변경 후 manual 유지, 비러닝 제외, 은퇴 후·개시 전 미배정, `default_since` 이전 미배정, 충돌 플래그 |
| T6 | `shoe_service.py`: CRUD·기본 신발 교체 트랜잭션·merge·import-gear(이름 묶음) | merge 후 링크·배정 이관, import-gear 재실행 시 중복 생성 0 |
| T7 | `routes_shoes.py` + 활동 신발 PUT/DELETE + 일괄 배정, `activity_detail_service` 에 `shoe` 필드 | 봉투 형식, Origin 없는 쓰기 403, 검증 400, 비러닝 400, 409 `GEAR_LINKED`, 200건 초과 400 |
| T8 | `lib/api/shoes.ts` + `/library/shoes` 목록·빈 상태·Library 홈 블록 | `frontend/tests` 단위(정렬·상태 문구 매핑), LoadResult 분기 |
| T9 | `/library/shoes/[id]` 상세 + `ShoeFormSheet` | 폼 검증 문구, 은퇴/복귀, 삭제 확인, 404 EmptyState |
| T10 | 활동 상세 신발 칩 + `ShoeAssignSheet` + 일괄 배정 UI | 칩 method 라벨, "자동으로 되돌리기" 후 표시 갱신, 비러닝 미표시 |
| T11 | 마감: 브라우저 스모크(목록→상세→수정→활동 배정→일괄 배정), a11y 스캔 기준선, `check_docs.py`, BACKLOG·DONE 갱신 | 실제 페이지 로드 확인(합성 테스트만으로 종료 금지) |

순서: T1 → T2 → (T3, T4) → T5 → T6 → T7 → T8 → T9 → T10 → T11. T3 은 T2 이후 독립 진행 가능.

## 9. 미결 사항 (추천안 명시)

| ID | 질문 | 추천안 |
|----|------|--------|
| Q1 | 화면 위치 | Library 홈 블록 + `/library/shoes`(탭 추가 안 함). 설정(`/data/settings`)은 "데이터 관리" 성격이라 부적합 |
| Q2 | 소스 gear 자동으로 신발 생성? | 동기화 중 자동 생성하지 않음. 빈 상태·목록 상단 제안 카드의 [가져오기] 한 번으로 생성(이름 같으면 묶음). 사용자 소유 데이터 원칙 |
| Q3 | Today 에 교체 알림? | `replace`(≥100%) 이고 최근 7일 내 그 신발을 신은 경우에만 Today 하단 한 줄. `soon` 은 Today 미노출 |
| Q4 | 마일리지에 소스 누적값 사용? | 사용 안 함(§5). 소스 비교로만 표시 — 투명성 원칙 |
| Q5 | 자동 배정 결과를 저장? | 저장 안 함(읽기 시점 계산). 사용자 데이터 규모(수천 활동)에서 집계 비용 무시 가능, 백필·재계산 불필요. 느리면 그때 캐시 |
| Q6 | 기본 임계값 | §5 표(데일리 700 · 템포 600 · 레이스 400 · 트레일 700, 경고 80%) |
| Q7 | 신발을 소스(Strava/Garmin)로 역동기화? | 하지 않음(쓰기 API·권한 범위 밖). LATER 후보 |
| Q8 | 기간(나이) 기반 교체 알림 | v2 범위 제외(거리 기준만). LATER 후보 |
| Q9 | v1 `shoes` 잔재 테이블 정리 | v42 에서 건드리지 않음. 존재 DB 확인 후 별도 정리 |
