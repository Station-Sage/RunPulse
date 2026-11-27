"""verify 실패 결정 카드 — 자동 재시도가 끝난 verify 실패를 '실패'가 아니라 진단별 선택지가 있는 사용자 결정으로 올린다.

선택지는 진단(real|absence_hit|missing_target|usage)과 항목 텍스트에서 규칙으로 만든다. 무엇을 고를지는 사용자가 정한다.
"""
from __future__ import annotations

from scripts.audit import decisions

_DROP = {"action": "dropped", "name": "폐기", "pros": "큐에서 내린다", "cons": "해당 작업은 하지 않는다"}
_RETRY_VERIFY = {"action": "retry_verify", "name": "verify 커맨드 수정 후 재시도", "pros": "의견란에 새 커맨드를 적는다", "cons": "커맨드가 틀리면 다시 실패한다"}
_RETRY_SCOPE = {"action": "retry_scope", "name": "실패 출력을 지시에 첨부하고 재시도", "pros": "모델이 실패 출력을 보고 원인을 고친다", "cons": "같은 원인이면 다시 실패한다"}
_RETRY_NOTE = {"action": "retry_note", "name": "내 지시를 추가해 재시도", "pros": "의견란의 지시(예: 계약을 바꿔도 됨, 이 파일만 고칠 것)를 scope 에 더한다", "cons": "의견이 비어 있으면 실패 출력만 첨부된다"}

_TABLE = {
    "real": ("테스트 실패가 자동 재시도로 해소되지 않음", [_RETRY_NOTE, _RETRY_SCOPE, _RETRY_VERIFY, _DROP]),
    "absence_hit": ("`! grep` 부재 검사가 계속 적중 — 패턴이 넓거나 일부 위치가 정당할 수 있음",
                    [{**_RETRY_VERIFY, "name": "grep 패턴을 좁혀 재시도", "pros": "의견란에 좁힌 커맨드를 적는다(정당한 위치를 제외)"}, _RETRY_NOTE, _DROP]),
    "missing_target": ("verify 가 가리키는 테스트 파일이 없고 자동 생성도 반복 실패",
                       [{"action": "add_target", "name": "테스트 파일을 범위에 추가하고 재시도", "pros": "그 파일을 만들어 계약을 유지한다", "cons": ""}, _RETRY_VERIFY, _DROP]),
    "usage": ("verify 명령의 인자·호출 방식 오류가 반복", [_RETRY_VERIFY, _RETRY_NOTE, _DROP]),
}


def build_verify_card(item_id: str, diag: str, reason: str, item_text: str, target: str = "") -> dict:
    head, rows = _TABLE.get(diag, _TABLE["real"])
    opts = [{"key": chr(65 + i), "pros": "", "cons": "", **r} for i, r in enumerate(rows)]
    rec = decisions.build(item_id, {"kind": "verify_decision", "impact": item_text[:120], "fix": ""},
                          {"why": reason[:600], "design": {"summary": f"{item_id} 검증 실패({diag}) — {head}"[:200]}})
    rec["options"] = opts
    rec["diag"] = diag
    if target:
        rec["target"] = target
    return rec
