# Phase 7 UI Renewal — 화면 카탈로그

**문서 상태**: Draft v0.3  
**작성일**: 2026-06-10  
**전제 문서**: `01-design-principles.md`, `02-information-architecture.md`  
**후속 문서**: `04-component-catalog.md`

---

## 이 문서의 목적

6개 영역의 핵심 화면을 텍스트 와이어프레임으로 정의한다.  
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
| [03a-today.md](03a-today.md) | 1. TODAY | Today 메인(1-A), 활동 상세(1-B) |
| [03b-story.md](03b-story.md) | 2. STORY | Story 메인(2-A), 마일스톤(2-B), 주간 리뷰(2-C) |
| [03c-library.md](03c-library.md) | 3. LIBRARY | Library 홈(3-A), 메트릭 드릴다운(3-B~D), Provider 비교(3-E~G), 활동 피드(3-H~I) |
| [03d-plan.md](03d-plan.md) | 4. PLAN | Plan 홈(4-A~B), 주 단위 뷰(4-C), 편집(4-D) |
| [03e-coach.md](03e-coach.md) | 5. COACH | Coach 홈(5-A), 피드백 상세(5-B), 목표 설정(5-C) |
| [03f-data.md](03f-data.md) | 6. DATA | Data 홈(6-A), 연동 관리(6-B), 프로파일(6-C) |
| [03g-common-patterns.md](03g-common-patterns.md) | 7. 공통 패턴 | 드릴다운 레벨, Provider 배지, EvidenceQuote 칩, 상태 기반 배지 |

---

## 작성 이력

- v0.3 (2026-06-10): REVIEW-02 반영 — AO-1: Story 마일스톤 metric_recompute 이벤트 예시 추가; AO-2: 3-G-1 매트릭스 세로축 동적 렌더링 명시(그룹별 실제 연결 provider 기준); AO-3: 3-G-1 셀 팝업 우선순위 근거 coverage → dedup.py 정적 순서로 정정
- v0.2 (2026-06-10): REVIEW 반영 — G2: 3-G Provider 비교 13×4 매트릭스 + 셀 인터랙션 구체화, G4: 활동 상세 환경 컨텍스트 카드 추가, G5: QuickInput 전 영역 배치 원칙(7-5) + 3-C·5-A compact 슬롯 추가
- v0.1 (2026-06-10): 초안 — 6개 영역 22개 화면 와이어프레임, 공통 패턴 4개
