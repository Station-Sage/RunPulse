"""300줄 초과 분할 결정 카드 — 초과 파일을 곧바로 개발 큐에 넣지 않고 '분리 진행 / 보류' 를 사용자가 고르게 한다.

추천은 규칙 기반 제안일 뿐 자동 적용하지 않는다: 초과폭이 작으면(NEAR 이하) 보류, 크면 분리 진행을 권한다.
"""
from __future__ import annotations

from scripts.audit import decisions

LIMIT = 300
NEAR = 360  # 상한 + 20% — 이 안쪽이면 분리 비용(회귀 위험·diff)이 이득보다 크다고 본다

_SPLIT = {"action": "split", "name": "분리 진행", "pros": "하위 모듈·컴포넌트로 나눠 상한(300줄)을 지킨다",
          "cons": "동작 변경이 없어야 하므로 리팩터링 비용과 회귀 위험이 든다",
          "review": "단위 하나로 큐에 올라가 자동 개발된다. 파일이 계속 커지는 중이거나 책임이 섞였다면 지금 나누는 편이 싸다."}
_DEFER = {"action": "deferred", "name": "보류", "pros": "지금은 손대지 않는다 — 초과폭이 작으면 분리 이득이 작다",
          "cons": "상한 초과 상태가 유지되고 이후 수정 때 더 커질 수 있다",
          "review": "항목을 완료(보류)로 닫는다. 같은 파일은 다시 제안되지 않는다."}


def recommend(lines: int) -> tuple[str, str]:
    """(추천 action, 이유) — 초과 줄 수 기준 규칙."""
    over = lines - LIMIT
    if lines <= NEAR:
        return "deferred", f"{lines}줄로 상한을 {over}줄({over * 100 // LIMIT}%) 넘었을 뿐이다. 이 정도는 분리 비용이 이득보다 커서 보류가 낫다."
    return "split", f"{lines}줄로 상한을 {over}줄({over * 100 // LIMIT}%) 넘었다. 더 커지기 전에 나누는 편이 싸다."


def build_split_card(item_id: str, path: str, lines: int, origin: str) -> dict:
    opts = [{"key": chr(65 + i), **r} for i, r in enumerate((_SPLIT, _DEFER))]
    rec_action, rec_why = recommend(lines)
    rec_key = next(o["key"] for o in opts if o["action"] == rec_action)
    rec = decisions.build(item_id, {"kind": "split_decision", "impact": f"{path} {lines}줄", "fix": ""},
                          {"why": f"{origin} 작업 중 발견 — {path} 가 {lines}줄로 {LIMIT}줄 상한을 초과", "design": {"summary": f"{path} 분할 여부 ({lines}줄)"}})
    rec.update(options=opts, review=f"{path} 는 {lines}줄이다. 분할은 동작을 바꾸지 않는 리팩터링이므로 필수는 아니며, 비용 대비 이득으로 정한다.",
               recommendation=rec_key, recommend_why=rec_why)
    return rec
