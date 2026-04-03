# Architecture Decision Records (ADR)

## ADR-001: weather_cache UNIQUE 제약에서 ROUND() 제거
- **날짜**: 2026-04-03
- **맥락**: SQLite는 PRIMARY KEY / UNIQUE 제약조건에 표현식(함수 호출)을 허용하지 않음
- **결정**: UNIQUE(date, hour, latitude, longitude, source)로 단순화하고, 좌표 반올림은 INSERT 전 Python에서 수행
- **결과**: 모든 SQLite 버전에서 호환, 정밀도 관리를 애플리케이션 레이어로 이동

## ADR-002: 동적 인덱스 생성 (_safe_create_indexes)
- **날짜**: 2026-04-03
- **맥락**: v0.2 실 DB에 gear_id, source 등 신규 컬럼이 없어 정적 CREATE INDEX가 실패
- **결정**: PRAGMA table_info로 컬럼 존재 여부 확인 후 조건부 인덱스 생성
- **결과**: v0.2 → v0.3 무중단 마이그레이션 가능, 기존 데이터 보존

## ADR-003: metric_store UNIQUE 키 설계
- **날짜**: 2026-04-03
- **맥락**: 동일 메트릭에 대해 여러 provider가 값을 제공할 수 있음
- **결정**: UNIQUE(scope_type, scope_id, metric_name, provider) — provider별 하나의 값만 저장
- **결과**: 다중 소스 비교 가능, is_primary 플래그로 UI 표시값 결정

## ADR-004: SyncResult dataclass로 sync 결과 표준화
- **날짜**: 2026-04-03
- **맥락**: 각 소스 sync 함수가 서로 다른 형식으로 결과를 반환하여 orchestrator에서 통합 처리 어려움
- **결정**: SyncResult dataclass에 status, counts, errors, retry_after를 통합. merge()로 여러 결과 합산. to_sync_job_dict()로 DB 기록 표준화
- **결과**: orchestrator가 소스에 관계없이 동일한 인터페이스로 결과 처리

## ADR-005: payload_hash 기반 변경 감지로 skip-unchanged 구현
- **날짜**: 2026-04-03
- **맥락**: 매번 전체 payload를 DB에 쓰면 불필요한 I/O와 재처리 발생
- **결정**: raw_store.upsert_raw_payload()가 JSON 정렬 후 SHA-256 해시 비교. 해시 동일하면 False 반환 → 하위 처리 skip
- **결과**: 반복 sync 시 변경 없는 데이터 skip, DB 쓰기 최소화

## ADR-006: Strava start_date_local 우선 사용
- **날짜**: 2026-04-03
- **맥락**: Strava API가 start_date(UTC)와 start_date_local 둘 다 반환. extractor가 start_date만 사용하여 다른 소스와 시간대 불일치, dedup 매칭 실패
- **결정**: start_date_local 우선, start_date fallback
- **결과**: cross-source dedup 시간 비교 정확도 향상

## ADR-007: ranges 형식 [low, high] 리스트 통일
- **날짜**: 2026-04-03
- **맥락**: 설계서(보강 #7)는 ranges를 [low, high] 리스트로 정의했으나, 포팅 메트릭이 단일 숫자로 구현됨
- **결정**: 전체 32개 calculator의 ranges를 [low, high] 리스트 형식으로 통일
- **결과**: UI에서 범위 시각화(게이지, 색상 바) 구현 시 일관된 데이터 구조 보장

## ADR-008: category 체계 — 소스 vs RunPulse 분리
- **날짜**: 2026-04-03
- **맥락**: metric_registry의 소스 메트릭은 training_load, efficiency 등 일반 카테고리, RunPulse calculator는 rp_ 접두사 사용
- **결정**: 의도적 분리 유지. 소스 메트릭(garmin/strava/intervals)은 도메인별 카테고리, RunPulse 메트릭은 rp_ 접두사
- **결과**: UI에서 소스별/RunPulse별 필터링 가능, 이름 충돌 방지

## ADR-009: Calculator 데이터 접근 정책 — CalcContext API 전용
- **날짜**: 2026-04-04
- **맥락**: MetricCalculator 내부에서 `ctx.conn.execute()`로 raw SQL을 직접 실행하면, 스키마 변경 시 모든 calculator를 수정해야 하고, MockCalcContext로 단위 테스트가 불가능하며, A/B 테스트 시 입력 데이터를 통제할 수 없음. 메트릭 공식은 지속적으로 변경·확장될 예정이므로 calculator의 순수 함수화가 필수.
- **결정**: Calculator는 반드시 CalcContext API(13개 메서드)만 사용하여 데이터에 접근. `ctx.conn.execute()` 직접 호출 금지. 필요한 쿼리 패턴이 없으면 CalcContext에 새 API를 추가.
- **적용 범위**:
  - Level 1 (필수): 단일 scope metric/wellness → `get_metric()`, `get_wellness()` 등
  - Level 2 (필수): 히스토리 조회 → `get_daily_metric_series()`, `get_activities_in_range()`, `get_activity_metric_series()`, `get_wellness_series()`
- **신규 API (이 정책을 위해 추가됨)**:
  - `get_activity_metric_series(name, days, activity_type?, include_json?)` — activity-scope metric 시계열 + activity_type 필터
  - `get_wellness_series(days, fields?)` — daily_wellness 히스토리
  - `get_activity_metric_text(activity_id, name)` — activity-scope text_value 조회
- **결과**: 32개 calculator 전부 CalcContext API 전용으로 전환 완료. `src/metrics/*.py` 내 `ctx.conn.execute` 잔여 0건. Calculator가 순수 함수로 동작하여 Mock 테스트, A/B 테스트, 스키마 변경 시 영향 최소화.
- **검증**: `grep -rc "ctx.conn.execute" src/metrics/*.py` → 0
