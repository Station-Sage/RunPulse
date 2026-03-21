# 테스트 fixture 안내

이 디렉토리는 데이터 파이프라인 및 파서 검증에 사용할
정제(sanitized)된 샘플 payload / import 파일을 저장한다.

## 목적
- 파서 회귀 테스트를 결정적으로 유지한다.
- 실제 수집 데이터와 임시 로컬 테스트 데이터를 분리한다.
- 소스별 edge case를 재현 가능하게 만든다.

## 디렉토리 구조
- `api/intervals/` - Intervals.icu API payload 샘플
- `api/garmin/` - Garmin API payload 샘플
- `api/strava/` - Strava API payload 샘플
- `api/runalyze/` - Runalyze API payload 샘플
- `history/garmin/` - exported activity history 파일(FIT/TCX/GPX)
- `history/strava/` - exported activity history 파일

## 파일명 규칙
파일명은 **소스 + 엔티티 + 시나리오**가 드러나게 짓는다.

권장 패턴:
- `<entity>_minimal.json`
- `<entity>_edge_missing_fields.json`
- `<entity>_edge_null_values.json`
- `<entity>_regression_<short_issue_name>.json`

예시:
- `activity_minimal.json`
- `wellness_edge_missing_fields.json`
- `activity_regression_timezone_offset.json`

## 민감정보/개인정보 정리 규칙
절대 커밋하지 말 것:
- API token
- refresh token
- session cookie
- 이메일 주소
- 가능하면 실제 athlete ID
- 민감한 정확한 위치 좌표(집/회사 등)

fixture 추가 전 체크:
- secret 제거
- 식별 가능한 값은 placeholder로 치환
- 테스트에 필요한 최소 크기로 축소
- 파서/회귀 케이스에 필요한 필드만 남김
- 구조적 현실성은 유지해서 실제 입력 형태와 너무 다르지 않게 함

## fixture 분류
### 1. minimal
가장 작은 정상 입력 샘플.  
정상 파싱이 되어야 하는 최소 payload.

사용 목적:
- smoke test
- 필수 필드 검증
- 기본 정규화 확인

### 2. edge-case
누락, null, 빈 배열, 이상값 등 비정상/경계 상황 샘플.

사용 목적:
- optional field 처리 검증
- null-safe parsing 확인
- fallback 동작 확인
- schema drift 내성 확인

### 3. regression
과거 실제 버그나 파싱 실패를 재현하는 샘플.

사용 목적:
- 고친 버그 재유입 방지
- 왜 이 케이스가 필요한지 문서화

## 소스별 최소 권장 세트
### Intervals
- 최소 activity payload 1개
- 최소 wellness payload 1개
- wellness 일부 필드만 있는 edge-case payload 1개

### Garmin
- exported activity 파일 1개
- 가능하면 API 형태 샘플 1개

### Strava
- activity payload 1개
- optional field가 누락된 edge-case payload 1개

### Runalyze
- 현재 parser 가정을 대표할 수 있는 activity 또는 metric payload 1개

## 테스트 작성 원칙
- 안정적이고 의미 있는 필드만 assert 한다.
- raw payload 전체 동일성 비교처럼 깨지기 쉬운 방식은 피한다.
- smoke test + 핵심 정규화 검증 중심으로 작성한다.
- fixture별 특수 검증은 관련 parser test 가까이에 둔다.
- regression fixture는 왜 필요한지 짧은 설명을 남긴다.

## 참고
fixture는 대용량 개인 기록 보관소가 아니다.  
작고 선별된 샘플을 통해 데이터 파이프라인 동작을 재현 가능하게 만드는 것이 목적이다.
