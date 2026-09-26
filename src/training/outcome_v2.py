"""계획↔실행 세그먼트 비교(순수, P7-PRED-42) — 계획 단계 구조(structure_json)와 실행 bout(classifier v2 json)를 맞춰 이행률 산출.

structure_json 형식(P7-PRED-42):
  {"steps": [{"type": "warmup", "dur_s": 600},
             {"type": "repeat", "count": 6, "steps": [{"type": "work", "dist_m": 1000, "speed_lo": 3.9, "speed_hi": 4.1},
                                                      {"type": "rest", "dur_s": 90}]},
             {"type": "cooldown", "dur_s": 600}]}
  work 단계는 dist_m 또는 dur_s 중 하나, 목표는 speed_lo/hi(m/s) 또는 hr_lo/hi(bpm) 중 하나(없어도 됨).
"""
from __future__ import annotations

PACE_TOL = 0.03       # 목표 범위 ±3% 까지 적중으로 본다
W_SETS, W_VOL, W_TGT = 0.4, 0.3, 0.3


def expand_work(steps: list[dict]) -> list[dict]:
    """repeat 를 펼쳐 work 단계만 순서대로."""
    out = []
    for s in steps:
        if s.get("type") == "repeat":
            for _ in range(int(s.get("count", 1))):
                out.extend(expand_work(s.get("steps", [])))
        elif s.get("type") == "work":
            out.append(s)
    return out


def _in_target(step: dict, bout: dict) -> bool | None:
    if step.get("speed_lo") and step.get("speed_hi"):
        v = bout["speed_ms"]
        return step["speed_lo"] * (1 - PACE_TOL) <= v <= step["speed_hi"] * (1 + PACE_TOL)
    if step.get("hr_lo") and step.get("hr_hi") and bout.get("hr"):
        return step["hr_lo"] * (1 - PACE_TOL) <= bout["hr"] <= step["hr_hi"] * (1 + PACE_TOL)
    return None


def compare(structure: dict, bouts: list[dict]) -> dict:
    """반환 {"sets_planned", "sets_done", "volume_ratio", "target_hit_pct", "compliance_pct", "label", "pairs"}."""
    plan = expand_work(structure.get("steps", []))
    n_p, n_d = len(plan), len(bouts)
    if n_p == 0:
        return {"sets_planned": 0, "sets_done": n_d, "volume_ratio": None, "target_hit_pct": None,
                "compliance_pct": None, "label": "modified" if n_d else "on_target", "pairs": []}
    pairs, vols, hits = [], [], []
    for st, b in zip(plan, bouts):
        r = b["dist_m"] / st["dist_m"] if st.get("dist_m") else (b["dur_s"] / st["dur_s"] if st.get("dur_s") else None)
        hit = _in_target(st, b)
        if r:
            vols.append(min(r, 1 / r))
        if hit is not None:
            hits.append(hit)
        pairs.append({"ratio": r and round(r, 2), "hit": hit, "speed_ms": round(b["speed_ms"], 3)})
    set_score = min(1.0, n_d / n_p)
    vol = sum(vols) / len(vols) if vols else set_score
    tgt = sum(hits) / len(hits) if hits else 1.0
    comp = round(100 * (W_SETS * set_score + W_VOL * vol + W_TGT * tgt), 1) if n_d else 0.0
    fast = [p for p, st in zip(pairs, plan) if st.get("speed_hi") and p["speed_ms"] > st["speed_hi"] * (1 + PACE_TOL)]
    if n_d == 0:
        label = "skipped"
    elif set_score == 1.0 and len(fast) > len(pairs) / 2:
        label = "overperformed"          # 세트는 다 했고 과반이 목표보다 3% 넘게 빠름
    elif comp >= 85:
        label = "on_target"
    elif comp < 60:
        label = "underperformed"
    else:
        label = "modified" if n_d != n_p else "underperformed"
    return {"sets_planned": n_p, "sets_done": n_d, "volume_ratio": round(vol, 2), "target_hit_pct": round(100 * tgt, 1),
            "compliance_pct": comp, "label": label, "pairs": pairs}


def prediction_note(outcomes: list[dict], min_n: int = 4) -> dict | None:
    """최근 4주 품질 세션 이행 결과 → 예측 1단계 사용(설명·범위만). 가중 반영은 검증 후(P7-PRED-42 §단계)."""
    q = [o for o in outcomes if o.get("compliance_pct") is not None and o.get("sets_planned")]
    if len(q) < min_n:
        return None
    avg = sum(o["compliance_pct"] for o in q) / len(q)
    note = {"n": len(q), "avg_compliance_pct": round(avg, 1), "slow_extra_pct": 0.0, "reason": None}
    if avg < 70:
        note.update(slow_extra_pct=1.0, reason=f"최근 4주 품질 세션 이행률 {avg:.0f}%")
    return note
