"""로컬 레벨 칼만 필터 — 날짜별 관측(VDOT·분산)을 정밀도 가중으로 결합해 기준일의 체력 VDOT와 분산을 낸다(순수).

상태: x_t = 레이스 능력(VDOT, 15℃ 등가). 과정: 랜덤워크, 하루 분산 q. 관측: y_i = x_t + e_i, e_i ~ N(0, r_i).
관측이 많을수록·최근일수록·분산이 작을수록 가중이 커진다. 기여도는 최종 추정에서 관측 종류별 가중 합.
"""
from __future__ import annotations

from datetime import date

INIT_VAR = 9.0           # 첫 관측 전 사전 분산(VDOT²) — 첫 관측값을 중심으로 둔다(정보 없는 사전, 결과 영향 작음)


def _days(a: str, b: str) -> int:
    return (date.fromisoformat(b) - date.fromisoformat(a)).days


def filter_level(obs: list[dict], as_of: str, q: float, low_mult: dict[str, float] | None = None) -> dict | None:
    """obs: [{"date","y","var","kind"}] (날짜 오름차순, as_of 이전만). 반환 {"x","var","weights","n","last"} 또는 None.

    weights: 종류별 최종 추정 기여(합 1). 사전(첫 관측 중심)의 몫은 첫 관측 종류에 합산한다.
    low_mult: 비대칭 변형 — 관측이 현재 추정보다 낮을 때 분산 배율({"race": 4, "set": 4}). 대회 = 상한 증거,
    세트 = 하한 증거라 '낮은 쪽'이 약한 증거다(REVIEW-07 §R4-8(2)). None 이면 대칭.
    """
    obs = [o for o in obs if o["date"] < as_of]
    if not obs:
        return None
    x = obs[0]["y"]
    p = INIT_VAR
    w: dict[str, float] = {obs[0]["kind"]: 1.0}
    last = obs[0]["date"]
    for o in obs:
        p += q * _days(last, o["date"])
        last = o["date"]
        r = o["var"]
        if low_mult and o["y"] < x:
            r *= low_mult.get("race" if o["kind"] == "race" else "set", 1.0)
        k = p / (p + r)
        x += k * (o["y"] - x)
        p *= 1.0 - k
        w = {key: v * (1.0 - k) for key, v in w.items()}
        w[o["kind"]] = w.get(o["kind"], 0.0) + k
    p += q * _days(last, as_of)
    tot = sum(w.values()) or 1.0
    return {"x": x, "var": p, "weights": {k2: round(v / tot, 3) for k2, v in sorted(w.items())}, "n": len(obs), "last": last}


def add_obs(state: dict, y: float, var: float, kind: str) -> dict:
    """기준일 시점의 추가 관측(예: 심박-속도 H) 1개를 반영한 새 상태."""
    k = state["var"] / (state["var"] + var)
    w = {key: v * (1.0 - k) for key, v in state["weights"].items()}
    w[kind] = w.get(kind, 0.0) + k
    tot = sum(w.values()) or 1.0
    return dict(state, x=state["x"] + k * (y - state["x"]), var=state["var"] * (1.0 - k),
                weights={k2: round(v / tot, 3) for k2, v in sorted(w.items())}, n=state["n"] + 1)
