# DESIGN — 감사 루프 failed 항목 처리 (사유 기록 · 콘솔 노출 · 사용자 결정 · 재개)

> 상태: 설계 초안 · 사용자 승인 대기. 코드 변경 없음.

## 1. 문제

- develop 단계에서 `failed` 가 된 항목은 어떤 코드도 다시 `queued` 로 돌리지 않는다(영구 정체).
- 사유가 저장되지 않는다. 콘솔에는 needs_decision·failed·review 가 한 목록에 사유 없이 나열된다.
- 사용자에게 "왜 안 했는지 / 어떻게 하면 되는지 / 의견" 을 묻는 카드가 없다.
- 단순 `queued` 복귀는 같은 원인으로 또 실패한다. `done` 은 개발을 건너뛴다.

## 2. 실제 사유 조사 (failed 5건, 실행 transcript 확인)

모두 ledger 상 `outcome: success`(18~27초, $0.12~0.18) — 실행 실패가 아니라 `run_once` 후처리가 failed 로 만든 것.

| 항목 | 모델이 한 일 | failed 가 된 경로 |
|---|---|---|
| P7-DATA-MENU-ENTRY-IMPL | 이미 구현돼 있음 확인, 미답 결정을 DECISIONS.md 에 3지선다로 기록 | `_decisions_changed()` |
| P7-UXR-ROADMAP-IMPL | 1-1 은 이미 반영됨(d43dedf). 재정의 3지선다 기록 | 동일 |
| P7-UXR-DESIGN-PENDING-IMPL | ◆·테이퍼·SWR 구현됨. `ai_context` 3함수 삭제는 사용자 결정 없음 → 3지선다 기록 | 동일 |
| P7-LLM-AGENT-CANDIDATES-IMPL | 설계가 "승인 대기" 상태, 1단계 범위(Q1) 답 없음 → 3지선다 기록 | 동일 |
| P7-DATA-STREAM-ELAPSED-IMPL | 코드는 이미 구현, 남은 건 운영 DB 재추출뿐 → 3지선다 기록. pytest 도 승인 대기로 막힘 | 동일 |

결론:
1. **5건 전부 "모델이 새 결정을 요청"** 한 것이다. 진짜 실패가 아니라 사용자 질문인데 `failed` 로 분류돼 묻히고 있다.
2. 그 질문(DECISIONS.md 의 새 섹션, 선택지 3개 + 권고)은 이미 잘 만들어져 있으나 콘솔 카드로 올라가지 않는다.
3. 3건은 "이미 구현됨" 이 근본 원인 — 큐 항목(IMPL)이 현 코드 상태와 어긋나 있다. 재시도해도 같은 결론이 나온다.
4. 부수 원인: 기본 verify 가 시스템 `python3 -m pytest` — pytest 없음(ENV-1). 코드 항목이 이 경로까지 가면 환경 때문에 실패한다.

## 3. 설계

### 3.1 실패 사유 분류 (`fail_kind`) 와 기록

큐 meta 에 `fail_kind`, `fail_reason`(≤300자) 를 추가한다. `run_once` 의 모든 failed 분기가 기록한다.

| fail_kind | 발생 경로 | 처리 |
|---|---|---|
| `asked` | DECISIONS.md 변경(모델이 결정 요청) | **failed 가 아니라 `needs_decision`** 으로 보냄 (3.2) |
| `verify` | `_post_verify` 비정상 종료 | failed + 출력 꼬리 저장 |
| `env` | verify 가 명령 없음/pytest 부재 (rc 127, "No module named pytest") | failed + env 안내 |
| `exec` | claude 실행 2회 연속 실패 | failed |
| `sync` | 워크트리 dirty / rebase 충돌 | failed (재시도 선택지 차단) |

### 3.2 `asked` — 가장 중요 (5/5건)

- `_decisions_changed()` 가 참이면 새로 추가된 `## [<id>]` 섹션을 추출해 pending_decisions 에 **카드로 등록**하고 stage 를 `needs_decision` 으로 한다. `fails` 는 올리지 않는다.
- 카드는 기존 결정 카드와 같은 UI(선택지·권고·자유 의견)를 쓴다 → 사용자가 콘솔에서 답한다.
- 답이 오면 기존 `consume._promote` 가 `queued` 로 복귀시킨다. 이때 **원인 필드를 같이 갱신**한다:
  - 선택된 선택지 본문을 항목의 `scope`(지시)에 덧붙이고 `answered: <결정 id>` 를 meta 에 기록.
  - run_unit 프롬프트에 "이 항목의 결정 [id]는 답변 완료: <선택>. 같은 질문을 다시 DECISIONS.md 에 쓰지 말 것" 을 주입.
  - 따라서 같은 사유로 재실패하지 않는다(사용자 지적 4번에 대한 답).
- 재질문 방지: `asked` 횟수(`asks`)가 2 를 넘으면 카드 대신 `failed`(kind=`asked_loop`) + "결정이 항목 범위를 못 정함 — 항목 재정의 필요" 로 올린다.

### 3.3 "이미 구현됨" 대응 선택지

`asked` 카드의 선택지에 모델의 3지선다 외에 **시스템 공통 선택지**를 항상 덧붙인다.
- **이미 구현됨 → 완료 처리**: stage=`done`, `resolution: already_done`. 개발 없이 닫는 것이 정답인 경우에만 사용자가 명시 선택.
- **폐기**: stage=`done`, `resolution: dropped` (큐 재진입 없음, 요약에서 "폐기" 로 구분 표시). 새 stage 값은 만들지 않는다 — 기존 `done` 의미·집계 호환 유지.
- **항목 재정의 후 진행**: 사용자 의견 텍스트를 `scope` 로 저장하고 queued.

즉 `done` 은 "수동 완료/폐기" 를 사용자가 직접 고른 경우에만, 단순 queued 복귀는 원인 필드 갱신이 동반된 경우에만 일어난다.

### 3.4 `verify` / `env` / `exec` / `sync` failed 카드

stage 는 `failed` 유지, 콘솔에 **사유·로그 꼬리·선택지** 를 가진 카드로 올린다.
- `verify`: ① verify 커맨드 수정 후 재시도(입력란) ② 수정 지시(scope 에 실패 출력 첨부)하고 재시도 ③ 폐기.
- `env`: ① 안내문("`.venv/bin/python -m pytest` 로 verify 변경") + 수정된 verify 로 재시도 ② 폐기. 기본 verify 를 `.venv/bin/python -m pytest tests/ -q` 로 고쳐 재발 자체를 막는다.
- `exec`: ① 재시도(attempts 초기화) ② 폐기.
- `sync`: 재시도 선택지 **없음**. 안내문(워크트리 정리 방법)만 표시, 해소 후 "재개" 버튼.

### 3.5 콘솔 표시

- 목록에서 `failed` 와 `needs_decision`/`review` 를 분리하고, failed 행에 `fail_kind` 배지 + 한 줄 사유를 표시.
- "개발 대기" 카드에 "막힌 항목 N건 — 응답 필요" 를 노출(정지 사유 FAILED 와 구분).

### 3.6 루프 영향

- `asked` 는 `fails` 를 올리지 않으므로 FAIL_LIMIT 정지(FAILED halt)에 기여하지 않는다. 그래서 5건 연속 `asked` 로 루프가 멈추는 일이 없어진다.
- 큐 순서는 건드리지 않는다(결정 반영 항목 앞당기기는 하지 않기로 함).

## 4. 변경 대상

- `scripts/autopilot/run_unit.py`: failed 분기에 `fail_kind/fail_reason` 기록, `_decisions_changed()` → 새 섹션 추출 + needs_decision 전환, 기본 verify 를 `.venv` 기준으로.
- `scripts/autopilot/queue.py`: meta 필드(`fail_kind`, `fail_reason`, `asks`, `answered`, `resolution`) 허용.
- `scripts/audit/consume.py`: `_promote` 가 선택지를 scope 에 반영·`answered` 기록, `done/dropped` 선택 처리.
- `scripts/audit/loop.py`: `_stage` 후 asked 를 실패로 세지 않음.
- `scripts/console/*`: 카드·배지·선택지 UI.
- 테스트: 각 분기(asked 전환, 재질문 상한, 선택 후 scope 갱신, done/dropped, sync 차단, env verify) + 콘솔 스냅샷.
- `v0.3/data/decisions.md`: ADR 기록(failed 의미 재정의).

## 5. 현재 failed 5건의 이행

일괄 이행 스크립트로 `fail_kind=asked` 로 재분류하고, 각 항목의 DECISIONS.md 섹션을 카드로 등록해 `needs_decision` 으로 되돌린다(사용자가 답하면 3.2 흐름). 코드 승인 후 1회 실행.

## 6. 사용자 결정 필요

1. `asked` 재질문 상한을 2 로 할지.
2. 폐기를 `done + resolution: dropped` 로 표현하는 것에 동의하는지(새 stage 를 만들지 않음).
3. ~~기본 verify 를 `.venv/bin/python` 으로 고정~~ — 2026-11-26 사용자 확정(ENV-1 기준).
