---
name: design-audit
description: >
  RunPulse 설계-구현 대조 검증 체크리스트.
  design-verifier 에이전트에 프리로드된다.
user-invocable: false
---

# 설계-구현 대조 검증 절차

## 사용법

이 스킬은 design-verifier 에이전트가 자동으로 참조한다.
검증 대상 Phase에 따라 해당 섹션의 체크리스트를 적용한다.

상세 체크리스트는 [checklist.md](checklist.md) 참조.

## 검증 원칙

1. 정량적 검증 우선: "테이블이 맞는지"가 아니라 "테이블이 12개인지" 확인
2. 코드가 진실: 설계 문서와 코드가 다르면, 코드가 맞고 문서를 수정해야 함
3. 양방향 검증: 설계에 있는데 코드에 없는 것 + 코드에 있는데 설계에 없는 것
4. 누적 검증: Phase 4 검증 시 Phase 1-3도 깨지지 않았는지 확인
