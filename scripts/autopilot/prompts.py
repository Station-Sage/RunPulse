"""claude -p 프롬프트 템플릿·커맨드 조립 — run_unit.py에서 분리한 순수 함수 모음."""
from __future__ import annotations

from . import fail_handling, queue, settings


_PROMPT_TEMPLATE_DOCS = """\
당신은 RunPulse 프로젝트의 Phase 7 UI 재설계 설계 문서 작업을 무인(사람 없이)으로 수행합니다.

규칙 (반드시 지킬 것):
- 작업 범위는 v0.3/data/phase-7-ui-renewal/ 안의 설계 문서로 한정합니다. 이 범위 밖
  (app 코드, DB, CLAUDE.md, .claude/, 다른 브랜치 등)은 절대 건드리지 않습니다.
- 먼저 CLAUDE.md와 v0.3/data/phase-7-ui-renewal/BACKLOG.md를 읽고 그 규칙을 따릅니다.
- 이미 확정된 결정(00 문서의 분기점 A~D, 01의 8원칙)을 바꾸는 판단, 또는 비전·방향성
  트레이드오프가 필요한 갈림길을 만나면 임의로 결정하지 마세요. 대신
  v0.3/data/phase-7-ui-renewal/DECISIONS.md 맨 끝에 "## [{item_id}] <제목>" 섹션으로
  질문·선택지 2~3개·당신의 권고 1개를 append하고, 그 갈림길 이전까지 한 작업만 커밋한
  뒤 종료합니다. 이번 실행은 그것으로 완료된 것으로 간주합니다.
- 작업을 마치면 (부분 완료라도) 반드시 git commit 하나 이상으로 마무리합니다. 커밋
  메시지는 conventional commits(docs:/feat: 등), 무엇을 끝냈고 무엇이 남았는지 명시.
- 커밋 메시지에 Co-Authored-By·Anthropic 메일·"Generated with Claude Code" 같은 트레일러/서명 줄을 절대 넣지 않습니다.
- push는 하지 않습니다. 이 브랜치({branch})는 검토 후 사람이 병합합니다.
- 확신 없는 사실(DB 값, 기존 코드 동작)은 추측하지 말고, 확인할 수 없으면 문서에
  "TODO: 확인 필요"로 남기세요.

이번 작업 [{item_id}]:
{item_text}
"""

_PROMPT_TEMPLATE_CODE = """\
당신은 RunPulse 프로젝트의 코드 구현 작업을 무인(사람 없이)으로 수행합니다.

규칙 (반드시 지킬 것):
- 이번 작업이 건드려도 되는 범위는 다음으로 한정합니다:
{scope}
  이 범위 밖의 파일(다른 기능 영역, CLAUDE.md, .claude/, 다른 브랜치 등)은 절대 건드리지
  않습니다. data/ 아래 실제 사용자 DB(running.db 등)는 존재해도 절대 열지 않습니다 —
  테스트는 기존 conftest.py의 db_conn 픽스처(임시 DB) 또는 tmp_path로만 검증합니다.
- 먼저 CLAUDE.md, .claude/rules/coding-rules.md, .claude/rules/workflow-rules.md를
  읽고 그 규칙을 따릅니다(파일 300줄 이하, Calculator는 CalcContext API만 사용하고
  raw SQL 금지, 새 함수엔 테스트 최소 1개, conventional commits).
- 작업을 마치기 전 반드시 아래 검증 커맨드를 전부 실행해 통과를 확인합니다:
{verify}
  하나라도 실패하면 완료로 간주하지 말고 원인을 고친 뒤 다시 검증합니다. 이 커맨드들은
  당신의 실행이 끝난 뒤 run_unit.py가 독립적으로 다시 돌려 재확인합니다 — 여기서
  통과했다고 보고해도 실제로 안 통과하면 이번 실행은 "review"가 아니라 "blocked"로
  남고, 이는 이번 실행의 실패로 기록됩니다.
- 이미 확정된 설계 결정을 바꾸는 판단, 또는 여러 타당한 구현 방식 중 하나를 골라야
  하는 갈림길(예: 새 스키마 필드 추가, API 응답 형태 변경)을 만나면 임의로 결정하지
  마세요. 대신 v0.3/data/phase-7-ui-renewal/DECISIONS.md 맨 끝에
  "## [{item_id}] <제목>" 섹션으로 질문·선택지 2~3개·당신의 권고 1개를 append하고,
  그 갈림길 이전까지 한 작업만 커밋한 뒤 종료합니다.
- 아래 "이번 작업" 항목에 함수 시그니처·SQL·의사코드가 적혀 있으면 그것이 구현 명세입니다 —
  참고용이 아니라 그대로 따라야 합니다. 원본 설계 문서(03c-library.md 등)의 목업·예시 행을
  직접 다시 읽더라도 그 예시를 근거로 명세와 다른 구조(그룹 기준·집계 방식·재사용 대상·
  타입/컴포넌트)를 택하지 마세요. 명세가 틀렸다고 판단되면 임의로 대체하지 말고 위의
  "갈림길" 규칙대로 DECISIONS.md에 기록하고 멈춥니다. 명세가 "기존 함수/컴포넌트를 재사용"
  하라고 하면 새로 만들지 말고 import해서 쓰세요. 작업 항목의 파일 목록(scope)에 있는데
  건드리지 않은 파일이 있으면 완료 전에 이유를 커밋 메시지에 적으세요.
- BACKLOG.md에서 이번 작업 [{item_id}] 외의 다른 항목(설명 문구·체크박스·
  `<!-- autopilot: ... -->` 메타 주석 어느 것도)은 절대 건드리지 마세요. 다른 항목이
  이번 작업과 관련 있어 보여도 먼저 구현하거나 대신 끝내지 마세요 — 큐는 한 번에
  한 항목만 실행하도록 설계돼 있고, 다른 항목의 `stage`는 오직 run_unit.py가 그
  항목을 직접 집어 verify 커맨드를 독립 재실행한 뒤에만 바뀝니다. **[{item_id}] 자신의
  메타 주석도 당신이 편집하지 마세요** — "review"로의 전환은 이 실행이 끝난 뒤
  run_unit.py가 verify 결과를 보고 판단합니다. workflow-rules.md의 "완료 체크리스트 1.
  BACKLOG.md 항목 상태 업데이트"는 이 무인 실행에는 적용되지 않습니다(그 규칙은
  사람이 진행하는 일반 세션 몫입니다) — 대신 이번 실행에서는 코드 커밋만 하고 큐
  파일은 전혀 수정하지 않는 것이 완료 조건입니다.
- 작업을 마치면 (부분 완료라도) 반드시 git commit 하나 이상으로 마무리합니다. 커밋
  메시지는 conventional commits(feat:/fix:/test: 등), 무엇을 끝냈고 무엇이 남았는지 명시.
- git은 현재 작업 디렉터리(워크트리)에서 `git add <파일>` / `git commit -m …`처럼 **`-C`
  옵션 없이** 실행하세요. `git -C <경로> …`는 허용 규칙(`git add:*` 등)과 매칭되지 않아
  승인 대기로 막히고 커밋이 안 됩니다(2026-09-24 ACTIVITY-ENV-CARD 실행이 이렇게 미커밋으로 끝남).
- 커밋 메시지에 Co-Authored-By·Anthropic 메일·"Generated with Claude Code" 같은 트레일러/서명 줄을 절대 넣지 않습니다.
- push는 하지 않습니다. 이 브랜치({branch})는 검토 후 사람이 병합합니다.

이번 작업 [{item_id}]:
{item_text}
"""


def _format_list(items: list[str], empty: str) -> str:
    if not items:
        return f"  {empty}"
    return "\n".join(f"  - {x}" for x in items)


def build_prompt(item: queue.QueueItem) -> str:
    note = fail_handling.answered_note(item)
    return _build(item) + (f"\n답변 완료된 결정:\n{note}\n" if note else "")


def _build(item: queue.QueueItem) -> str:
    if item.kind == "code":
        return _PROMPT_TEMPLATE_CODE.format(
            item_id=item.item_id, item_text=item.text, branch=settings.AUTOPILOT_BRANCH,
            scope=_format_list(item.scope, "(scope 미지정 — 위험하니 큐 등록 시 채울 것. 지금은 item 설명 텍스트만 근거로 최대한 보수적으로 판단)"),
            verify=_format_list(item.verify, fail_handling.DEFAULT_VERIFY),
        )
    return _PROMPT_TEMPLATE_DOCS.format(
        item_id=item.item_id, item_text=item.text, branch=settings.AUTOPILOT_BRANCH,
    )


def build_cmd(prompt: str, kind: str) -> list[str]:
    allowed = settings.CODE_ALLOWED_TOOLS if kind == "code" else settings.ALLOWED_TOOLS
    budget = settings.PER_RUN_MAX_USD_CODE if kind == "code" else settings.PER_RUN_MAX_USD
    return [
        "claude", "-p", prompt,
        "--model", settings.MODEL,
        "--output-format", "stream-json",
        "--verbose",
        "--no-session-persistence",
        "--permission-mode", "acceptEdits",
        "--allowed-tools", ",".join(allowed),
        "--disallowed-tools", ",".join(settings.DISALLOWED_TOOLS),
        "--max-budget-usd", str(budget),
    ]
