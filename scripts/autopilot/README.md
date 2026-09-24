# autopilot — Phase 7 설계·구현 작업 자율 실행 러너

`v0.3/data/phase-7-ui-renewal/BACKLOG.md`의 `mode:"auto"` 항목을 골라 `claude -p`로
1건씩 실행하고, 격리된 worktree(`autopilot/phase7` 브랜치)에 커밋한다. **자동 병합은
하지 않는다** — 완료된 항목은 `stage: review`로 남고, 병합은 사람이 한다.

> 유닛 병합 전 리뷰 절차·환경 함정은 [REVIEW.md](REVIEW.md), 화면 검증 하네스는 `scripts/synth_smoke/`.

## 종류 (`kind`)

- **`kind:"docs"`(기본값)** — `v0.3/data/phase-7-ui-renewal/` 안 설계 문서 편집 전용.
  앱 코드·DB는 프롬프트에서 절대 못 건드리게 막혀 있다. 안전판은 "사람이 diff로 리뷰".
- **`kind:"code"`** — 앱 코드 구현(2026-09-22 도입). 큐 항목에 `scope`(건드려도 되는
  경로)와 `verify`(성공 판정 커맨드, 보통 `python3 -m pytest tests/test_x.py -q`)를
  같이 적는다. `claude -p`가 "성공"이라 보고해도 그대로 믿지 않는다 — `run_unit.py`가
  워크트리에서 `verify` 커맨드를 **독립적으로 다시 실행**해 전부 통과해야만
  `stage: review`로 넘어간다. 하나라도 실패하면 `stage: blocked`(사람 확인 필요).
  이게 code 항목의 진짜 안전판이다(docs 항목의 "사람 리뷰"에 해당하는 자리를 테스트가
  대신함). 도구 허용도 `settings.CODE_ALLOWED_TOOLS`로 별도(pytest/npm 실행 포함).
  예산·타임아웃도 더 넉넉하다(`PER_RUN_MAX_USD_CODE`, `RUN_TIMEOUT_SEC_CODE`) — 코드
  구현은 테스트·빌드 왕복이 있어 문서 편집보다 턴 수가 늘어난다.

## 왜 있는가

- 사용자가 자주 접속하지 않으므로 무인으로 진행이 필요하다.
- 토큰/비용 한도를 넘기면 안 된다 — Claude Code는 5시간 창의 `rate_limit_event`는
  내보내지만 주간(seven_day) 사용률은 노출하지 않는다(2026-09-22 확인). 그래서
  `ledger.py`가 유일한 예산 근거다.
- 설계 변경은 사람이 확인해야 한다(CLAUDE.md) — 그래서 실행마다 격리 브랜치에
  커밋만 하고, 최종 판단(병합·방향 결정)은 사람에게 남긴다.

## 사용법

```bash
# 게이트 통과 시 큐에서 1건 실행 (야간 시간대에만 통과)
python3 -m scripts.autopilot.run_unit

# 무엇을 할지만 확인 — LLM 호출 없음
python3 -m scripts.autopilot.run_unit --dry-run

# 시간대 게이트만 무시 (수동 검증용 — 예산/유휴/circuit breaker는 그대로 적용)
python3 -m scripts.autopilot.run_unit --ignore-night

# 현황 확인
python3 -m scripts.autopilot.status
```

정지: `.claude/autopilot/STOP` 파일을 만들면 즉시 멈춘다(지울 때까지 유지).
일시정지: 같은 자리에 `PAUSE` 파일.

## 안전장치 (gate.py, fail-closed)

1. STOP/PAUSE 파일
2. 실행 시간대 (기본 KST 02–06시, `settings.py`에서 조정)
3. 유휴 — 이 프로젝트의 실제 세션이 30분 이내 활동했으면 양보
4. 연속 실패 2회 → circuit breaker로 정지
5. 예산 — 일간/주간 누적 상한(`ledger.py`), 실행당 상한은 `--max-budget-usd`

## 큐 형식

`BACKLOG.md`의 `- **[ID]** 설명` 항목 바로 다음 줄에:

```
<!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[]} -->
```

`kind:"code"`는 `scope`/`verify`를 같이 적는다(자세한 필드 설명은
`scripts/autopilot/queue.py` docstring 참조). **메타 줄은 반드시 한 줄**이어야 한다 —
줄바꿈하면 파서가 못 읽고 조용히 사람 전용 항목(`mode:"manual"`)으로 취급한다:

```
<!-- autopilot: {"stage":"queued","mode":"auto","attempts":0,"deps":[],"kind":"code","scope":["src/metrics/pmc.py","tests/test_pmc.py"],"verify":["python3 -m pytest tests/test_pmc.py -q"]} -->
```

메타 줄이 없는 항목(기존 BACKLOG 대부분)은 사람 전용이며 자동 실행에서 건너뛴다.
`stage`: `queued → in_progress → review|blocked → done`. `blocked`은
`DECISIONS.md`에 사람 결정이 올라갔거나(모든 kind), `verify` 검증에 실패했다는 뜻
(`kind:"code"`만 해당).

## 파일

| 파일 | 역할 |
|---|---|
| `settings.py` | 예산·시간대·경로·허용 도구 (비밀값 없음, git 추적) |
| `ledger.py` | 실행 비용 append-only 기록 + 예산 판정 |
| `gate.py` | 실행 전 5단계 안전 확인 |
| `queue.py` | BACKLOG.md 큐 파싱/갱신 |
| `worktree.py` | 격리 git worktree 보장 |
| `notify.py` | Telegram Bot API 알림 (best-effort) |
| `run_unit.py` | 메인 진입점 — 1건 실행 |
| `status.py` | 현황 요약 |

런타임 상태(`ledger.jsonl`, 잠금, 실행 로그)는 `.claude/autopilot/`에 있고
git에 추적되지 않는다(운영 이력이지 코드가 아님).
