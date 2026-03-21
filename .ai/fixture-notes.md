# Fixture 주의사항

## 병합 이력

`feature/data-pipeline-foundation` 브랜치 (2026-03-21 머지)에서 가져온 fixture 파일들.
이 브랜치는 현재 DB 스키마보다 **이전 버전**을 기준으로 작성되어 있다.

---

## 현재 fixture 상태

### tests/fixtures/api/intervals/ — 4종 존재

| 파일 | 내용 | 비고 |
|------|------|------|
| `activities_minimal.json` | Intervals.icu activity 최소 payload 1건 | DB 스키마 변경 전 기준 |
| `activities_edge_missing_optional_fields.json` | optional 필드 누락된 edge-case payload 1건 | |
| `wellness_minimal.json` | wellness 최소 payload | |
| `wellness_edge_missing_fields.json` | wellness 일부 필드 누락 edge-case | |

### tests/helpers/fixture_loader.py
- `fixture_path(*parts)` — `tests/fixtures/` 기준 경로 반환
- `read_json_fixture(*parts)` — JSON fixture 로드
- `read_text_fixture(*parts)` — 텍스트 fixture 로드

---

## 알려진 불일치 사항

현재 DB 스키마 (`running.db`) 및 sync 파서는 여러 차례 확장/변경되었다.
아래 항목은 fixture 갱신 시 확인이 필요하다.

### Intervals.icu
- 현재 `sync/intervals.py`는 `from_date`, `to_date` 파라미터 지원, `fill_null_columns`, `store_raw_payload` 적용
- fixture JSON의 필드 구조는 현재 파서와 대체로 호환되나, 아래 필드 누락 가능:
  - `icu_training_load`, `icu_intensity`, `icu_hrss` → `activity_detail_metrics` 저장 경로 확인 필요

### Garmin
- `tests/fixtures/api/garmin/` — 아직 fixture 없음 (.gitkeep만 존재)
- 현재 파서는 wellness 10종 + activity detail 대폭 확장된 상태

### Strava / Runalyze
- `tests/fixtures/api/strava/`, `tests/fixtures/api/runalyze/` — 아직 fixture 없음

---

## fixture 추가 시 체크리스트

1. `tests/fixtures/README.md` 의 파일명 규칙 참조
2. 민감정보(토큰, 이메일, 좌표) 제거 확인
3. 현재 `sync/` 파서가 기대하는 필드와 일치 여부 확인
4. 대응하는 테스트를 `tests/test_sync_*.py` 또는 별도 `test_fixtures_*.py`에 추가

---

## 참고

- `tests/fixtures/README.md` — fixture 작성 가이드 (파일명 규칙, 민감정보 처리)
- `tests/test_fixture_loader.py` — fixture_loader 헬퍼 테스트
- `tests/test_fixtures_layout.py` — fixture 디렉토리 구조 레이아웃 테스트
- IV-5 항목 (`todo.md`) — 익명화 fixture dataset 설계 및 tests/fixtures 구조 정리
