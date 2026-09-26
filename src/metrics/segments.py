"""세그먼트 분해 — 랩/스트림 블록을 워밍업·작업·휴식·쿨다운으로 나누고 세트·세션 유형을 판정한다(순수 함수).

평균 HR·평균 페이스·기기 없이(GPS·시간만) 판정한다. 입력 블록 형식:
    {"dur_s": float, "dist_m": float, "speed_ms": float, "hr": float|None, "max_hr": float|None, "itype": str|None}
speed_ms 는 경사 보정 속도(GAP)가 있으면 그것을 넣는다. 세트 구간(R/I/T/M)은 Daniels 처방 구조
(반복 길이·휴식/작업 비·연속 시간)로 정한다(`prediction.daniels.set_zone`, REVIEW-09 §3).
"""
from __future__ import annotations

from statistics import median

from src.metrics.prediction.daniels import set_zone

WORK_RATIO = 1.10       # 작업 블록 후보: 이지 기준 속도의 110% 이상
QUALITY_CONTRAST = 1.18  # 품질 세트: 작업 평균 속도 ≥ 이지 기준 속도 × 1.18 (오토랩 이지런 오탐 제거, REVIEW-09 §3-3)
FLOAT_RATIO = 0.75      # 휴식 속도 ≥ 작업 속도 × 0.75 면 플로트(능동 회복) — 휴식으로 세지 않는다
STRIDE_MAX_S = 40.0     # 이보다 짧은 빠른 블록은 스트라이드(작업 블록에 붙어 있으면 작업의 꼬리로 합친다)
LONG_KM = 16.0
LONG_S = 5400.0
REST_ITYPES = {"REST", "RECOVERY"}


def label_blocks(blocks: list[dict], v_easy: float) -> list[str]:
    """각 블록의 역할: warmup | work | stride | rest | cooldown | easy."""
    labels: list[str] = []
    for b in blocks:
        it = (b.get("itype") or "").upper()
        v = b.get("speed_ms") or 0.0
        if it == "WARMUP":
            labels.append("warmup")
        elif it == "COOLDOWN":
            labels.append("cooldown")
        elif it in REST_ITYPES:
            labels.append("rest")
        elif v >= v_easy * WORK_RATIO:
            labels.append("stride" if b["dur_s"] < STRIDE_MAX_S else "work")
        else:
            labels.append("easy")
    for i, lab in enumerate(labels):      # 오토랩이 반복 끝을 잘라 만든 짧은 조각은 작업의 일부
        if lab == "stride" and ((i > 0 and labels[i - 1] == "work") or (i + 1 < len(labels) and labels[i + 1] == "work")):
            labels[i] = "work"
    work_idx = [i for i, lab in enumerate(labels) if lab == "work"]
    if work_idx:
        first, last = work_idx[0], work_idx[-1]
        for i in range(first + 1, last):
            if labels[i] == "easy":
                labels[i] = "rest"
        for i in range(0, first):
            if labels[i] == "easy":
                labels[i] = "warmup"
        for i in range(last + 1, len(labels)):
            if labels[i] == "easy":
                labels[i] = "cooldown"
    return labels


def build_bouts(blocks: list[dict], labels: list[str]) -> list[dict]:
    """연속 work 블록을 bout 하나로 합친다. 각 bout 직후 첫 rest 의 길이·평균 HR·HR 하강을 붙인다."""
    raw: list[dict] = []
    cur: dict | None = None
    for b, lab in zip(blocks, labels):
        if lab == "work":
            if cur is None:
                cur = {"dur_s": 0.0, "dist_m": 0.0, "hr_sum": 0.0, "hr_dur": 0.0, "max_hr": None}
            cur["dur_s"] += b["dur_s"]
            cur["dist_m"] += b["dist_m"]
            if b.get("hr"):
                cur["hr_sum"] += b["hr"] * b["dur_s"]
                cur["hr_dur"] += b["dur_s"]
            if b.get("max_hr"):
                cur["max_hr"] = max(cur["max_hr"] or 0, b["max_hr"])
            continue
        if cur is not None:
            raw.append(cur)
            cur = None
        if lab == "rest" and raw and "rest_s" not in raw[-1]:
            raw[-1]["rest_s"] = b["dur_s"]
            raw[-1]["rest_hr"] = b.get("hr")
            raw[-1]["rest_speed_ms"] = b.get("speed_ms")
    if cur is not None:
        raw.append(cur)
    out = []
    for o in raw:
        hr = o["hr_sum"] / o["hr_dur"] if o["hr_dur"] else None
        rest_hr = o.get("rest_hr")
        out.append({
            "dur_s": round(o["dur_s"], 1),
            "dist_m": round(o["dist_m"], 1),
            "speed_ms": o["dist_m"] / o["dur_s"] if o["dur_s"] else 0.0,
            "hr": round(hr, 1) if hr else None,
            "max_hr": o["max_hr"],
            "rest_s": o.get("rest_s"),
            "rest_hr": rest_hr,
            "rest_speed_ms": o.get("rest_speed_ms"),
            "hr_drop": round(o["max_hr"] - rest_hr, 1) if (o["max_hr"] and rest_hr) else None,
        })
    return out


def work_set(bouts: list[dict]) -> dict | None:
    """bout 목록 → 세트 구조: 반복 수, 반복 중앙 길이, 작업 시간, 평균 작업 속도, 휴식/작업 비(마지막 bout 제외, 플로트 제외)."""
    if not bouts:
        return None
    n = len(bouts)
    work_s = sum(b["dur_s"] for b in bouts)
    speed = sum(b["dist_m"] for b in bouts) / work_s if work_s else 0.0
    rest = den = 0.0
    for b in bouts[:-1]:
        den += b["dur_s"]
        rv = b.get("rest_speed_ms")
        if b.get("rest_s") and not (rv and b["speed_ms"] and rv >= FLOAT_RATIO * b["speed_ms"]):
            rest += b["rest_s"]
    rho = rest / den if den else 0.0
    rep_s = median(b["dur_s"] for b in bouts)
    return {"n": n, "rep_s": rep_s, "work_s": work_s, "speed_ms": speed, "rho": round(rho, 3),
            "zone": set_zone(n, rep_s, rho, work_s)}


def session_type(bouts: list[dict], total_s: float, total_m: float, v_easy: float,
                 is_race: bool = False, n_strides: int = 0) -> str:
    """race | sprint | repetition | interval | tempo | steady | long | easy (기기 없이 구조·속도 대비로만)."""
    if is_race:
        return "race"
    is_long = total_m >= LONG_KM * 1000 or total_s >= LONG_S
    ws = work_set(bouts)
    if ws is None:
        if n_strides >= 4 and total_s < LONG_S:
            return "sprint"
        return "long" if is_long else "easy"
    quality = ws["speed_ms"] >= QUALITY_CONTRAST * v_easy
    if ws["zone"] is None or not quality:
        if ws["zone"] in ("T", "M") and ws["n"] == 1 and not is_long:
            return "steady"
        return "long" if is_long else "easy"
    return {"R": "repetition", "I": "interval", "T": "tempo"}.get(ws["zone"], "long" if is_long else "steady")


def set_summary(bouts: list[dict]) -> dict | None:
    """세트 요약: 세트 수, 평균 작업 거리·시간, 작업 페이스, 휴식/작업 비율, 세트 간 속도 유지(드롭 %)."""
    if not bouts:
        return None
    n = len(bouts)
    work_s = sum(b["dur_s"] for b in bouts)
    work_m = sum(b["dist_m"] for b in bouts)
    rest_s = sum(b.get("rest_s") or 0 for b in bouts)
    drop = None
    if n >= 4:
        half = n // 2
        v1 = sum(b["speed_ms"] for b in bouts[:half]) / half
        v2 = sum(b["speed_ms"] for b in bouts[-half:]) / half
        drop = round((v1 - v2) / v1 * 100, 1) if v1 else None
    hrs = [b["hr"] for b in bouts if b.get("hr")]
    drops = [b["hr_drop"] for b in bouts if b.get("hr_drop") is not None]
    ws = work_set(bouts)
    return {
        "n_sets": n,
        "zone": ws["zone"],
        "rho": ws["rho"],
        "work_dist_m_avg": round(work_m / n, 1),
        "work_dur_s_avg": round(work_s / n, 1),
        "work_pace_sec_km": round(1000 * work_s / work_m, 1) if work_m else None,
        "work_hr_avg": round(sum(hrs) / len(hrs), 1) if hrs else None,
        "rest_work_ratio": round(rest_s / work_s, 2) if work_s else None,
        "speed_drop_pct": drop,
        "hr_drop_avg": round(sum(drops) / len(drops), 1) if drops else None,
    }


def stream_to_blocks(t: list[float], dist: list[float], hr: list, win_s: float = 30.0, tol: float = 0.08) -> list[dict]:
    """스트림(실제 경과초·누적거리·HR) → 30초 창 블록 → 속도 차 tol 이내 인접 블록 병합."""
    blocks: list[dict] = []
    i, n = 0, len(t)
    while i < n - 1:
        j = i
        while j < n - 1 and t[j] - t[i] < win_s:
            j += 1
        dt = t[j] - t[i]
        dd = max(0.0, (dist[j] or 0) - (dist[i] or 0))
        hs = [h for h in hr[i:j + 1] if h]
        if dt > 0:
            blocks.append({"dur_s": dt, "dist_m": dd, "speed_ms": dd / dt,
                           "hr": sum(hs) / len(hs) if hs else None,
                           "max_hr": max(hs) if hs else None, "itype": None})
        i = j
    merged: list[dict] = []
    for b in blocks:
        if merged and merged[-1]["speed_ms"] > 0 and abs(b["speed_ms"] - merged[-1]["speed_ms"]) / merged[-1]["speed_ms"] <= tol:
            m = merged[-1]
            d = m["dur_s"] + b["dur_s"]
            if m["hr"] and b["hr"]:
                m["hr"] = (m["hr"] * m["dur_s"] + b["hr"] * b["dur_s"]) / d
            else:
                m["hr"] = m["hr"] or b["hr"]
            m["max_hr"] = max(m["max_hr"] or 0, b["max_hr"] or 0) or None
            m["dur_s"] = d
            m["dist_m"] += b["dist_m"]
            m["speed_ms"] = m["dist_m"] / d
        else:
            merged.append(dict(b))
    return merged


def repair_time_axis(elapsed: list[float], duration_s: float) -> list[float]:
    """시간축이 샘플 번호(마지막 값 < 활동시간의 90%)면 활동시간을 균등 분배한 초로 바꾼다."""
    if not elapsed:
        return []
    if elapsed[-1] >= duration_s * 0.9:
        return list(elapsed)
    n = len(elapsed)
    dt = duration_s / max(1, n - 1)
    return [i * dt for i in range(n)]


def cumulative_distance(t: list[float], speed: list) -> list[float]:
    """누적거리가 없는 스트림: 속도 × 시간 적분."""
    out = [0.0]
    for i in range(1, len(t)):
        out.append(out[-1] + (speed[i] or 0.0) * (t[i] - t[i - 1]))
    return out
