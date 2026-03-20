# RunPulse 사용 가이드

## 일상 워크플로

### 매일 아침 (동기화 + 오늘 요약)

    cd ~/projects/RunPulse
    python src/sync.py --source garmin --days 1
    python src/analyze.py today

### 러닝 후 (전체 동기화 + 비교)

    python src/sync.py --source all --days 1
    python src/analyze.py today
    python src/plan.py today

### 주말 (주간 리포트 -> Genspark 분석)

    python src/sync.py --source all --days 7
    python src/analyze.py full --clipboard
    # Genspark AI Chat에 붙여넣기
    # "이 러닝 데이터를 분석하고 다음 주 훈련 계획을 제안해줘"

### 월간 (추세 + 목표 점검)

    python src/analyze.py full
    python src/plan.py --help
    # Genspark에 붙여넣기
    # "장기 추세를 분석하고 목표 달성을 위한 조언을 해줘"

## 목표 관리

    python src/plan.py goal add --name "서울마라톤" --date 2026-11-01 --distance 42.195 --target-time "3:30:00"
    python src/plan.py goal list

## 훈련 계획

    python src/plan.py week           # 이번 주 계획 보기
    python src/plan.py week
    # 주간 계획을 확인한 뒤 필요하면 Genspark에 붙여넣기

## 웹 대시보드 (선택)

    python src/serve.py &
    # 브라우저에서 http://localhost:8080 접속
    # PC에서 접속하려면 같은 네트워크에서 http://폰IP:8080

## Genspark AI Chat 활용 패턴

### 패턴 1: 오늘 분석
analyze.py today 출력을 Genspark에 붙여넣고:
"이 오늘의 러닝 데이터를 어제와 비교 분석해줘. 개선점과 주의사항을 알려줘."

### 패턴 2: 주간 계획 점검
plan.py week 또는 today 출력을 Genspark에 붙여넣고:
"현재 피트니스 상태를 기반으로 이번 주 훈련 배치와 회복 균형을 점검해줘."

### 패턴 3: 레이스 준비
analyze.py full 출력 + 목표 정보를 Genspark에 붙여넣고:
"서울마라톤(11월 1일, 목표 3시간 30분)까지 남은 기간 동안의 훈련 방향을 4주 단위로 제안해줘."

### 패턴 4: 컨디션 조정
오늘 웰니스 데이터를 붙여넣고:
"오늘 HRV가 낮고 수면 점수가 좋지 않은데, 원래 계획된 인터벌 훈련을 어떻게 조정해야 할까?"


## 웹 workbench 점검 팁

웹 workbench는 현재 read-only 점검과 통합 상태 확인에 유용하다.

실행:

    python src/serve.py
    # 브라우저에서 http://localhost:8080

자주 보는 경로:
- `/db` : DB 테이블별 row 수와 기본 상태 확인
- `/config` : 민감값 노출 없이 설정 존재 여부 확인
- `/sync-status` : 권장 sync 명령 및 서비스 설정 상태 확인
- `/analyze/today` : 오늘 리포트 미리보기
- `/analyze/full` : 전체 리포트 미리보기
- `/payloads` : raw payload / activity_detail_metrics 현황 확인
- `/payloads/view?id=...` : 특정 payload JSON과 연관 metrics drill-down

`/payloads` 필터 예시:

    /payloads?source=intervals
    /payloads?source=intervals&entity_type=wellness&limit=10
    /payloads?source=intervals&entity_type=activity
    /payloads?activity_id=1

Intervals 실데이터 점검 시에는 다음 순서를 권장한다.

1. `/sync-status`에서 명령 예시 확인
2. `python src/sync.py --source intervals --days 28`
3. `/payloads?source=intervals` 로 raw payload 유입 확인
4. `/analyze/today` 로 interval summary / efficiency / zone 분포 sanity 확인
