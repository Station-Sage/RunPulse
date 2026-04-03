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
