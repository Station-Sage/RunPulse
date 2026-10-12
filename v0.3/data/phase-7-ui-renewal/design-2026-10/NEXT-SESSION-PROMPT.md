# 다음 세션 시작 프롬프트 (복사해서 새 세션 첫 메시지로 사용)

```
RunPulse v2 점검(2026-10) 설계가 끝났고 구현 착수 직전이다. 브랜치 ccr-8ec9b1bc-q2i3u3 에서 이어서 진행한다(PR 은 내가 요청할 때만 만든다).

[먼저 읽을 것 — 이 순서로, 필요한 부분만]
1. CLAUDE.md 와 .claude/rules/ (파일 300줄 이하, 함수마다 테스트 1개 이상, Calculator raw SQL 금지, 커밋은 conventional commits + 아래 트레일러)
2. BACKLOG.md 의 NOW/BUGS (V2-AUDIT 항목에 '설계 완료' 표시가 있음)
3. v0.3/data/phase-7-ui-renewal/design-2026-10/README.md — 문서 색인, 스키마 v37~v40 순서, 제안 구현 순서, 사용자 사전 작업, 구현 전 정책 질문 5건
4. 작업 대상 설계서의 '변경 파일 표'와 '단계·검증'(patterns/·bundles/). 결정 번호의 근거는 decisions-table.md 의 해당 행만 grep (354행, 미결정은 TXT-1 문구 1건)

[현재 상태]
- 설계서 15개 + 결정표 완료, 코드 변경 없음, 운영 DB 접근 없음. SCHEMA_VERSION 은 아직 36.
- 핵심 확정: 레거시 삭제 7종(planner 행, 외부 계획 행, plan_adjustments, plan_replans, plan_progression, session_outcomes, goals[active·cancelled만, completed 유지])은 내가 v37 이전에 DB 에서 직접 실행. planned_workouts.goal_id 는 planner 행 한정 CHECK(v40). v37 조정 신호 재구축, v38 race_calendar·context_episodes·illness_consent_events, v39 goals.race_id 백필, v40 goal_id+CHECK. v1 은 UI·라우트만 일몰(공용 파일은 src/sync/, utils/user_context.py, src/mcp_remote/ 등으로 이관, shim 없음). ADR 번호 048 SRV, 049 SEC, 050 FRS, 051 NRA, 이후 순차(구현 시 v0.3/data/decisions.md 에 기록).

[이번 세션에서 할 일]
A. 내가 승인하기 전에는 코드를 수정하지 않는다. 먼저 README 의 제안 구현 순서를 바탕으로 구체적인 구현 계획(단계, 단계별 변경 파일, 테스트, 롤백, 내가 해야 할 사전 작업)을 제시하고 승인을 요청한다.
B. 계획 승인 전에, README §5 정책 질문 5건을 AskUserQuestion 카드(질문당 선택지+추천+장단점, 한 번에 4개 이하)로 나에게 묻는다.
C. 승인 후 S0 점검(각 설계서 말미 'S0 점검 목록': SCAN_DIRS, 읽기 경로별 goal_id 필터 분류, 운영 SQLite 버전 등)부터 사실 확인하고, crs.evaluate() 복원 선행 커밋(ADJ-22)으로 시작한다.

[작업 규칙]
- 정책·기본값·문구·삭제/보존 결정은 네가 정하지 말고 선택지·장단점으로 나에게 묻는다. 문구는 TXT-1 로 내가 확정.
- 운영 DB·외부 서비스에는 접근하지 않는다. 레거시 삭제는 내가 실행하며, 삭제 전 대상 건수·백업 확인 절차를 문서대로 따른다(session_outcomes·goals 는 건수 표시 후 재확인).
- 문서/설계 변경을 하는 서브에이전트는 병렬로 돌리지 말고 한 번에 하나씩 순차로 돌린다(읽기 전용 조사만 병렬 허용). 모델은 opus.
- 서브에이전트에 system-architect·product-architect 타입은 Edit/Write 가 없으니 편집이 필요하면 general-purpose 를 쓴다.
- 서브에이전트가 만든 새 열린 질문은 결정표에 등록하고 카드로 묻되, 구현 중 사실 확인으로 풀리는 것은 S0 점검 목록으로 처리한다. 같은 문서를 반복 동기화하는 순환을 만들지 않는다.
- 변경 후 python3 scripts/check_docs.py, python3 -m pytest tests/, (프런트) npm run check·test:unit 으로 검증하고, 커밋/푸시는 작업 단위로 한다. 훅이 미커밋 파일을 지적하므로 에이전트가 편집 중인 파일은 끝난 뒤 커밋한다.
- 커밋 메시지 끝에 다음 두 줄을 붙인다:
  Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
  Claude-Session: https://claude.ai/code/session_01VeBbPXn2Zn4qv9iN1xegmU
- 보고는 핵심만 한국어로 간결하게. 확인하지 못한 것은 '미확인'으로 표시한다.

[알아 둘 함정]
- 에이전트 보고가 코드와 어긋난 적이 있다(예: matcher 는 날짜별 리스트 acts_by_date 를 쓴다). 구현 전 핵심 사실은 grep 으로 직접 확인한다.
- csp-report 는 CF Access·사용자 식별을 거치므로 enforce 전환 전 의도적 위반으로 보고 도착을 실환경에서 확인해야 한다.
- strava_csv.py:384-387 이 CSV 재가져오기 때 start_time 을 덮어쓴다(활동 1327 정정은 수동 SQL).
- decisions-table.md 의 '부분 결정' 표기 일부(TZ-3, TZ-6 등)는 실제로는 후속 결정으로 해소된 것이 있다. 헤더 집계를 믿기 전에 행 본문을 확인한다.
```
