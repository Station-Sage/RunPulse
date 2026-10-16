# design-2026-10 — v2 점검 설계 묶음 (설계 완료, 구현 승인 대기)

> 상태(2026-10-12): 설계 단계 종료. 결정 `decisions-table.md`(총 373행, 미결정 2건 = TXT-1 문구·FRS-28). 코드 변경 없음. **구현은 사용자 승인 후 착수**(CLAUDE.md: plan 승인 후 진행).

## 1. 문서 색인
| 구분 | 문서 | ADR(구현 시 기록) |
|---|---|---|
| patterns | server-input-origin-validation(SRV) | 048 |
| patterns | security-headers(SEC) | 049 |
| patterns | data-freshness(FRS) | 050 |
| patterns | non-running-activities(NRA) | 051 |
| patterns | timezone-display(TZ), overlay-common-behavior(OVL), error-retry-common(ERR), accessibility-common·accessibility-layout(A11Y) | 번호는 구현 시 순차 배정(052~) |
| bundles | coach-plan-bundle(PLN), race-calendar(RC), adjustment-signals·adjustment-new-signals(ADJ·NEW), high-severity-remaining(HSR), data-export(EXP), v1-sunset-prep(V1·V1S) | 위와 동일 |

## 2. 스키마 순서 (현 SCHEMA_VERSION = 36 → 최종 40)
| 버전 | 내용 | 전제 |
|---|---|---|
| (사전) | 레거시 삭제 7종 — planner 행, 외부 계획 행, plan_adjustments, plan_replans, plan_progression, session_outcomes, goals(active·cancelled만; completed 유지) | **사용자가 v37 이전에 DB 에서 직접 실행**. session_outcomes·goals 는 건수 표시 후 재확인, plan_adjustments 는 source 별 분포 확인, `sqlite_sequence` 는 건드리지 않음, 반드시 백업 |
| v37 | plan_adjustments 재구축(source·signals_json·재분류, 자동 source 'auto' 표현식 유니크 인덱스) | 위 삭제 후 |
| v38 | race_calendar, context_episodes, illness_consent_events, cancel_prev_* 컬럼 | |
| v39 | goals.race_id 백필(completed 목표 → done A 대회 생성, 활성 목표 재사용 B/C 는 A 승격), 자동 DB 백업·단일 트랜잭션 — ✅ 구현(S4-16) | v38 |
| v40 | planned_workouts.goal_id + CHECK(source<>'planner' OR goal_id IS NOT NULL) + adj_accepted + user_training_prefs.workout_weekdays_mask — ✅ 구현(S4-17) | planner 행 0건(수동 삭제 누락 시 중단·롤백) |

## 3. 제안 구현 순서 (미승인 — 각 문서 '단계·검증' 참조)
0. **S0 점검**: 각 문서 말미 'S0 점검 목록'(SCAN_DIRS, 읽기 경로별 goal_id 필터 분류, 운영 SQLite 버전 등) 사실 확인
1. `crs.evaluate()` 복원 선행 커밋(ADJ-22, replanner 테스트 기대값 갱신)
2. v1 일몰 준비(v1-sunset-prep): 공용 파일 이관(`src/sync/`, `utils/user_context.py`, `src/mcp_remote/`, `routes_calendar_feed`), `/ai-coach` 라우트 등록 삭제(파일은 일몰 때), loader 제거
3. (0단계 환경: flask·gunicorn 은 `.venv`, 표준 테스트 명령·설치 문서 정정, ENV-1 승인 2026-10-13) SRV(048) → SEC(049): Origin 관문·입력 제한, uid 검증(`validate_uid`), 보안 헤더(CSP Report-Only 2주 후 enforce — 전환 전 의도적 위반 보고 도착 확인 필수)
4. FRS(050)·NRA(051)·TZ: 신선도·비러닝·시간대
5. 레거시 삭제(사전) → v37~v40 + PLN·RC·ADJ·NEW 구현(캘린더·조정 신호·플랜 생성 변경)
6. EXP·OVL·ERR·A11Y(레이아웃 포함, coach/+page 분리) 프런트 작업

## 4. 사용자 사전 작업
- 레거시 삭제 실행(위 §2) 및 백업
- Today 모바일 순서 변경(A11Y-L4: 다음 세션이 2번째)을 375px 스크린샷으로 확인
- enforce 전환 전 CSP 보고 도착 테스트(실환경)
- TXT-1 문구 확정(RC-18·EXP-7·NEW-15·17·19·25·35·PLN-14·sr-only h2 4개·skip link·crs_stale/missing 등)
- 아이콘 디자인은 별도 에이전트 활용(SEC-11)

## 5. 구현 착수 전에 정해야 할 정책 질문 (1~3 은 decisions-table 에서 이미 결정됨 — 2026-10-16 확인, 남은 것 4·5)
1. **결정됨(RC-28·36·37·41·42·46·47·53)** 창을 거쳐 연결되는 복원·되돌린 A 의 `adapt_choice`·`plan_state` 우선순위(§2.4 'A·adapt 고정·applied' vs RC-28·RC-37 값)와 RC-36 재반영을 재계획 `apply` 와 함께 실행할지
2. **결정됨(RC-29·47·53: 확인 문구 후 복원, 재반영은 지난 날짜 행 제외·0행은 adapt·stale 안내)** 지난 날짜 복원(done, RC-29)에서 창이 뜰 때 미리보기를 보일지/막을지
3. **결정됨(RC-27·51: cancelled 수정 가능, 후보는 복원 대상 하나로 한정)** cancelled A 를 B 로 내리는 수정 허용 여부('B 로 바꾼 뒤 다시 활성화' 안내의 전제)
4. `/api/v1/csp-report` 가 CF Access·사용자 식별에 막히면 우회 대상으로 둘지
5. Origin 관문 observe 의 '위반 0건' 집계에서 봇·스캐너 제외 방식

그 밖의 모호점은 각 문서 'S0 점검 목록'에서 구현 중 사실 확인으로 해소한다. 결정 번호 → 설계서 매핑은 `decisions-table.md`.
