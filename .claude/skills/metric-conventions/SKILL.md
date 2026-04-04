---
name: metric-conventions
description: >
  RunPulse 메트릭(calculator) 추가/수정 시 준수해야 할 규칙.
  system-architect에 프리로드되며, 메트릭 관련 작업 시 자동 적용.
user-invocable: false
---

# RunPulse 메트릭 규칙

## Calculator 필수 메타데이터

모든 MetricCalculator 서브클래스는 다음을 선언해야 한다:

- name: 고유 식별자 (snake_case, 예: "relative_effort")
- display_name: 사용자에게 보이는 이름 (한국어 가능)
- description: 1-2문장 설명
- scope_type: "activity" 또는 "daily"
- category: rp_load, rp_performance, rp_efficiency, rp_readiness,
            rp_risk, rp_recovery, rp_prediction, rp_distribution,
            rp_endurance, rp_trend, rp_classification 중 하나
- unit: SI 단위 (AU, sec/km, W, %, 점 등)
- requires: 의존하는 메트릭 이름 리스트
- produces: 생산하는 메트릭 이름 리스트
- provider: "runpulse:formula_v1" (기본)
- ranges: 범위 해석 딕셔너리 (예: {"poor": "0-30", "good": "70-100"})
- higher_is_better: True/False/None

## Calculator 작성 템플릿

[calculator-template.md](calculator-template.md) 참조.

## 규칙

1. CalcContext API만 사용 (ADR-009)
2. 데이터 부족 시 빈 리스트 반환 (에러 금지)
3. ConfidenceBuilder로 confidence 값 설정 (0.0-1.0)
4. metric_registry.py에 MetricDef 등록
5. requires에 선언하지 않은 메트릭을 내부에서 조회하지 마라
6. produces에 선언하지 않은 메트릭을 저장하지 마라
7. 테스트: 최소 정상 케이스 1개 + 데이터 부족 케이스 1개
