# V2-REPAIR B — 내비 규칙·CTA 표 (B1/B2)

근거: `REVIEW-10-v2-completeness-audit.md` §2(B-1~B-7), §6. 결정 ③ = a (2026-11-18).

## 결정
- 하단 탭 3개(Today/Library/Coach) 유지. Plan 은 Coach 하위 탭(`대화` `/coach`, `플랜` `/coach/plan`). Data 는 드로어 유지.
- Coach 하위 탭은 `/coach`, `/coach/plan`, `/coach/plan/{id}` 에서만 표시. 그 밖(새 플랜·세션 상세·스레드)은 하위 탭 없이 `‹` 뒤로가기.

## 뒤로가기 규칙 (`frontend/src/lib/backNav.ts`)
1. 헤더 `‹` 는 유효한 내부 `?from=` 경로가 있으면 그곳으로, 없으면 부모 경로(`parentPath`)로 이동.
2. 외부 URL, `//` 로 시작하는 값, 내부 경로가 아닌 값은 무시(`safeInternalPath`).
3. 직접 진입·새로고침은 부모 경로로 폴백.
4. 글리프는 `‹` 하나(`BACK_GLYPH`). `←` 사용 금지.
5. 화면 이동 시 `withFrom(path, current)` 로 출처를 실어 보낸다.
6. 기존 태그 기반 `activityHeader.backTarget(from)` 은 활동 상세 계열에서 병존(건드리지 않음).

## CTA 표 (`frontend/src/lib/ctaRoutes.ts`)
| 의미 | 경로 | 비고 |
|------|------|------|
| 소스 연결 | `/data/sources` | Library 빈 상태가 기존 `/data/settings` 로 가던 것 수정 |
| 플랜 홈 | `/coach/plan` | 활성 플랜 있으면 `/coach/plan/{goalId}` 로 302 |
| 새 플랜 | `/coach/plan/new` | |
| 플랜 상세 | `/coach/plan/{goalId}` | |
| 세션 상세 | `/coach/plan/{goalId}/session/{date}` | goalId·date 없으면 플랜 홈 |

## 남은 범위
- B3 온보딩 `return_to`(Step1·Step3·Step4·welcome).
- B4 화면별 적용: 빈/오류 상태를 `EmptyState`/`ErrorState` 로 통일, 체크인 입력은 Today 로 일원화(Coach 홈은 요약+링크, B4)·"코치에게 묻기" 중복 제거, V2-AUDIT-INDIV 흡수.
- replan 은 PageHeader 적용(B4). 미적용: compare(‹ 새 프로그램 링크 유지), `library/[id]` 레이아웃(태그 로직 유지).
