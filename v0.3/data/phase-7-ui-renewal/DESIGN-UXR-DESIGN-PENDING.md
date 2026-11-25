# DESIGN-UXR-DESIGN-PENDING — Phase 3 보류 항목 현황 대조 (2026-11-25)

출처: `BACKLOG.md [P7-UXR-DESIGN-PENDING]`(190~220행), `ux-review-2026-09/DESIGN-PENDING-12.md`·`DESIGN-CLEANUP.md`·`DESIGN-S1S4-REMAIN.md`, `DESIGN-ALGO-VERSION-MARKER.md`.
방식: 읽기 전용 조사(코드 grep·파일 존재 확인). 코드·DB 변경 없음. 브라우저·DB 값 검증은 하지 않았다.

## 1. 결론

12개 항목 + 구조·정리 보류 3건 중 **사용자 결정이 실제로 남은 것은 1건**(① ai_context 미사용 3함수 삭제)뿐이다.
나머지는 BACKLOG 기록 시점 이후 구현·종료됐거나 결정이 불필요하다. 따라서 `P7-UXR-DESIGN-PENDING-IMPL`의 구현 대상 중
"◆ 마커·테이퍼 드릴·SWR"은 이미 소멸했고, 남은 것은 ①의 삭제 여부에 달려 있다 → `DECISIONS.md [P7-UXR-DESIGN-PENDING]` 참조.

## 2. 항목별 현황

| # | 항목 | 현황 | 근거 |
|---|------|------|------|
| 1 | UTRS 입력 드릴 | 완료(2026-10-04) | BACKLOG "진행" 문단 |
| 2 | RRI 등급 SSOT | 완료(2026-10-04) | 동 |
| 3 | 활동 `@a{id}` 드릴 | 완료(2026-10-04) | 동 |
| 4 | S1b 잔여 3건 | 종료(① TRIMPEst ADR-024, ② 기구현, ③ acwr 정본화) | BACKLOG 4번 |
| 5 | RPE·`⋯` 메뉴 | 기구현(U15, ADR-022) | BACKLOG 5번 |
| 6 | 3-16(D4) 스냅샷 | 불필요 종료(사용자 결정 2026-10-10) | BACKLOG 6번 |
| 7 | 캐시 워밍 | 기구현(U17d/e/f) | BACKLOG 7번 |
| 8 | 달성 가능성·`x.taper` | 기구현. `frontend/src/lib/components/drill/TaperSheet.svelte` 존재 확인 | BACKLOG 8번 |
| 9 | 이벤트 마커(▲·◆)·Sparkline | 구현. `src/metrics/algo_changelog.py`(CHANGELOG)·`src/services/metrics_changelog_events.py`(상위 지표 전파 `via` 포함)·`metrics_trend_service.py:14` 사용 확인 | `DESIGN-ALGO-VERSION-MARKER.md` D-1·D-2의 추천 방향이 구현에 반영돼 있으나 사용자 승인 기록은 찾지 못함 — TODO: 확인 필요 |
| 10 | 계정 설정 스키마 | 기구현(U15, v25) | BACKLOG 10번 |
| 11 | 스트림 다운샘플·SWR | 완료. `frontend/src/lib/loadCache.ts`(`swrLoad`) 존재, 다운샘플은 사용자 "설계 방식대로 해"로 진행 | `IMPL-PROGRESS.md` 2-6 5차 |
| 12 | 활동 목록 기간 필터 | 완료(2026-10-04) | BACKLOG "진행" 문단 |

## 3. 남은 결정: ① `ai_context.py` 미사용 3함수

- 대상: `src/ai/ai_context.py`의 `build_daily_briefing`(31행)·`build_activity_analysis`(115행)·`build_ai_context`(176행). 약 186줄.
- 운영 호출처 없음(grep: `src/` 내 호출은 3함수끼리뿐, `briefing.py`는 레거시 경로 `build_context` 등만 사용). 참조처는 `tests/test_ai_context.py`와 `scripts/check_docs.py:872`(검사 19, `build_ai_context` 문자열 존재 확인)뿐.
- 레거시 dict 경로는 이미 `ai_context_legacy.py`로 분리·재노출됨(DESIGN-CLEANUP §2 A안 적용).
- 삭제 시 영향: ① 함수 3개 삭제 ② `tests/test_ai_context.py`의 해당 테스트 삭제 ③ `check_docs.py` 검사 19 대상 교체(예: `build_context`) ④ `v0.3/data/phase-5.md`·`phase-5-impl/02-ai-context.md`·`04-tests.md` 정정, `files_index.md`는 `gen_files_index.py`로 재생성.
- 보존 시: docstring의 "Q1: 삭제 여부는 BACKLOG 판단 대기" 문구만 정리하면 끝. 위험 없음.
- BACKLOG가 "(사용자 결정)"으로 보류한 항목이고 코드·테스트·문서를 지우는 변경이라 임의 결정하지 않는다.

## 4. 보류 ②: `HIGHER_IS_BETTER` 위치·`template_helpers.py` 28키 사본

결정 불필요. 현 위치 유지, Jinja 폐기 시 정리(BACKLOG 기록 그대로). 추가 설계 없음.

## 5. IMPL 단위 영향

`[P7-UXR-DESIGN-PENDING-IMPL]`은 ①의 결정에 따라 (a) 삭제 구현(위 ①~④) 또는 (b) 문구 정리만으로 축소된다. 결정 전에는 착수하지 않는다.
