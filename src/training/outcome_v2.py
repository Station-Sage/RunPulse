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


def is_continuous(structure: dict) -> bool:
    """단일 work 단계(반복·휴식 없음) — 이지·롱런 같은 연속 러닝 계획. 세트 비교 대상이 아니다."""
    steps = structure.get("steps", [])
    return len(expand_work(steps)) == 1 and not any(s.get("type") in ("repeat", "rest") for s in steps)


def _step_ok(step: dict, v: float) -> bool:
    """속도 v(m/s)가 work 단계 목표에 드는가. max_only 는 상한 속도(speed_hi)만 본다."""
    if step.get("max_only"):
        return v <= step["speed_hi"] * (1 + PACE_TOL)
    return step["speed_lo"] * (1 - PACE_TOL) <= v <= step["speed_hi"] * (1 + PACE_TOL)


def compare_continuous(structure: dict, act_dur_s: float | None, act_dist_m: float | None,
                       laps: list[tuple[float, float]] | None = None) -> dict | None:
    """연속 러닝 계획 이행 — 볼륨(시간, 없으면 거리) 이행률 + 목표 페이스 구간 비중(랩별 거리 가중, 없으면 평균 속도).

    laps = [(distance_m, duration_sec)]. 비교 기준이 없으면 None.
    compliance = 볼륨 60% + 페이스 40%(목표 페이스가 있을 때). 볼륨은 맞는데 페이스가 크게 어긋나면 'modified'.
    """
    steps = structure.get("steps", [])
    work = next((s for s in steps if s.get("type") == "work"), {})
    p_dur = sum(s.get("dur_s") or 0 for s in steps)
    p_dist = sum(s.get("dist_m") or 0 for s in steps)
    if p_dur and act_dur_s:
        ratio = act_dur_s / p_dur
    elif p_dist and act_dist_m:
        ratio = act_dist_m / p_dist
    else:
        return None
    hit = share = None
    if work.get("speed_lo") and work.get("speed_hi"):
        good = [(d, d / t) for d, t in (laps or []) if d and t and d >= 100]
        if good:
            share = sum(d for d, v in good if _step_ok(work, v)) / sum(d for d, _ in good)
        elif act_dist_m and act_dur_s:
            share = 1.0 if _step_ok(work, act_dist_m / act_dur_s) else 0.0
        if share is not None:
            hit = min(1.0, share / work.get("min_share", 0.8))
    label = "skipped" if ratio < 0.5 else "underperformed" if ratio < 0.85 else "overperformed" if ratio > 1.1 else "on_target"
    if hit is not None and hit < 0.6 and label in ("on_target", "overperformed"):
        label = "modified"                       # 볼륨은 했지만 처방한 페이스가 아니었다
    vol = min(ratio, 1.0)
    comp = 100 * (0.6 * vol + 0.4 * hit) if hit is not None else 100 * vol
    return {"sets_planned": 1, "sets_done": 1 if ratio >= 0.5 else 0, "volume_ratio": round(ratio, 2),
            "target_hit_pct": None if hit is None else round(100 * hit, 1), "pace_share_pct": None if share is None else round(100 * share, 1),
            "compliance_pct": round(comp, 1), "label": label, "continuous": True, "pairs": []}


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
