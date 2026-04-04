# 메트릭 표시 규칙

## 메트릭 유형별 표시 패턴

### 점수형 (0-100)
예: CRS, UTRS, RMR, CIRS, REC, Marathon Shape, RRI
- 원형 게이지 또는 반원 게이지
- 범위별 색상: ranges 필드의 구간에 따라
- 텍스트: 범위 라벨 (예: "good", "poor") + 점수

### 비율형
예: ACWR, LSI, Monotony, RTTI
- 수평 바 또는 숫자 + 범위 표시
- 최적 구간 강조 (예: ACWR 0.8-1.3이 초록)

### 추세형
예: ADTI, TEROI, CTL
- 미니 차트 (sparkline) 또는 화살표 (상승/하락/유지)
- 기간: 기본 28일

### 페이스/속도형
예: GAP, FEARP, eFTP
- mm:ss/km 형식
- 대소 비교: lower is better 표시

### 예측형
예: DARP, VDOT, Critical Power
- 목표 대비 현재 위치 표시
- 레이스 거리별 예측 시간 표

### 복합형 (JSON)
예: Critical Power (cp + w_prime + r_squared), TIDS (분포)
- 주값 + 보조값 구분 표시
- json_value에서 추출하여 서브 항목으로

## 소스 비교 표시

같은 metric_name에 여러 provider가 있을 때:
1. is_primary=1 값을 기본 표시
2. "소스 비교" 토글/패널에 provider별 값 나열
3. SEMANTIC_GROUPS의 primary_strategy에 따라:
   - prefer_runpulse: RunPulse 값이 기본
   - show_all: 모든 소스를 동등하게 표시

## 색상 체계

각 calculator의 ranges 필드를 참조:
- ranges의 첫 번째 구간 (가장 낮은/나쁜): 빨강 계열
- 중간 구간: 노랑/주황 계열
- 마지막 구간 (가장 높은/좋은): 초록 계열
- higher_is_better=false인 경우: 색상 순서 반전
