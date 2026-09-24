# 오토파일럿 유닛 리뷰 절차

오토파일럿 유닛(`stage: review`)을 병합하기 전 매번 하는 절차. 2026-09-24 세션에서 유닛 8개 중 5개가
명세와 다르게 구현돼 왔고, 리뷰에서 실제 결함(아래 사례)을 잡았다 — "테스트 통과 + 에러 0건"만으로는
부족하다. 러너 사용법은 [README.md](README.md), 합성 DB 스모크 하네스는 [`scripts/synth_smoke/`](../synth_smoke/__init__.py).

## 1. 명세 대비 diff (매번)

```bash
W=.claude/worktrees/autopilot-phase7
MB=$(git -C $W merge-base renew/data-architecture HEAD)
git -C $W diff --stat $MB HEAD
git -C $W diff $MB HEAD            # BACKLOG의 해당 유닛 명세와 줄 단위 대조
```

- 명세는 "코드를 그대로 구현"이라고 못 박아도 구조·조건·색·배치를 바꾸거나 일부(테스트·가드)를 빼먹는다.
- 이탈은 **main에서 교정**하고, done 리뷰 노트에 *수용/교정*을 구분해 정직하게 적는다("명세 일치"라고 쓰지 않는다).
- 결정(DECISIONS.md)을 어겼는데 `DECISIONS`에 사유도 없이 진행한 경우가 있었다 — 중단 규칙이 지켜지지 않는다고 가정한다.

## 2. 자동 검증

| 종류 | 명령 |
|---|---|
| 프론트 | `cd frontend && npm run check && npm run build` (+ 순수 함수는 `npm run test:unit`) |
| 백엔드 | 해당 테스트 → 병합 후 main에서 **풀** `python3 -m pytest tests` |
| 문서/데이터 | `python3 scripts/check_docs.py`, `python3 scripts/check_data_consistency.py`, `.py`를 추가했으면 `python3 scripts/gen_files_index.py` |

워크트리에서 돌리면 `test_autopilot_run_unit.py`의 워크트리 경로 의존 테스트 3건이 실패한다 — 환경 한정, main에서 재확인.

## 3. 브라우저 실동작 (화면이 바뀐 유닛)

합성 DB로 앱을 띄워 직접 열어 본다([`scripts/synth_smoke/`](../synth_smoke/__init__.py)). 에러 0건은 "아무것도
안 그려짐"을 못 잡는다(스트림 차트가 최초 구현부터 기본으로 꺼져 있던 것도 에러 없이 통과했다).

- `smoke2.mjs` — 텍스트, 390px 가로 넘침, 콘솔/HTTP 에러
- `sweep.mjs` — 화면별 svg/체크박스 개수, 빈 상태 문구
- 클릭·hover·입력이 있는 유닛은 실제로 눌러서 결과 텍스트/`page.title()`까지 확인
- 빈 DB(`--empty`)에서도 한 번: "데이터 수집 중" 계열이 깨지지 않는지
- 스크린샷은 `pw/shots/`에 저장되고 Read로 볼 수 있다(한글·이모지 폰트 설치는 하네스 docstring 참조)

## 4. 병합 절차

1. 워크트리 `BACKLOG.md`의 stage 전이 커밋 → `git merge --no-ff autopilot/phase7`
2. done 전환 + 리뷰 노트 커밋 (노트에 이탈 사항·교정 여부)
3. main 빌드 후 합성 서버 재시작(서버는 코드를 시작 시 한 번 로드) → 브라우저 재확인
4. 다음 유닛 기동 전에 main 교정 커밋을 **먼저** 끝낸다(러너가 시작 때 워크트리를 main에 rebase)

## 5. 실행 환경 함정

- 셸에 `VIRTUAL_ENV=…/scripts/.venv`(pytest 없음)가 잡혀 있다 → `env -u VIRTUAL_ENV /usr/bin/python3`,
  러너 기동은 `env -u VIRTUAL_ENV PATH="$CLEAN_PATH" nohup python3 -m scripts.autopilot.run_unit …`
  (`CLEAN_PATH`는 PATH에서 `scripts/.venv/bin:` 제거).
- BACKLOG 큐 항목은 `- **[ID]**` 줄과 `<!-- autopilot: {…} -->` 사이에 **빈 줄이 있으면 안 된다**(파서가 항목을
  못 찾음). 편집 뒤 `queue.parse`/`next_runnable`/`find_malformed_meta`로 확인. 실행 중에는 BACKLOG.md를 편집하지 않는다.
- `pkill -f serve_synth`는 호출한 셸까지 죽인다(exit 144) → `pgrep -f "^/usr/bin/python3 .*serve_synth"` 루프로 kill.
- default 계정(`data/users/default`)은 쓰지 않는다. pytest가 남기는 `data/users/default/running.db`가 있으면
  `TestRealDbDefault`가 실패하니 pytest 뒤 지운다.
- VS Code 확장에서 `Read/Write/Edit`이 10분 뒤 "PreToolUse hook did not respond"로 실패하면: 확장이 Read/Write/Edit
  직전에 `openTextDocument`로 파일을 열어 저장하는 훅(`claudeCode.autosave`, 기본 켜짐)이 워크스페이스 밖 경로
  (`/tmp` 스크래치패드·`~/.claude/plans`)에서 멈추는 것(권한 문제 아님, 확장 호스트가 응답을 안 함). 이 머신은
  `~/.vscode-server/data/Machine/settings.json`에 `"claudeCode.autosave": false`를 넣어 뒀다(트레이드오프: 에디터에서
  저장 안 한 변경은 Claude가 읽기/쓰기 전에 자동 저장되지 않음). 스크린샷은 워크스페이스 안(`pw/shots/`)에 둔다.

## 6. 발견 사례 (2026-09-24)

| 유닛/화면 | 결함 | 발견 방법 |
|---|---|---|
| PROVIDER-STATUS | `has_data`가 활동 수만 봐서 "데이터 없음"인데 동기화 시각 표시 | diff 대조 |
| METRICS-BROWSER-PROVIDER | 결정(칩 행)과 다른 상시 드롭다운 | diff 대조 |
| TODAY-FITNESS-CHART | 위치·1점 시리즈·SVG에 `var()` 색 | diff 대조 |
| Coach 홈 | 상대 시간 9시간 오차(UTC 파싱) | 브라우저 텍스트 |
| 스트림 | 차트가 기본으로 하나도 안 그려짐 | hover 시나리오 |
| 활동 상세 | 근거 없는 "● 보통" 라벨 | 브라우저 텍스트 |
| 웰니스 | 구현된 "Provider 비교" 탭이 "준비 중"으로 비활성 | 브라우저 텍스트 |
