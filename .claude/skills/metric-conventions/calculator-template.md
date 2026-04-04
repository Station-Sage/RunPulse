# Calculator 작성 템플릿

## 파일: src/metrics/<name>.py

from src.metrics.base import (
    MetricCalculator, CalcContext, CalcResult, ConfidenceBuilder
)

class <Name>Calculator(MetricCalculator):
    name = "<snake_case_name>"
    display_name = "<한국어 이름>"
    description = "<1-2문장 설명>"
    scope_type = "activity"  # 또는 "daily"
    category = "rp_<category>"
    unit = "<단위>"
    requires = ["<dependency_1>", "<dependency_2>"]
    produces = ["<metric_name>"]
    provider = "runpulse:formula_v1"
    ranges = {
        "poor": "0-30",
        "moderate": "30-60",
        "good": "60-100"
    }
    higher_is_better = True  # 또는 False, None

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # 1. 필요한 데이터 가져오기 (CalcContext API만 사용)
        # 2. 계산
        # 3. confidence 설정
        # 4. CalcResult 리스트 반환
        #    데이터 부족 시 빈 리스트 반환
        return []

## 테스트 파일: tests/test_<name>.py

- test_compute_normal: 정상 데이터로 계산 확인
- test_compute_no_data: 데이터 없을 때 빈 리스트 반환 확인
- test_metadata: name, category, requires, produces 확인

## 등록

1. src/metrics/engine.py: ALL_CALCULATORS에 추가
2. src/utils/metric_registry.py: MetricDef 추가
3. python scripts/gen_metric_dictionary.py 실행
