# Phase 7 UI Renewal — BACKLOG

## 진행 현황

**현재 상태**: 설계 문서 8개 완료 (00~07). 구현 단계 준비 — Phase 7a부터 시작.

---

## 결정 완료 사항 (`00` 문서)

| 분기점 | 결정 내용 |
|--------|-----------|
| **A. IA** | 사용자 의도 중심 5+1 영역 — Today / Story / Library / Plan / Coach + Data |
| **B. 기술 스택** | SvelteKit + Tailwind CSS + Flask API (JSON only) + 단일 프로세스 배포 |
| **C. 디자인** | Quiet Data 미니멀리즘 + Story 영역 에디토리얼 / 글래스모피즘 폐기 |
| **D. 마이그레이션** | `/v2/` 단계별 구축 → 완성 후 디폴트 스위치 (Phase 7a→7d 4단계) |

### 설계 원칙 8개 (확정)
1. Evidence-First
2. Drillable Everything
3. Provider Transparency
4. Intent-Centered IA
5. Quiet Data
6. One Finger Reach for Input
7. State-Bound Plan
8. Local-First Identity

### 핵심 컴포넌트 1차 목록 (확정)
`<EvidenceQuote>` / `<MetricCell>` / `<MetricBreakdown>` / `<ProviderComparison>` / `<QuickInput>` / `<RecommendationCard>` / `<TimelineNarrative>`

### 데이터 레이어 확장 5건 (미구현)
| ID | 내용 | 단계 |
|----|------|------|
| D1 | 합성 메트릭 `json_value` 분해 스키마 표준화 | Phase 7a |
| D2 | 활동 그룹 ID 모델 명시화 (그룹 마스터 테이블) | Phase 7b |
| D3 | `user_inputs` / `ai_feedback` 테이블 신설 | Phase 7a |
| D4 | `athlete_profile_snapshots` 테이블 신설 | Phase 7c |
| D5 | `src/services/` 서비스 레이어 신설 | Phase 7a (전제조건) |

---

## NOW

(비어있음 — 설계 문서 완료. 구현 시작 시 NEXT에서 승격)

---

## NEXT

- **[P7-IMPL-D5]** `src/services/` 서비스 레이어 구현 (Phase 7a 전제조건 — D5)
- **[P7-IMPL-D3]** `user_inputs` / `ai_feedback` DDL + `db_setup.migrate()` 등록 (Phase 7a)
- **[P7-IMPL-API]** Flask `/api/v1/` 블루프린트 + Today/Library/activities 엔드포인트 (Phase 7a)

---

## LATER

- **[P7-IMPL-D1]** parent_metric_id 활성화 — fitness/utrs/cirs Calculator 수정 (Phase 7a)
- **[P7-IMPL-SVELTE]** SvelteKit 프로젝트 초기화 + 공통 컴포넌트 7개 구현 (Phase 7a)

---

## DONE

- **[P7-07]** `07-migration-roadmap.md` v0.1 완료 — Phase 7a~7d 4단계 로드맵, 단계별 산출물·검증 기준·전환 조건, 롤백 전략, 기능 동등성 체크리스트, 위험 요소 5건
- **[P7-06]** `06-data-layer-extensions.md` v0.1 완료 — D1~D5 ADR 5건, DDL (user_inputs/ai_feedback/activity_groups/athlete_profile_snapshots), Calculator 수정 범위(4개), 마이그레이션 실행 순서, 영향 파일 목록, 테스트 요건
- **[P7-05]** `05-tech-architecture.md` v0.1 완료 — SvelteKit adapter-static + Flask 단일 프로세스, `/api/v1/` 엔드포인트 전체 목록, 빌드·배포 전략, PWA Cache-First 전략, 베타 토글 구현, ADR 6개, 구현 전제조건 체크리스트
- **[P7-04]** `04-component-catalog.md` v0.1 완료 — 7개 컴포넌트 props 인터페이스(TypeScript), 상태 테이블, 레이아웃 와이어프레임, 인터랙션 패턴, 공유 디자인 토큰(색상·타이포·간격), 접근성 원칙
- **[P7-03]** `03-screen-catalog.md` v0.1 완료 — 6개 영역 22개 화면 텍스트 와이어프레임, 공통 패턴 4개 (드릴다운 레벨, Provider 배지, EvidenceQuote 칩, 상태 기반 배지)
- **[P7-02]** `02-information-architecture.md` v0.1 완료 — 전체 라우트 트리, URL 스키마 규칙, 구↔신 URL 리다이렉트 매핑, 네비게이션 구조(데스크탑/모바일), 영역별 진입 흐름 5개, 영역 간 컨텍스트 유지 패턴, 딥링크, 마이그레이션 단계
- **[P7-01]** `01-design-principles.md` v0.1 완료 — 원칙 8개 상세 정의(적용/위반/준수 예시 포함), 우선순위, 충돌 해결 예시, 설계 완료 체크리스트
- **[P7-00]** `00-diagnostic-and-direction.md` v0.2 완료 — 현 UI 진단(3/10), 데이터 레이어 적합도(8.5/10), 분기점 A/B/C/D 확정, KPI 매핑 8개
