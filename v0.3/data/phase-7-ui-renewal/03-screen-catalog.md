# Phase 7 UI Renewal — 화면 카탈로그

**문서 상태**: Draft v0.4 — REVIEW-03(하단 3탭 IA) 반영  
**작성일**: 2026-06-10 (v0.1) / 2026-09-22 (v0.4 재정렬)  
**전제 문서**: `01-design-principles.md`, `02-information-architecture.md`,
`00-diagnostic-and-direction.md` §5.1  
**후속 문서**: `04-component-catalog.md`

---

## 이 문서의 목적

하단 3탭(Today/Library/Coach) + 상단 ☰ 메뉴(Data)의 핵심 화면을 텍스트 와이어프레임으로
정의한다. 구 Story·Plan은 독립 영역이 아니라 Today(L2)·Coach로 흡수됐다 — 해당 파일은
안내 스텁으로 남아있다(아래 표 참조).  
시각 디자인(색상·폰트·여백 수치)은 다루지 않는다. 구조·계층·컴포넌트 배치에 집중한다.

**범례**
```
[ ]  버튼 또는 인터랙티브 요소
< >  컴포넌트 참조 (04-component-catalog.md)
→    탭/클릭 시 이동 대상
↕    확장/축소 가능
★    P1~P8 설계 원칙 적용 지점
```

---

## 영역별 파일 목록

| 파일 | 영역 | 주요 화면 |
|------|------|----------|
| [03a-today.md](03a-today.md) | 1. TODAY (하단 탭) | L0 즉시 브리핑, L1 내 상태(1-A), L2 흐름·훈련·성장(1-A, 구 Story·Plan"보기" 흡수), L3 드릴다운(1-B~D) |
| [03b-story.md](03b-story.md) | ~~2. STORY~~ **흡수됨 → 03a** | 안내 스텁 — 구 2-A/2-B는 `03a-today.md`의 L2로 흡수 |
| [03c-library.md](03c-library.md) | 3. LIBRARY (하단 탭) | Library 홈(3-A), 메트릭 드릴다운(3-B~D), Provider 비교(3-E~G) |
| [03d-plan.md](03d-plan.md) | ~~4. PLAN~~ **분할 흡수됨** | 안내 스텁 — "보기"는 `03a-today.md` L2, "작업"은 `03e-coach.md` 5-C~5-G |
| [03e-coach.md](03e-coach.md) | 5. COACH (하단 탭) | Coach 홈(5-A), 대화 스레드(5-B), 플랜 작업 흐름(5-C~5-G, 구 Plan "작업" 흡수) |
| [03f-data.md](03f-data.md) | 6. DATA (상단 ☰ 메뉴) | Data 홈(6-A), 동기화 상태(6-B) |
| [03g-common-patterns.md](03g-common-patterns.md) | 7. 공통 패턴 | 드릴다운 D1~D3(구 L1~L3, Today L0~L3과 명칭 충돌 회피), Provider 배지, EvidenceQuote 칩, 상태 기반 배지 |

---

## 작성 이력

- v0.4 (2026-09-22): REVIEW-03(하단 3탭 IA) 반영 재정렬 — Story는 Today L2로, Plan은
  Today L2(보기)·Coach(작업)로 분할 흡수. `03b-story.md`·`03d-plan.md`는 안내 스텁으로 대체.
  `03g`의 드릴다운 레벨 표기를 L1~L3 → D1~D3으로 변경(Today 관여 계층 L0~L3과 명칭 충돌
  해소). 상세 판단 근거는 `00-diagnostic-and-direction.md` §4.1, `07-migration-roadmap.md`.
- v0.3 (2026-06-10): REVIEW-02 반영 — AO-1: Story 마일스톤 metric_recompute 이벤트 예시 추가; AO-2: 3-G-1 매트릭스 세로축 동적 렌더링 명시(그룹별 실제 연결 provider 기준); AO-3: 3-G-1 셀 팝업 우선순위 근거 coverage → dedup.py 정적 순서로 정정
- v0.2 (2026-06-10): REVIEW 반영 — G2: 3-G Provider 비교 13×4 매트릭스 + 셀 인터랙션 구체화, G4: 활동 상세 환경 컨텍스트 카드 추가, G5: QuickInput 전 영역 배치 원칙(7-5) + 3-C·5-A compact 슬롯 추가
- v0.1 (2026-06-10): 초안 — 6개 영역 22개 화면 와이어프레임, 공통 패턴 4개
