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
