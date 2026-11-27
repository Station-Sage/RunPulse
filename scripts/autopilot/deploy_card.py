"""운영 반영 실패 결정 카드 — 반영(deploy) 실패를 '조용히 다음 라운드'가 아니라 검토안·추천안이 있는 사용자 결정으로 올린다.

실패 종류(branch|dirty|diverged|tests|merge|build)별로 규칙 기반 검토안(원인 진단 + 선택지별 평가)과 추천안(선택지 + 이유)을 만든다.
추천은 제안일 뿐 자동 적용하지 않는다 — 무엇을 고를지는 사용자가 정한다.
선택지 action: fix_unit(수정 단위 큐 투입 후 재시도)|retry_now(지금 재시도)|retry_later(다음 라운드 끝에 재시도)|hold(보류, 사람 처리 후 재개).
"""
from __future__ import annotations

from scripts.audit import decisions

_FIX = {"action": "fix_unit", "name": "수정 단위를 큐에 넣고 고친 뒤 재시도", "pros": "원인을 오토파일럿이 고친다", "cons": "수정 단위 1건이 더 개발된다"}
_NOW = {"action": "retry_now", "name": "지금 재시도", "pros": "일시적 원인이면 바로 반영된다", "cons": "원인이 그대로면 같은 실패가 반복된다"}
_LATER = {"action": "retry_later", "name": "이번엔 건너뛰고 다음 라운드 끝에 다시 시도", "pros": "루프가 멈추지 않고 이어진다", "cons": "이번 라운드 결과 반영이 미뤄진다(커밋은 누적)"}
_HOLD = {"action": "hold", "name": "보류 — 사람이 처리한 뒤 재개", "pros": "원인을 직접 확인·정리할 수 있다", "cons": "처리 전까지 루프가 멈춘다"}

# kind → (진단, [(선택지, 평가)], 추천 action, 추천 이유)
_TABLE = {
    "tests": ("병합 직전 전체 테스트가 실패했다(재실행 1회 후에도). 이번 라운드 변경이 기존 테스트를 깼을 가능성이 크다.",
              [(_FIX, "실패 출력이 있어 원인이 코드에 있다면 가장 근본적인 해결이다."),
               (_NOW, "flaky 이면 통과하지만, 이미 재실행에서도 실패했으므로 기대하기 어렵다."),
               (_LATER, "다음 라운드가 같은 브랜치 위에 쌓이므로 실패 원인이 더 깊어질 수 있다."),
               (_HOLD, "원인이 불명확하거나 계약을 바꿔야 할 때 적합하다.")],
              "fix_unit", "테스트 실패는 코드 원인이라 재시도만으로 해소되지 않는다. 고치지 않고 라운드를 넘기면 실패가 누적된다."),
    "build": ("병합은 끝났으나 frontend 빌드가 실패했다 — 운영 폴더 코드는 새 버전인데 정적 빌드는 이전 상태일 수 있다.",
              [(_FIX, "빌드 오류가 코드(타입·import)에 있다면 고쳐서 다시 빌드한다."),
               (_NOW, "의존성 설치·일시적 자원 문제라면 통과한다. 원인이 코드면 반복 실패한다."),
               (_LATER, "병합이 이미 끝난 상태라 다음 라운드까지 정적 파일이 낡은 채 남는다."),
               (_HOLD, "node_modules 등 환경 문제를 직접 손볼 때 적합하다.")],
              "fix_unit", "빌드 실패는 대개 코드 원인이고 이미 병합이 끝나 방치 시 운영 화면이 낡는다. 먼저 고치는 편이 안전하다."),
    "dirty": ("운영 폴더에 커밋되지 않은 추적 파일 변경이 있다 — 병합하면 덮어쓰거나 충돌할 수 있어 반영을 막았다.",
              [(_NOW, "변경을 커밋·되돌린 뒤라면 바로 통과한다. 그대로면 같은 실패가 난다."),
               (_LATER, "그사이 운영 폴더를 정리하면 다음 라운드 끝에 반영된다."),
               (_HOLD, "변경 내용을 먼저 확인하고 싶을 때 적합하다.")],
              "hold", "운영 폴더의 변경은 사람의 작업일 수 있어 자동 재시도로 덮어쓰면 안 된다. 확인·정리 후 재개하는 것이 안전하다."),
    "branch": ("운영 폴더가 기준 브랜치가 아니다 — 다른 브랜치로 병합하면 안 되므로 반영을 막았다.",
               [(_NOW, "브랜치를 되돌린 뒤라면 통과한다."),
                (_LATER, "그사이 브랜치를 복구하면 다음 라운드 끝에 반영된다."),
                (_HOLD, "사람이 의도한 브랜치 전환인지 먼저 확인할 때 적합하다.")],
               "hold", "누군가 의도적으로 브랜치를 바꿨을 수 있다. 확인 후 복구하고 재개하는 것이 안전하다."),
    "diverged": ("autopilot 브랜치가 기준 브랜치의 후손이 아니다(갈라짐) — fast-forward 병합이 불가능해 사람 확인이 필요하다.",
                 [(_NOW, "갈라짐은 시간이 지나도 풀리지 않으므로 같은 실패가 난다."),
                  (_LATER, "다음 라운드에도 같은 사유로 실패한다."),
                  (_HOLD, "기준 브랜치의 새 커밋을 autopilot 브랜치에 통합(rebase/merge)해야 해결된다.")],
                 "hold", "기준 브랜치와 autopilot 브랜치를 사람이 통합해야 하며, 자동 재시도로는 풀리지 않는다."),
    "merge": ("fast-forward 병합 명령이 실패했다 — 직전 가드를 통과했으므로 그 사이 운영 폴더가 바뀌었거나 락·권한 문제일 수 있다.",
              [(_NOW, "경합·락이 일시적이었다면 통과한다."),
               (_LATER, "원인이 사라졌다면 다음 라운드 끝에 반영된다."),
               (_HOLD, "git 상태(락 파일·권한)를 직접 확인할 때 적합하다.")],
              "retry_now", "가드를 통과한 직후의 실패라 일시적 경합일 가능성이 높다. 한 번 재시도해 보고 반복되면 보류가 낫다."),
}


def build_deploy_card(rnd: int, kind: str, reason: str, units: int = 0, commits: int = 0) -> dict:
    diag, rows, rec_action, rec_why = _TABLE.get(kind, _TABLE["merge"])
    opts = [{"key": chr(65 + i), "pros": "", "cons": "", **o, "review": ev} for i, (o, ev) in enumerate(rows)]
    rec_key = next(o["key"] for o in opts if o["action"] == rec_action)
    rec = decisions.build(f"DEPLOY-R{rnd}", {"kind": "deploy_failed", "impact": f"라운드 {rnd} 통과 단위 {units}건·커밋 {commits}건 미반영", "fix": ""},
                          {"why": reason[:600], "design": {"summary": f"라운드 {rnd} 운영 반영 실패({kind}) — {diag}"[:300]}})
    rec.update(options=opts, diag=kind, review=diag, recommendation=rec_key, recommend_why=rec_why, round=rnd,
               revert="선택 후에도 개발·재시도가 시작되기 전까지는 다른 안으로 바꿀 수 있다. 병합된 커밋은 운영 폴더에서 git revert 로 되돌린다.")
    return rec
