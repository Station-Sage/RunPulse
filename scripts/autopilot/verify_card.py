"""verify 실패 결정 카드 — 자동 재시도가 끝난 verify 실패를 '실패'가 아니라 진단별 선택지가 있는 사용자 결정으로 올린다.

선택지는 진단(real|absence_hit|missing_target|usage)과 항목 텍스트에서 규칙으로 만든다. 카드에는 규칙 기반 검토안(진단·선택지별 평가)과
추천안(선택지 + 이유)을 싣는다 — 추천은 제안일 뿐 무엇을 고를지는 사용자가 정한다. target(실패 원인 파일)이 있으면 add_target 선택지를 더한다.
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


_REVIEW = {
    "retry_note": "의견란에 방향(계약 변경 허용·고칠 파일 지정)을 주면 가장 정확하다. 비워 두면 실패 출력만 첨부된다.",
    "retry_scope": "실패 출력(원인 위치 포함)을 지시로 받아 모델이 원인부터 고친다. 원인 파일이 범위 밖이면 다시 실패한다.",
    "retry_verify": "커맨드 자체가 틀렸을 때만 효과가 있다. 코드 원인이면 같은 실패가 반복된다.",
    "dropped": "해당 작업을 포기한다 — 실패가 계약 변경 없이는 풀리지 않을 때의 마지막 수단.",
    "add_target": "원인 파일이 항목 범위 밖이라 모델이 고칠 수 없었다. 범위에 넣으면 그 파일을 직접 고칠 수 있어 근본 해결이다.",
}
_DIAG_REVIEW = {
    "real": "테스트가 자동 재시도 후에도 실패한다. 실패한 테스트 파일이 항목 범위 밖이면 모델이 원인을 고칠 수 없어 같은 실패가 반복된다.",
    "absence_hit": "부재 검사(`! grep`)가 계속 적중한다. 적중 위치가 항목 범위 밖이면 고칠 수 없고, 정당한 위치라면 패턴을 좁혀야 한다.",
    "missing_target": "verify 가 가리키는 테스트 파일이 없고 자동 생성도 반복 실패했다.",
    "usage": "verify 명령의 호출 방식 오류가 반복된다 — 코드가 아니라 커맨드 문제다.",
}
_REC = {"real": ("retry_scope", "실패 출력을 근거로 원인을 고치게 하는 것이 근본 해결이다."),
        "absence_hit": ("retry_scope", "적중 위치를 지시로 주면 그 위치를 고쳐 0건으로 만들 수 있다."),
        "missing_target": ("add_target", "테스트 파일 생성을 범위에 허용해야 계약이 유지된다."),
        "usage": ("retry_verify", "커맨드 오류는 커맨드를 고쳐야 풀린다.")}


def build_verify_card(item_id: str, diag: str, reason: str, item_text: str, target: str = "") -> dict:
    head, rows = _TABLE.get(diag, _TABLE["real"])
    rows = list(rows)
    if target and not any(r["action"] == "add_target" for r in rows):
        rows.insert(0, {"action": "add_target", "name": f"`{target}` 를 범위에 추가하고 재시도", "pros": "원인 파일을 직접 고칠 수 있다", "cons": "범위가 넓어진다"})
    rec_action, rec_why = _REC.get(diag, _REC["real"])
    if target and diag in ("real", "absence_hit"):
        rec_action, rec_why = "add_target", f"원인 파일 `{target}` 이 항목 범위 밖이라 고칠 수 없었다. 범위에 넣고 다시 시도하는 것이 근본 해결이다."
    opts = [{"key": chr(65 + i), "pros": "", "cons": "", **r, "review": _REVIEW.get(r["action"], "")} for i, r in enumerate(rows)]
    rec_key = next((o["key"] for o in opts if o["action"] == rec_action), opts[0]["key"])
    rec = decisions.build(item_id, {"kind": "verify_decision", "impact": item_text[:120], "fix": ""},
                          {"why": reason[:600], "design": {"summary": f"{item_id} 검증 실패({diag}) — {head}"[:200]}})
    rec.update(options=opts, diag=diag, review=_DIAG_REVIEW.get(diag, head), recommendation=rec_key, recommend_why=rec_why)
    if target:
        rec["target"] = target
    return rec
