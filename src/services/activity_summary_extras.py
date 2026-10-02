"""활동 상세 S1 부가 필드 — workout_class·environment·hr_zones·source_diffs·verdict.

읽기 전용. 이미 조회한 core/splits/source_comparison 위에 얹는 규칙 기반 가공(UX 리뷰 20 §7-2 ①).
DB 접근은 metric_store 단건 조회뿐이며 계산식은 새로 만들지 않는다(기존 메트릭 재사용).
"""
from __future__ import annotations

import json
import sqlite3
import statistics

from src.metrics.workout_classifier import TAG_LABELS

# (row, core 컬럼, 단위, 임계 종류, 임계값, 사유)
_DIFF_ROWS = [
    ("distance", "distance_m", "m", "pct", 0.01, "기기별 GPS 거리 보정 차이"),
    ("elevation", "elevation_gain", "m", "abs", 10.0, "고도 소스(기압계·DEM)와 보정 방식 차이"),
    ("duration", "elapsed_time_sec", "sec", "pct", 0.01, "일시정지 처리 방식 차이"),
    ("avg_hr", "avg_hr", "bpm", "abs", 3.0, "심박 센서·평균 산출 구간 차이"),
    ("temperature", "avg_temperature", "°C", "abs", 2.0, "기기 센서는 체온 영향으로 높게 측정"),
]
_STEADY_PACE_CV = 0.05


def _metric(conn: sqlite3.Connection, ids: list[int], name: str, prefer: tuple[str, ...] = ()) -> dict | None:
    marks = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT provider, numeric_value, text_value, json_value FROM metric_store WHERE scope_type='activity'"
        f" AND scope_id IN ({marks}) AND metric_name=? AND (numeric_value IS NOT NULL OR text_value IS NOT NULL"
        f" OR json_value IS NOT NULL)", [str(i) for i in ids] + [name]).fetchall()
    if not rows:
        return None
    rows = sorted(rows, key=lambda r: prefer.index(r[0]) if r[0] in prefer else len(prefer))
    return {"provider": rows[0][0], "numeric": rows[0][1], "text": rows[0][2], "json": rows[0][3]}


def pace_cv(splits: list[dict]) -> float | None:
    """온전한 스플릿 이동 페이스의 변동계수. 3개 미만이면 None."""
    paces = [s["pace_sec_km"] for s in splits if not s.get("partial") and s.get("pace_sec_km")]
    if len(paces) < 3:
        return None
    return round(statistics.pstdev(paces) / statistics.mean(paces), 4)


def build_workout_class(conn: sqlite3.Connection, ids: list[int], core: dict, splits: list[dict]) -> dict:
    m = _metric(conn, ids, "workout_type_classified", ("runpulse:auto", "runpulse"))
    tag = m["text"] if m else None
    hr_pct = None
    if core.get("avg_hr") and core.get("max_hr"):
        hr_pct = round(core["avg_hr"] / core["max_hr"] * 100, 1)
    return {"workout_class": tag, "label": TAG_LABELS.get(tag) if tag else None,
            "workout_class_basis": {"hr_pct_max": hr_pct, "pace_cv": pace_cv(splits)}}


def build_environment(conn: sqlite3.Connection, ids: list[int], core: dict) -> dict | None:
    temp = _metric(conn, ids, "weather_temp_c", ("open_meteo", "device_corrected"))
    dew = _metric(conn, ids, "weather_dew_point_c", ("open_meteo",))
    fearp = _metric(conn, ids, "fearp", ("runpulse:auto", "runpulse"))
    if not (temp or dew or fearp):
        return None
    fearp_v = fearp["numeric"] if fearp else None
    pace = core.get("avg_pace_sec_km")
    effect = round(pace - fearp_v, 1) if fearp_v and pace else None
    return {"temp_c": temp["numeric"] if temp else None, "dew_point_c": dew["numeric"] if dew else None,
            "fearp_sec_km": fearp_v, "pace_effect_sec_km": effect}


def build_hr_zones(conn: sqlite3.Connection, ids: list[int]) -> dict | None:
    detail = _metric(conn, ids, "hr_zones_detail", ("intervals",))
    if detail and detail["json"]:
        try:
            data = json.loads(detail["json"])
            if isinstance(data, list) and data:
                return {"provider": detail["provider"], "basis": "intervals_zones",
                        "sec": [int(v or 0) for v in data[:5]]}
        except (ValueError, TypeError):
            pass
    secs = []
    for z in range(1, 6):
        m = _metric(conn, ids, f"hr_zone_time_{z}", ("garmin",))
        if not m or m["numeric"] is None:
            return None
        secs.append(int(m["numeric"]))
    return {"provider": "garmin", "basis": "device_zones", "sec": secs}


def build_source_diffs(source_comparison: dict) -> list[dict]:
    """같은 양(quantity)·단위의 행끼리만 비교. 소스 2개 미만이면 []."""
    if len(source_comparison) < 2:
        return []
    out = []
    for row, col, unit, kind, thr, reason in _DIFF_ROWS:
        vals = {src: r.get(col) for src, r in source_comparison.items() if r.get(col) is not None}
        if len(vals) < 2:
            continue
        hi, lo = max(vals.values()), min(vals.values())
        diff, pct = hi - lo, ((hi - lo) / hi if hi else 0.0)
        significant = pct >= thr if kind == "pct" else diff >= thr
        out.append({"row": row, "quantity": row, "unit": unit, "values": vals, "abs": round(diff, 2),
                    "pct": round(pct, 4), "significant": significant,
                    "threshold": {"kind": kind, "value": thr}, "reason": reason if significant else None})
    return out


def _fmt_pace(sec: float) -> str:
    return f"{int(sec // 60)}:{int(round(sec % 60)):02d}/km".replace(":60/", ":59/")


def build_verdict(core: dict, wc: dict, splits: list[dict], environment: dict | None) -> dict | None:
    """규칙 기반 한 줄 판정 + 근거 칩. 페이스·심박 둘 다 없으면 None."""
    pace, hr = core.get("avg_pace_sec_km"), core.get("avg_hr")
    if not pace and not hr:
        return None
    basis = wc["workout_class_basis"]
    cv = basis["pace_cv"]
    head = wc["label"] or "러닝"
    parts = [f"{head} {_fmt_pace(pace)}" if pace else head]
    evidence = []
    if hr:
        pct = basis["hr_pct_max"]
        parts.append(f"평균 심박 {round(hr)}" + (f"(최대의 {round(pct)}%)" if pct else ""))
        if pct:
            evidence.append({"kind": "info", "label": f"최대심박 {round(pct)}%", "target": "hr_pct_max"})
    if cv is not None:
        steady = cv < _STEADY_PACE_CV
        parts.append("페이스 일정" if steady else "페이스 변동 큼")
        evidence.append({"kind": "info", "label": f"페이스 변동 {cv * 100:.1f}%", "target": "pace_cv"})
    eff = environment and environment.get("pace_effect_sec_km")
    if eff and abs(eff) >= 5:
        parts.append(f"날씨로 km당 약 {abs(round(eff))}초 {'느려짐' if eff > 0 else '빨라짐'}")
        evidence.append({"kind": "drill", "label": "날씨 보정", "target": "m.fearp"})
    return {"text": " · ".join(parts), "evidence": evidence[:3]}
