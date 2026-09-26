"""Garmin 참조값 파서(순수) — 젖산역치(LTHR·역치속도·FTP)와 레이스 예측 payload → 날짜별 값(P7-PRED-25).

실측 payload 형태(2026-05 저장본):
  lactate_threshold: {"speed_and_heart_rate": {"calendarDate": "2026-05-01T17:56:58.483", "heartRate": 177,
                      "speed": 0.38055}, "power": {"calendarDate": ..., "functionalThresholdPower": 313}}
  race_predictions : {"calendarDate": "2026-05-11", "time5K": 1201, "time10K": 2585, "timeHalfMarathon": 5847,
                      "timeMarathon": 12849}
레이스 예측 이력(startdate~enddate, 'daily') 응답은 위 dict 의 리스트다(실측 2026-09-26, 최대 366일).
젖산역치 이력(latest=False)은 리스트가 아니라 {"speed": [...], "heart_rate": [...], "power": [...]} 이고 각 항목이
{"from", "until", "series": "running", "value", "updatedDate"}(측정이 갱신된 날짜만 있음, 최대 366일)이다(실측 2026-09-26).
"""
from __future__ import annotations

LT_SPEED_SCALE = 10.0   # Garmin speed 0.38055 → 3.8055 m/s (4:23/km). 10K 대회 페이스(4:25/km)와 정합(2026-09-26 대조)
RACE_KEYS = {"time5K": "race_pred_5k_sec", "time10K": "race_pred_10k_sec",
             "timeHalfMarathon": "race_pred_half_sec", "timeMarathon": "race_pred_marathon_sec"}


def _day(v) -> str | None:
    return str(v)[:10] if v else None


def _parse_lt_history(payload: dict) -> list[dict]:
    """이력 응답 {"speed"|"heart_rate"|"power": [{"from", "value", "series"}]} → 날짜별 병합. running 시리즈만."""
    by_day: dict[str, dict] = {}
    for key, field, scale in (("heart_rate", "lthr_ref", 1.0), ("speed", "lt_speed_ref", LT_SPEED_SCALE), ("power", "ftp", 1.0)):
        for e in payload.get(key) or []:
            if not isinstance(e, dict) or e.get("value") is None or e.get("series", "running") != "running":
                continue
            day = _day(e.get("from") or e.get("updatedDate"))
            if day:
                by_day.setdefault(day, {"date": day, "lthr_ref": None, "lt_speed_ref": None, "ftp": None})[field] = \
                    round(float(e["value"]) * scale, 4)
    return [by_day[d] for d in sorted(by_day)]


def parse_lactate_threshold(payload, fallback_date: str) -> list[dict]:
    """→ [{"date", "lthr_ref", "lt_speed_ref", "ftp"}] (값 없는 키는 None). 알 수 없는 형태면 []."""
    if isinstance(payload, dict) and ("heart_rate" in payload or "speed" in payload) and "speed_and_heart_rate" not in payload:
        return _parse_lt_history(payload)
    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        shr = it.get("speed_and_heart_rate") or it.get("lactateThresholdHeartRate") or it
        pw = it.get("power") or {}
        hr = shr.get("heartRate") if isinstance(shr, dict) else None
        sp = shr.get("speed") if isinstance(shr, dict) else None
        ftp = pw.get("functionalThresholdPower") if isinstance(pw, dict) else None
        if hr is None and sp is None and ftp is None:
            continue
        out.append({"date": _day(shr.get("calendarDate")) or fallback_date,
                    "lthr_ref": float(hr) if hr else None,
                    "lt_speed_ref": round(sp * LT_SPEED_SCALE, 4) if sp else None,
                    "ftp": float(ftp) if ftp else None})
    return out


def parse_race_predictions(payload, fallback_date: str) -> list[dict]:
    """→ [{"date", "race_pred_5k_sec", ...}] — 값이 하나도 없는 항목은 제외."""
    items = payload if isinstance(payload, list) else [payload] if isinstance(payload, dict) else []
    out = []
    for it in items:
        if not isinstance(it, dict):
            continue
        vals = {m: float(it[k]) for k, m in RACE_KEYS.items() if it.get(k)}
        if vals:
            out.append({"date": _day(it.get("calendarDate")) or fallback_date, **vals})
    return out
