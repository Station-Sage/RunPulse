# Phase 7 UI Renewal — 화면 카탈로그 · 공통 패턴

[← 목차](03-screen-catalog.md)

## 7. 공통 패턴 요약

### 7-1. 우측 패널 사용 원칙 (P2 Drillable Everything)

*표기 주의: 이 드릴다운 단계(요약→분해→원본)는 Today의 관여 계층 L0~L3(`03a-today.md`,
`00-diagnostic-and-direction.md` §5.1)와 다른 축이다 — 혼동을 피하기 위해 "D1~D3"로
표기한다(Drill 1~3, D1~D5 데이터 레이어 ADR 번호와도 별개).*

| 드릴다운 단계 | 데스크탑 | 모바일 |
|-------------|---------|--------|
| D1 요약 | 메인 화면 <MetricCell> | 메인 화면 카드 |
| D2 분해 | 우측 패널 슬라이드인 | 풀스크린 슬라이드업 |
| D3 원본 | Library 이동 (하단 탭 전환) | Library 이동 |

### 7-2. Provider 배지 표시 위치 (P3 Provider Transparency)

모든 `<MetricCell>`, `<MetricBreakdown>`, `<ProviderComparison>` 컴포넌트에서  
데이터 출처 배지는 생략하지 않는다. Provider 없이 표시되는 숫자는 없다.

### 7-3. EvidenceQuote 칩 동작 (P1 Evidence-First)

- AI가 생성하는 모든 결론(Today 브리핑, Coach 답변, Today L2 성장 내러티브)에 `<EvidenceQuote>` 칩 필수
- 칩 탭 → 우측 패널에서 원천 데이터 표시
- 원천 데이터가 없는 결론은 "(데이터 부족 — 추후 업데이트)" 레이블 표시

### 7-4. 상태 기반 배지 (P7 State-Bound Plan)

Plan 관련 세션 카드에서 상태 조정이 필요할 때:  
`⚠ 상태 조정: [근거] → [변경 내용]` 형식 + [수락] / [원래대로] 버튼 쌍으로 표시한다.

### 7-5. QuickInput 배치 원칙 (P6 One Finger Reach)

`<QuickInput>`은 Today 전용이 아니다. 다음 위치에 `compact=true` 모드로 배치한다:

| 화면 | 배치 위치 | 의도 |
|------|-----------|------|
| Today L0 (1-A) | 권고 카드 바로 아래 — compact(접힌 한 줄 · 입력 후 요약). 2026-09-24 갱신 | 권고(오늘 무엇을 할까)가 첫 화면 히어로, 입력은 탭 한 번 |
| 활동 상세 (3-C) | 하단 — compact | 활동 직후 컨디션 기록 |
| Coach 홈 (5-A) | 스레드 목록 하단 — compact | Coach 질문에 컨텍스트 자동 제공 |
| Coach 세션 상세 (5-G) | 세션 메모 영역 | 세션 후 메모와 일체화 |

이미 당일 입력이 있으면 `compact+complete` 상태(한 줄 요약)로 표시하고 탭 시 수정 모드로 전환한다.

---

## 작성 이력

- v0.2 (2026-09-22): REVIEW-03 반영 — 7-1 드릴다운 레벨 표기를 L1~L3 → D1~D3으로 변경
  (Today의 관여 계층 L0~L3과의 명칭 충돌 해소). 7-3 "Story 내러티브" → "Today L2 성장
  내러티브". 7-5 표의 화면 참조를 신 IA 화면 번호로 갱신.
- v0.1 (2026-06-10): 초안

