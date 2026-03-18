# RunPulse 사용 가이드

## 일상 워크플로

### 매일 아침 (동기화 + 오늘 요약)

    cd ~/projects/RunPulse
    python src/sync.py --source garmin --days 1
    python src/analyze.py today

### 러닝 후 (전체 동기화 + 비교)

    python src/sync.py --source all --days 1
    python src/analyze.py today
    python src/plan.py done

### 주말 (주간 리포트 -> Genspark 분석)

    python src/sync.py --source all --days 7
    python src/analyze.py full --clipboard
    # Genspark AI Chat에 붙여넣기
    # "이 러닝 데이터를 분석하고 다음 주 훈련 계획을 제안해줘"

### 월간 (추세 + 목표 점검)

    python src/analyze.py trends
    python src/plan.py context --clipboard
    # Genspark에 붙여넣기
    # "장기 추세를 분석하고 목표 달성을 위한 조언을 해줘"

## 목표 관리

    python src/plan.py goal add --name "서울마라톤" --date 2026-11-01 --distance 42.195 --target-time "3:30:00"
    python src/plan.py goal list

## 훈련 계획

    python src/plan.py week           # 이번 주 계획 보기
    python src/plan.py context --clipboard  # Genspark용 컨텍스트 생성

## 웹 대시보드 (선택)

    python src/serve.py &
    # 브라우저에서 http://localhost:8080 접속
    # PC에서 접속하려면 같은 네트워크에서 http://폰IP:8080

## Genspark AI Chat 활용 패턴

### 패턴 1: 오늘 분석
analyze.py today 출력을 Genspark에 붙여넣고:
"이 오늘의 러닝 데이터를 어제와 비교 분석해줘. 개선점과 주의사항을 알려줘."

### 패턴 2: 주간 계획 요청
plan.py context 출력을 Genspark에 붙여넣고:
"현재 피트니스 상태를 기반으로 다음 주 훈련 계획을 만들어줘. 요일별로 구체적인 거리와 페이스를 제안해줘."

### 패턴 3: 레이스 준비
plan.py context 출력 + 목표 정보를 Genspark에 붙여넣고:
"서울마라톤(11월 1일, 목표 3시간 30분)까지 남은 기간 동안의 훈련 계획을 4주 단위로 만들어줘."

### 패턴 4: 컨디션 조정
오늘 웰니스 데이터를 붙여넣고:
"오늘 HRV가 낮고 수면 점수가 좋지 않은데, 원래 계획된 인터벌 훈련을 어떻게 조정해야 할까?"
