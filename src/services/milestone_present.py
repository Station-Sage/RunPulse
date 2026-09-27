"""마일스톤 표시용 가공(순수) — 재계산 항목의 내부 메트릭 키를 사람이 읽는 이름으로 바꾸고, 같은 날 예측 재계산은 한 줄로 묶는다.

저장은 메트릭별 1행(metric_recompute)이라 예측 4종을 재계산하면 같은 날 4줄이 쌓인다 — 조회 시점에 합친다.
"""
from __future__ import annotations

_PRED = [("race_pred_5k_sec", "5K"), ("race_pred_10k_sec", "10K"),
         ("race_pred_half_sec", "하프"), ("race_pred_marathon_sec", "마라톤")]
_PRED_KEYS = dict(_PRED)
_OTHER = {"ctl": "체력(CTL)", "runpulse_vdot": "VDOT", "rri": "RRI"}


def _clock(sec: float) -> str:
    s = round(sec)
    h, m, r = s // 3600, s % 3600 // 60, s % 60
    return f"{h}:{m:02d}:{r:02d}" if h else f"{m}:{r:02d}"


def _versions(detail: str | None) -> str:
    """저장된 detail('1.0→2.0 적용')에서 버전 구간만 뽑는다."""
    return (detail or "").replace(" 적용", "").strip()


def present_milestones(rows: list[dict]) -> list[dict]:
    """rows(최신순)를 표시용으로 가공. 재계산 외 항목은 그대로."""
    out: list[dict] = []
    merged: dict[str, dict] = {}
    for r in rows:
        name = r.get("metric_name")
        if r.get("type") != "metric_recompute" or name is None:
            out.append(r)
            continue
        if name in _PRED_KEYS:
            g = merged.get(r["date"])
            part = f"{_PRED_KEYS[name]} {_clock(r['old_value'])}→{_clock(r['new_value'])}"
            if g is None:
                g = merged[r["date"]] = {**r, "title": "예측 기록 재계산", "_parts": {}, "_ver": _versions(r.get("detail"))}
                out.append(g)
            g["_parts"][name] = part
        else:
            label = _OTHER.get(name, name)
            out.append({**r, "title": f"{label} 재계산",
                        "detail": f"{r['old_value']:.1f}→{r['new_value']:.1f} · 알고리즘 {_versions(r.get('detail'))}"})
    for g in merged.values():
        parts = [g["_parts"][k] for k, _ in _PRED if k in g["_parts"]]
        g["detail"] = f"{' · '.join(parts)} · 알고리즘 {g.pop('_ver')}"
        g.pop("_parts")
        g["metric_name"], g["old_value"], g["new_value"] = None, None, None
    return out
