---
name: project-pred-r4
description: 예측 리뉴얼 r4(2026-09-26) 핵심 결론 — 세트 Daniels 등가시간 환산, 칼만 결합, 내장 Daniels 표 오류, 명세 미완 상태
metadata:
  type: project
---
r4 설계 문서는 REVIEW-07 §R4, REVIEW-09-signal-design-r4.md, specs/PRED-99. 코드 명세(PRED-2x/5x 등)는 미완(INDEX r4 표에 "미작성" 표시).

- 세트→VDOT: t_eq = 60분(ρ≤0.2) ~ 11.03분(ρ≥1.0) ln ρ 보간 → I 편향 −2.1→0. 세트는 기온 정규화 안 함, 대회만.
- 결합: 로컬 레벨 칼만(σ대회 1.0, σ세트 1.75, σH 1.25, q 0.01 휴리스틱). 대회 D-0 1.63%/D-28 1.75% vs r3 1.26/2.10(r3는 표본 내 낙관, 대회 간 변동 바닥 ≈1.8%).
- src/utils/daniels_table.py 표는 Daniels 식과 불일치 + 3곳이 없는 src.metrics.daniels_table import (P7-PRED-85, 사용자 확인 필요).
- 사용자는 임의 상수를 싫어함 → 모든 상수에 (a)문헌/(b)데이터/(c)휴리스틱+민감도 표기 요구.

**Why:** 다음 세션이 명세 작성을 이어받아야 함. **How to apply:** 재개 시 INDEX r4 표 순서대로 명세 작성, 분석판 수치를 계산기 값으로 교체(PRED-99 U-12).
