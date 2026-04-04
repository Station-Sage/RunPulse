---
name: product-design-conventions
description: >
  RunPulse 제품 경험 설계 규칙. UI/UX 원칙, 메트릭 표시 규칙, AI 코칭 패턴.
  product-architect 에이전트에 프리로드된다.
user-invocable: false
---

# RunPulse 제품 설계 규칙

## 핵심 수치 빠른 확인 (파일 전체를 읽지 말고 이 명령어 사용)

```bash
# Blueprint(화면) 목록
grep "register_blueprint" src/web/app.py

# 뷰 파일 목록
ls src/web/views_*.py

# SEMANTIC_GROUPS (메트릭 카테고리)
python3 -c "from src.utils.metric_groups import SEMANTIC_GROUPS; print(list(SEMANTIC_GROUPS.keys()))"

# AI Coach 관련 파일
ls src/web/views_ai_coach*.py src/ai/chat_engine*.py

# 템플릿 목록
find templates/ -name "*.html" | head -30

# 대시보드 카드 구조
ls src/web/views_dashboard_cards*.py
```

## 세 원칙 (모든 UI/UX 결정의 기준)

1. 데이터 통합과 소유권 — 4개 소스를 하나로, 로컬 데이터 소유
2. 투명한 분석 — 블랙박스 금지, 계산 과정 공개
3. 맥락 있는 안내 — 숫자만이 아니라 "그래서 뭘 해야 하는지"

## 정보 계층 원칙

모든 화면은 3단계 정보 계층을 따른다:

Level 0 (즉시 보임): 핵심 메시지 1-2개. 숫자가 아니라 의미.
  예: "몸이 지쳐 있어요" (CRS 35)

Level 1 (한 번 탭): 핵심 메트릭 3-5개와 간단한 해석.
  예: CIRS 62 (높음), TSB -15, 수면 65점

Level 2 (깊이 파고들기): 전체 메트릭, 계산 과정, 소스 비교.
  예: "CIRS는 ACWR(1.4) x 0.3 + LSI(1.6) x 0.25 + ..."

## 메트릭 표시 규칙

상세 규칙은 [metric-display-rules.md](metric-display-rules.md) 참조.

핵심 원칙:
- 숫자 먼저가 아니라 의미 먼저
- 범위 해석을 색상으로 표시 (초록=좋음, 노랑=주의, 빨강=위험)
- 단위는 항상 표시하되 작게
- 소스 비교는 별도 패널/토글로

## AI 코칭 대화 원칙

- 코치 톤: 친구 같은 전문가 (친근하지만 근거 있는)
- 숫자 인용: 자연어 해석 먼저, 괄호 안에 메트릭명과 값
  나쁜 예: "CRS가 35점입니다."
  좋은 예: "지금 몸이 꽤 지쳐 있어요. (CRS 35)"
- 투명성: 모든 조언에 "왜?"를 누르면 근거 메트릭이 보여야 함
- 맥락 적응: 대회 2주 전 vs 베이스 훈련 중 → 다른 해석

## 경쟁 앱 대비 차별점 (항상 기억할 것)

RunPulse만의 것:
- 4개 소스 통합 뷰 (Strava는 자기 데이터만 보여줌)
- 소스 비교 기능 (Garmin 10.02km vs Strava 10.05km)
- 계산 과정 투명 공개 (Garmin Training Effect는 블랙박스)
- 메트릭 진화 추적 (같은 날의 UTRS가 버전별로 다를 수 있음)

RunPulse가 하지 않는 것:
- 소셜 네트워크 (Strava 영역)
- 라이브 GPS 트래킹 (시계 앱 영역)
- 경직된 12주 플랜 PDF
