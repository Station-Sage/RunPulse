---
name: check-data-consistency
description: >
  SSOT(metric_registry.py) ↔ DDL(db_setup.py) ↔ Extractor 데이터 정합성 검증.
  check_data_consistency.py(16개 검사)를 실행한다.
  "데이터 정합성", "consistency 확인", "registry 검증", "extractor 점검" 요청 시 사용.
user-invocable: true
argument-hint: "[--db PATH]"
---

# /check-data-consistency — 데이터 정합성 검증

SSOT ↔ DDL ↔ 실제 DB ↔ Extractor ↔ Validator 교차 검증. (~3초)
커밋 전 `/pre-commit`에도 포함되어 있다.

## 실행

    python3 scripts/check_data_consistency.py

DB까지 검증하려면:

    python3 scripts/check_data_consistency.py --db data/running.db

## 검사 항목 (16개)

| # | 검사 | 대상 |
|---|------|------|
| 1 | SSOT activity_summary ↔ DDL 컬럼 일치 | metric_registry ↔ db_setup.py |
| 2 | SSOT wellness ↔ DDL 컬럼 일치 | metric_registry ↔ db_setup.py |
| 3 | daily_fitness 삭제 여부 | db_setup.py |
| 4 | 카테고리 정합성 (SSOT 내) | metric_registry.py |
| 5 | MetricDef 필드 유효성 (storage/scope/category) | metric_registry.py |
| 6 | MetricDef 중복 이름 | metric_registry.py |
| 7 | alias 충돌 | metric_registry.py |
| 8 | scope 일관성 (wellness→daily, activity_summary→activity) | metric_registry.py |
| 9 | 실제 DB ↔ DDL 컬럼 일치 (--db 옵션 시만) | running.db |
| 10 | Extractor `_metric()` category 값 검증 (16-domain 기준) | *_extractor.py |
| 11 | Extractor `_metric()` 미등록 메트릭 이름 검출 | *_extractor.py |
| 12 | Extractor `_metric()` 폐기 예정 메트릭 이름 검출 | *_extractor.py |
| 13 | Garmin wellness entity_type 이름 일관성 (wellness_* 설계 spec) | garmin_wellness_sync.py, reprocess.py |
| 14 | Calculator category 속성 16-domain 준수 (rp_* 등 구버전 방지) | src/metrics/*.py |
| 15 | Calculator produces ↔ METRIC_REGISTRY 등록 일치 | engine.py × metric_registry |
| 16 | DataValidator _check_* 메서드 수(12개) + CheckResult 필드 정합성 | src/validation/validator.py |

## 결과 해석

- 🔴 오류: 반드시 수정 후 커밋
- 🟠 경고: 내용 확인 후 판단
- 🟡 참고: 정보성, 수정 불필요

## 결과 보고

    ## /check-data-consistency 결과
    - 검사 16개, 🔴 N건, 🟠 N건, 🟡 N건
    - 🔴 목록: (있으면 열거)
    - 🟠 목록: (있으면 열거)
    -> PASS / FAIL (🔴 0건이면 PASS)
