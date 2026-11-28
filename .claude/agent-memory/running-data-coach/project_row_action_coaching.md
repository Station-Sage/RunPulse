---
name: project-row-action-coaching
description: 행 액션(move/reduce/rest/skip) 코칭 규칙 설계 2026-10-09 — 하드 간격·같은 주 move, 품질은 reps 축소, load_delta 식, 승인 대기
metadata:
  type: project
---
2026-10-09 DESIGN-PLAN-ROW-ACTION-COACHING.md(phase-7-ui-renewal)에 작성, 결정 필요 4건 승인 대기.

**Why:** 이 러너는 하드 세션 간 간격이 거의 항상 6일 이상(37건 중 1일 간격 1회), 롱런은 일요일, 실제 주간 km가 계획의 약 40~45%(ISO 40~41). planner 인터벌 distance_km는 반복 일부(3.2km)만 저장돼 % 감소가 무의미. 주간 TRIMP ≈ km×8.8×유형계수(중앙 오차 7.2%, 표본 내).

**How to apply:** move는 같은 ISO 주·+3일·하드 사이 1일 비하드(현 구조에서 화 Q는 이동 불가가 의도). 품질 reduce는 reps/work 구간만, 페이스 불변. 경고는 replan 유도로 모으고 비난 금지. 관련 [[project-plan-engine-u16]].
