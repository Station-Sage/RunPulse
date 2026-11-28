---
name: project-plan-engine-u16
description: 계획 엔진 R6·R7(D4)과 P7-PLAN-ENGINE 설계 확정(2026-10-05) — 목표별 규칙 버전 고정, 백테스트는 안전·실행가능성 게이트
metadata:
  type: project
---
2026-10-05 DESIGN-U16-PLAN-ENGINE.md(ux-review-2026-09)에 확정. 11/22 풀 목표(goal id=1, 3:19 목표)는 v1 규칙 유지·재생성 금지; 새 목표만 `plan_rules_version=2`.

**Why:** 풀코스 기록이 1건(2025-10-18 경주 3:42:12)뿐이라 계획 최적성 백테스트는 불가 → 하드 게이트(G1~G8, 100%)·소프트 게이트(F1~F5) 방식. 이 러너는 과거 롱런 비중 64%(32km/주50km)였고 주 러닝 일수 중앙값 3~4.

2026-10-05 롱런 하한·상한 재설계 제안서 DESIGN-U16-LONGRUN.md(RunPulse-p0, 승인 대기). 핵심 발견: G3 5.0km는 _recap_long 고정점 L=rQ/(1-r), G6 20건도 같은 볼륨 유실 원인, G2 1건은 게이트 360초 고정 페이스 불일치, 풀 피크 롱런은 150분·feasible_week_km(r=0.35)이 묶음, start_km=0이면 v2 목표가 v1로 빠짐.

**How to apply:** 계획 엔진 작업 시 이 문서의 게이트 수치를 기준으로 삼고 느슨하게 바꾸지 말 것. 롱런 비율 r=0.35/0.45 분기(D-U16-4)는 이 러너 데이터 근거. 관련 [[project-pred-r4]].
