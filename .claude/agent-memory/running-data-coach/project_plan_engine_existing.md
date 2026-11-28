---
name: project-plan-engine-existing
description: 2026-10-10 v1(11/22) 계획에 v2 적용 검토 — 사용자 승인 재계획 추천, anchor별 rules_version 필요, X2~X5 결함
metadata:
  type: project
---
2026-10-10 DESIGN-P7-PLAN-ENGINE-EXISTING.md(ux-review-2026-09) 작성, Q1~Q7 사용자 결정 대기.
추천: D4 부분 번복 — 자동 X, 미리보기·승인 재계획으로 다음 월요일부터 v2. anchor 10/19 목표.

**Why:** 백테스트 하드 0·재계획 안전장치(T1~T7)로 D4 근거 해소. 그러나 rules_version이 goal 단위라 flip 시 접두 주 목표 변경·undo 불일치 → plan_replans.rules_version(v35) 필요.
시뮬 발견: default_run_days 미연결(mask 0이면 주 3 하드·대회 전날 8.9km), MP_now가 VDOT M(5:03)이라 r3(5:15)보다 빠른 처방 4:52, 재계획 시작 km가 prev4 이상으로만(입력 하향 불가), 휴식 병합 행에 이지 페이스 잔존, long_mp structure에 MP 구간 없음.
러너 사실: 9/14 이후 최장 10km, 이행 45~57%, 주 4일, r3 3:41:25.

**How to apply:** 기존 계획 이행 논의 시 E1(anchor rv)부터. 관련 [[project-plan-engine-u16]] [[project-row-action-coaching]].
