# Phase 7 UI Renewal — 목업·구현 작업 방향

**문서 상태**: Draft v0.1
**작성일**: 2026-06-10
**전제 문서**: `00`~`07` 설계서, `REVIEW-01`, `REVIEW-02`
**목적**: 설계서 검토 완료 후, 실제 UI/UX를 눈으로 확인하고 구현에
진입하기까지의 작업 순서·산출물·규칙을 고정한다.

---

## 0. 현재 위치

- 설계서 00~07 + BACKLOG 작성 완료, REVIEW-01(정합성)·REVIEW-02(아키텍처
  최적성) 반영 완료 (AO-1~AO-4).
- 미해결: 시각 디자인 실제값(디자인 토큰의 hex/px), 화면의 실제 모습,
  인터랙션 체감.
- 결론: 지금부터는 "보이는 것"을 만들어 방향을 확정하는 단계.

---

## 1. 핵심 원칙 — 토큰은 목업 "안"에서 확정한다

디자인 토큰(`--surface-2`, `--text-xl` 등)을 목업 없이 추상적으로 먼저
확정하는 것은 불가능하다 (눈으로 봐야 정해진다). 따라서:

- 토큰을 **목업 HTML `:root`에 초안값으로 박고**, 화면을 그리면서 눈으로
  보며 그 자리에서 조정한다.
- 마크업에 hex/px **직접 입력 금지**. 모든 스타일은 `var(--token)` 참조.
- 목업이 확정되면 그 `:root` 블록을 그대로 `08-design-system.md`(또는
  `tokens.css`)로 추출한다 → **목업의 부산물로 토큰이 확정된다.**

> 순서: 토큰 확정이 목업 *앞*이 아니라 목업 *안*에서 일어난다.

---

## 2. 작업 순서

### Step 1 — 핵심 화면 HTML 목업 (현재 단계)

전체 22개 화면이 아니라 **핵심 화면 우선**. 8개 원칙·7개 컴포넌트를 가장
넓게 검증하는 화면부터.

| 우선순위 | 화면 | 검증하는 컴포넌트·원칙 |
|---|---|---|
| 1 | Today 메인 + MetricBreakdown 패널 | QuickInput, MetricCell, RecommendationCard, EvidenceQuote, MetricBreakdown / P1·P2·P5·P6 |
| 2 | Provider 비교 매트릭스 (3-G-1) | ProviderComparison, 동적 매트릭스(AO-2), is_primary 근거(AO-3) / P3 |
| 3 | Activity 상세 (3-C) | MetricCell 그리드, 환경 카드, QuickInput compact / P2·P3·P6 |
| 4 | Story 메인 (2-A) | TimelineNarrative, 재계산 마일스톤(AO-1) / P1·P5 |

각 목업은 **단일 HTML 파일**(인라인 CSS, 더미 데이터)로 만들어 브라우저에서
바로 열어 확인한다.

### Step 2 — 토큰 확정 → 08 문서 추출

목업 3~4개에서 `:root` 토큰이 안정되면 `08-design-system.md`로 추출.
포함: 색상(다크/라이트), 타이포 스케일, 간격, 반경, 시맨틱 5단계, provider 색.

### Step 3 — SvelteKit 이식 = Phase 7a 구현 착수

확정된 목업 마크업을 `.svelte` 컴포넌트의 출발점으로 사용.
`07-migration-roadmap.md`의 Phase 7a 순서(서비스 레이어 D5 → API → 프론트)와
연결. 목업 더미 데이터를 실제 API 응답으로 교체.

---

## 3. 목업 작성 규칙 (모든 에이전트 공통)

1. **토큰 SSOT**: 색·간격·폰트는 반드시 `:root` 변수 참조. 하드코딩 금지.
2. **데이터 형태 일치**: 더미 데이터의 구조를 `04-component-catalog.md`의
   props 인터페이스와 동일하게 맞춘다 (API 교체 시 마찰 최소화).
3. **디자인 언어**: P5 Quiet Data — 글래스모피즘·그라데이션·네온·장식 모션
   금지. 데이터가 전면, UI는 후면. 레퍼런스: Linear / Stripe / Vercel.
4. **다크 모드 기준**으로 먼저 만들고, 토큰으로 라이트 모드 파생.
5. **드릴다운 동선 필수**: MetricCell·차트는 클릭 시 MetricBreakdown 패널이
   열리는 동작을 목업에서도 (간단한 토글로) 보여준다 (P2 검증 목적).
6. **provider 버전 표기**: RunPulse 메트릭은 `[RunPulse · formula_v1]` 형태
   배지로 표시 (AO-1 검증).

---

## 4. 산출물 목록

| # | 파일 | 단계 |
|---|------|------|
| M1 | `mockups/today.html` | Step 1 |
| M2 | `mockups/providers.html` | Step 1 |
| M3 | `mockups/activity-detail.html` | Step 1 |
| M4 | `mockups/story.html` | Step 1 |
| D1 | `08-design-system.md` (+ `tokens.css`) | Step 2 |
| — | SvelteKit `frontend/` 초기화 + 컴포넌트 이식 | Step 3 |

---

## 5. 완료 기준 (이 단계의 DoD)

- [ ] 핵심 4개 화면 목업 완성, 브라우저에서 확인됨
- [ ] 8개 원칙이 목업에서 시각적으로 검증됨 (특히 P1·P2·P3·P5·P6)
- [ ] `:root` 토큰이 안정화되어 `08-design-system.md`로 추출됨
- [ ] 목업 더미 데이터 구조가 04 props 인터페이스와 일치
- [ ] 다음 단계(7a 구현) 진입 가능 상태

---

## 6. 의도적으로 지금 하지 않는 것

- Figma 등 별도 디자인 도구 (1인 개발 — 이중 작업 회피, 코드가 곧 산출물).
- 22개 화면 전부 목업 (핵심 4개로 방향 확정 후 나머지는 구현 중 처리).
- 실제 API·DB 연동 (목업은 더미 데이터, 연동은 7a에서).

---

## 작성 이력
- v0.1 (2026-06-10): 최초 작성. 목업 우선·토큰 후확정 방향, 작업 순서,
  목업 규칙, 산출물·DoD 정의.
