# 클라우드 세션 인수인계 (Claude Code on the web)

로컬 작업을 클라우드에서 이어가기 위한 절차와 프롬프트. 작성 2026-09-26.

## 범위
- **클라우드에서 한다**: BACKLOG의 큐(`stage: queued`, `mode: auto`)에 등록된 `P7-PRED-*` 유닛 구현 — 명세가 코드 블록 수준이고 실 DB 없이 verify가 돈다.
- **로컬에서만 한다**: 실 DB 작업(백필 런북 P7-PRED-61, 재추출·재계산), 실 계정 화면 검증(브라우저 스모크), 동기화(Garmin/Strava/Intervals — 자격증명), 병합 리뷰의 실데이터 확인. 클라우드에는 `data/`·`config.json`·`.mcp.json`을 두지 않는다.

## 시작
1. GitHub 푸시 상태 확인: 브랜치 `renew/data-architecture`(원격 최신). 클라우드는 푸시된 커밋만 본다.
2. claude.ai/code → 저장소 `Station-Sage/RunPulse` 연결 → 기준 브랜치 `renew/data-architecture` 선택.
3. 환경 설정 스크립트에 `bash scripts/cloud_setup.sh` (Python 3.12, Node 24 권장).
4. 아래 프롬프트로 세션 시작. 터미널에서는 `claude --remote "<프롬프트>"`.
5. 결과는 PR로 받는다(병합은 로컬 리뷰 후). 로컬로 가져올 때 `claude --teleport`.

## 프롬프트

```
RunPulse 예측 리뉴얼 r4 유닛을 구현한다. 저장소 규칙(CLAUDE.md, .claude/rules)을 따른다.

먼저 읽을 것(이 순서):
1. v0.3/data/phase-7-ui-renewal/HANDOFF-2026-09-25.md (r4 후보 설계 상태 절)
2. v0.3/data/phase-7-ui-renewal/specs/PRED-00-INDEX.md (유닛 순서·의존·검증 상태)
3. v0.3/data/phase-7-ui-renewal/BACKLOG.md 의 AUTOPILOT QUEUE 에서 stage=queued 인 P7-PRED-* 유닛

작업 방식:
- 새 브랜치 cloud/pred-r4 를 renew/data-architecture 에서 만든다. main·renew/data-architecture 에 직접 커밋하지 않는다.
- 큐의 P7-PRED 유닛을 파일 순서대로 하나씩 구현한다. 각 유닛의 명세는 specs/PRED-*.md 의 해당 절이 유일한 명세이며, 코드 블록·diff 를 그대로 적용한다(임의 개선 금지).
- 유닛마다: 명세 적용 → 해당 유닛의 verify 명령(BACKLOG 메타의 verify) 통과 → python3 scripts/gen_files_index.py → 커밋(conventional commits, 한 유닛 한 커밋, 한국어 메시지 허용, 끝에 'Co-Authored-By: Claude <noreply@anthropic.com>') → BACKLOG 해당 항목 stage 를 review 로 바꾸고 명세 대조 결과 한 줄 기록.
- 명세 코드가 틀렸거나 적용이 안 되면 임의로 고치지 말고 이탈 내용을 BACKLOG 항목에 적은 뒤 그 유닛에서 멈추고 보고한다.
- 5개 유닛마다 전체 검증: python3 -m pytest tests/ -q, python3 scripts/check_docs.py, python3 scripts/check_data_consistency.py. 실 DB 없는 환경이라 tests/test_integration_realdb.py 는 skip 되는 것이 정상이고, tests/test_autopilot_run_unit.py::TestPostVerify 3건은 autopilot 워크트리가 없어서 실패하는 알려진 환경 한정 실패다(다른 실패는 조사).
- P7-PRED-72(레이스 허브 UI)는 마지막에 한다. 시작 전에 cd frontend && npm run check 로 svelte-check 오류가 있으면 원인을 먼저 보고한다(이전에 오류 1건이 미확인). 통과 후 npm run test:unit, npm run build.
- 실 DB(data/users/*/running.db), config.json, .mcp.json, 자격증명은 만들거나 커밋하지 않는다. data/users/default 는 만들지 않는다. 동기화·재계산·reprocess_all·recompute-all 은 실행하지 않는다.
- BACKLOG 의 큐 항목 외 작업, LATER.md 참조, 설계 변경은 하지 않는다. 설계 변경이 필요해 보이면 멈추고 보고한다.

끝나면 PR 을 만든다. 본문에는 유닛별 상태(명세 대조 이탈 여부, verify 결과), 전체 pytest 결과, 미확인 항목(특히 실 DB·브라우저 스모크가 필요한 것)을 적는다. 병합은 하지 않는다.
```

## 알아둘 점
- 클라우드는 별도 VM이라 로컬 대화·`/tmp`·메모리(`~/.claude/...`)가 넘어가지 않는다. 재개에 필요한 내용은 HANDOFF·INDEX 문서에 있다.
- `.claude/agents/`(running-data-coach 등)와 CLAUDE.md 는 저장소에 있어 클라우드에도 적용된다.
- 유닛은 같은 파일(`engine.py`, `db_setup.py` 등)을 순서대로 누적 편집한다. 한 세션에서 순서대로 진행하고 병렬 세션으로 나누지 않는다.
- 오토파일럿 러너(로컬 워크트리·ledger)는 클라우드에서 쓰지 않는다. 클라우드 세션이 직접 구현한다.
- 로컬 복귀 후 리뷰 규율(`scripts/autopilot/REVIEW.md`): 명세 대조, pytest·check_docs, 실데이터 사본에서 브라우저 스모크(UI 유닛), 이탈은 main 에서 교정·기록.
- 로컬 오토파일럿 큐와 중복 실행하지 않는다. 클라우드로 넘긴 유닛은 로컬에서 체인을 돌리지 않는다.
