# 다음 세션 시작 프롬프트 (복사해서 새 세션 첫 메시지로 사용)

> 갱신: 2026-10-14, S3 완료 시점. 이전 버전(구현 착수 전)은 git 이력 참조.

```
RunPulse v2 점검(2026-10) 구현을 이어서 진행한다. 브랜치 ccr-8ec9b1bc-q2i3u3, 작업 디렉터리 /home/user/webapp. S0~S3 구현·로컬 검증·push 가 끝났고 S3 결과 보고 후 내 확인을 기다리는 상태다.

[먼저 읽을 것 — 이 순서로, 필요한 부분만]
1. CLAUDE.md 와 .claude/rules/ (파일 300줄 이하, 함수마다 테스트 1개 이상, Calculator raw SQL 금지, conventional commits)
2. BACKLOG.md 의 [V2-IMPL] 항목 (현재 상태 요약)
3. v0.3/data/phase-7-ui-renewal/design-2026-10/S3_results.md — 단계·커밋, 위험(R1~R13), 운영 인계(§6), 열린 항목(§7), 다음 단계(§8)
4. design-2026-10/README.md — 스키마 v37~v40 순서, 제안 구현 순서, 사용자 사전 작업, 정책 질문 5건
5. decisions-table.md 는 필요한 행만 grep (373행: 결정 367 / 부분 4 / 미결정 2 = TXT-1 문구, FRS-28). S3-3~S3-11 이 '사용자 확인 필요' 행이다.

[현재 상태]
- 완료: S0(점검) S1(crs.evaluate 복원) S2(v1 일몰 준비) S3(SRV ADR-048 + SEC ADR-049 + v1 sync/import 라우트 Blueprint 이동). S3 커밋 7082428..(11단계 커밋), 모두 origin 에 push 됨. PR 은 만들지 않았다(내가 요청할 때만).
- 테스트 기준선: .venv/bin/python -m pytest tests/ -q -p no:cacheprovider → 3255 passed, 240 skipped. 프런트: cd frontend && npm run test:unit (479), npm run check (에러 0), npm run build. check_docs: 오류 0 / 경고 64. SCHEMA_VERSION 은 아직 36.
- 시스템 python3 에는 flask 가 없다 — 반드시 .venv/bin/python 사용. 테스트가 data/users 에 디렉터리를 만들면 안 된다(실행 전후 ls data/users 비교). 쓰기 요청을 보내는 테스트는 Origin: http://localhost 헤더가 필요하다(conftest 가 Origin 관문을 enforce 로 돌림).
- 내 확인 대기: S3-3~S3-11(에이전트가 정한 구현 세부), V1-8 해석(GET /api/v1/dev/users + POST /api/v1/dev/switch-user + MenuDrawer 다이얼로그). 임시 아이콘·알림 문구·'CSV 내보내기' 라벨은 TXT-1 과 함께 확정.
- 열린 항목: R1 백필 결정, TXT-1 문구, FRS-28, TEST-PLAN-CREATION-DATE(간헐 실패), README §5 정책 질문(1~3 은 S4 이후 해당 단계 전에, 4·5 는 운영 관찰 시).
- 운영 인계(내가 운영에서 할 일, 에이전트는 접근 불가): check_user_dirs.py 실행, PUBLIC_BASE_URL·APP_ENV 등 환경변수, Origin observe 2주 → ORIGIN_GUARD_MODE=enforce, CSP Report-Only 2주 + 의도적 위반 보고 도착 확인(CF Access 경유) → CSP_V2_MODE=enforce, 최종 아이콘 제공. 결과를 알려주면 S3_results.md §6 에 반영한다.

[이번 세션에서 할 일]
A. 먼저 S3 에서 내 확인이 필요한 항목(위 '내 확인 대기')을 정리해 AskUserQuestion 카드(질문당 선택지+추천+장단점, 한 번에 4개 이하)로 묻고, 답을 decisions-table.md 에 반영한다. 내가 이미 정한 것(Q1~Q5 정책, V1S-12 b안)은 다시 묻지 않는다.
B. 내가 'S4 진행'을 승인하기 전에는 코드를 수정하지 않는다. 승인되면 S4(FRS 신선도 ADR-050 · NRA 비러닝 ADR-051 · TZ 시간대)의 구체 계획(단계, 단계별 변경 파일, 테스트, 롤백, 내가 해야 할 사전 작업)을 설계서 patterns/·bundles/ 의 '변경 파일 표'와 '단계·검증'으로 작성해 승인을 요청한다. 계획에는 S0 점검 목록(사실 확인 항목)도 포함한다.
C. 레거시 삭제 7종(planner 행 등)과 v37 이후 스키마 작업은 S4 범위가 아니다. 내가 DB 에서 직접 삭제하기 전에는 시작하지 않는다.

[작업 규칙]
- 단계마다: 계획 → 내 승인 → 구현 → 결과 보고 → 내 확인. 승인 안 된 단계는 시작하지 않는다. 단계마다 push 한다("단계별로 push 할 것"). PR 은 요청 시에만.
- 정책·기본값·문구·삭제/보존 결정은 네가 정하지 말고 선택지·장단점으로 묻는다. 구현 중 설계에 없는 세부를 네가 정했다면 decisions-table.md 에 'S3-n 식 행(사용자 확인 필요)'으로 기록한다.
- 운영 DB·외부 서비스에는 접근하지 않는다. 레거시 삭제(S5 등)는 내 명시적 허가 + 대상 건수 + 백업 확인 후에만.
- 커밋은 작업 단위로, git add 는 파일을 명시해서(git add -A 금지). 커밋 메시지 끝에 트레일러:
  Co-Authored-By: Claude Code <noreply@anthropic.com>
- 푸시: setup_github_environment 로 인증 후 GIT_TERMINAL_PROMPT=0 git push origin ccr-8ec9b1bc-q2i3u3, 이후 git rev-parse HEAD origin/ccr-8ec9b1bc-q2i3u3 로 일치 확인. 실패 시 원인만 보고(인증 재설정은 내가 한다).
- 문서 변경 후 python3 scripts/gen_files_index.py → python3 scripts/check_docs.py. 코드 변경 후 전체 pytest(.venv) + 프런트 check/test:unit/build.
- 보고는 핵심만 한국어로 간결하게. 확인하지 못한 것은 '미확인'으로 표시. 결정·미결정·연기·인계는 문서에 기록한다.

[알아 둘 함정]
- 에이전트 보고가 코드와 어긋난 적이 있다. 구현 전 핵심 사실은 grep 으로 직접 확인한다(예: matcher 는 날짜별 리스트 acts_by_date 를 쓴다).
- decisions-table.md 헤더 집계의 '부분 결정' 표기 일부(TZ-3, TZ-6 등)는 후속 결정으로 해소된 것이 있다. 집계를 믿기 전에 행 본문을 확인한다.
- strava_csv.py:384-387 이 CSV 재가져오기 때 start_time 을 덮어쓴다(활동 1327 정정은 수동 SQL).
- csp-report 는 CF Access·사용자 식별을 거치므로 enforce 전환 전 의도적 위반으로 보고 도착을 실환경에서 확인해야 한다.
- Origin 관문·CSP 는 기본이 observe/Report-Only 다. 코드 기본값을 enforce 로 바꾸는 것은 운영 관찰 결과를 받은 뒤 내가 결정한다.
- 프런트 테스트에서 소스 파일 문자열을 assert 하는 경우, 주석에 같은 문자열을 쓰면 실패한다(S3 10단계에서 겪음).
- 브라우저 실동작(DevUserSwitch, UpdateNotice, 아이콘/manifest, CSP 위반)은 이 샌드박스에서 확인하지 못했다 — 관련 주장은 '미확인'으로 유지한다.
```
