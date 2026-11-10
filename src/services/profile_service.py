"""러너 기준값(HRmax·LTHR·역치 페이스·안정심박·주간 목표) — 자체 추정/기기/직접 입력 병합과 사용값 결정.

저장 키: config["profile"]["overrides"] = {key: value}, config["profile"]["source_choice"] = {key: self|device|manual}.
존·플랜 엔진은 effective_value()만 읽는다(옛 user.max_hr / threshold_pace* 키는 legacy fallback).
"""
from __future__ import annotations

import sqlite3
from statistics import median

from src.utils.config import save_config

KEYS = ("hrmax", "lthr", "threshold_pace", "resting_hr", "weekly_km")
SOURCES = ("self", "device", "manual")
_RANGE = {
    "hrmax": (120, 230), "lthr": (100, 220), "threshold_pace": (150, 600),
    "resting_hr": (30, 100), "weekly_km": (0, 300),
}
_LEGACY = {"hrmax": "max_hr", "threshold_pace": "threshold_pace_sec_km", "weekly_km": "weekly_distance_target"}
_DEVICE_PROVIDERS = ("garmin", "intervals")


def _latest(conn: sqlite3.Connection, name: str, provider: str | None = None) -> tuple[float, str] | None:
    sql = ("SELECT numeric_value, scope_id FROM metric_store WHERE metric_name=? AND scope_type='daily' "
           "AND numeric_value IS NOT NULL")
    args: list = [name]
    if provider:
        sql += " AND provider=?"
        args.append(provider)
    else:
        sql += " AND is_primary=1"
    row = conn.execute(sql + " ORDER BY scope_id DESC LIMIT 1", args).fetchone()
    return (float(row[0]), str(row[1])) if row else None


def _self_estimates(conn: sqlite3.Connection) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, metric in (("hrmax", "hrmax_self"), ("lthr", "lthr_self")):
        r = _latest(conn, metric)
        if r:
            out[key] = {"value": round(r[0]), "basis": metric, "at": r[1], "confidence": None}
    rhrs = [r[0] for r in conn.execute(
        "SELECT resting_hr FROM daily_wellness WHERE resting_hr BETWEEN 30 AND 90 "
        "ORDER BY date DESC LIMIT 30")]
    if rhrs:
        out["resting_hr"] = {"value": round(median(rhrs)), "basis": "wellness_30d_median", "at": None, "confidence": None}
    v = _latest(conn, "vdot")
    if v and v[0] > 20:
        from src.utils.daniels_table import get_training_paces
        out["threshold_pace"] = {"value": int(get_training_paces(v[0])["T"]), "basis": "vdot", "at": v[1], "confidence": None}
    return out


def _device_values(conn: sqlite3.Connection) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for key, metric in (("hrmax", "hrmax_ref"), ("lthr", "lthr_ref")):
        for p in _DEVICE_PROVIDERS:
            r = _latest(conn, metric, p)
            if r:
                out[key] = {"value": round(r[0]), "provider": p, "at": r[1]}
                break
    return out


def _stored(config: dict) -> tuple[dict, dict]:
    prof = config.get("profile") or {}
    return dict(prof.get("overrides") or {}), dict(prof.get("source_choice") or {})


def _legacy(config: dict, key: str):
    name = _LEGACY.get(key)
    if key == "threshold_pace":
        u = config.get("user", {})
        return u.get("threshold_pace_sec_km") or u.get("threshold_pace")
    return config.get("user", {}).get(name) if name else None


def _using(key: str, choice: dict, manual: dict, self_v: dict, device: dict) -> str:
    c = choice.get(key)
    if c == "manual" and key in manual:
        return "manual"
    if c == "device" and key in device:
        return "device"
    if c == "self" and key in self_v:
        return "self"
    if key in manual:
        return "manual"
    if key in self_v:
        return "self"
    return "device" if key in device else "none"


def profile_rows(conn: sqlite3.Connection, config: dict) -> list[dict]:
    manual, choice = _stored(config)
    for k in KEYS:
        if k not in manual and (lv := _legacy(config, k)):
            manual[k] = lv
    self_v, device = _self_estimates(conn), _device_values(conn)
    rows = []
    for k in KEYS:
        using = _using(k, choice, manual, self_v, device)
        rows.append({
            "key": k, "self": self_v.get(k), "device": device.get(k),
            "manual": {"value": manual[k]} if k in manual else None, "using": using,
        })
    return rows


def effective_value(config: dict, key: str, conn: sqlite3.Connection | None = None):
    """존·플랜이 읽는 단일 진입점. 해당 값이 없으면 None."""
    if conn is None:
        return _stored(config)[0].get(key, _legacy(config, key))
    try:
        rows = profile_rows(conn, config)
    except sqlite3.Error:
        return _stored(config)[0].get(key, _legacy(config, key))
    for r in rows:
        if r["key"] == key and r["using"] != "none":
            return r[r["using"]]["value"]
    return None


def validate_changes(body: dict) -> tuple[dict, str | None]:
    """body = {"overrides": {key: number|None}, "source_choice": {key: source}} → 정제된 변경."""
    out: dict = {"overrides": {}, "source_choice": {}}
    for key, v in (body.get("overrides") or {}).items():
        if key not in KEYS:
            return {}, f"알 수 없는 항목: {key}"
        if v is None:
            out["overrides"][key] = None
            continue
        lo, hi = _RANGE[key]
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not lo <= v <= hi:
            return {}, f"{key}는 {lo}~{hi} 사이 숫자여야 해요"
        out["overrides"][key] = float(v) if key == "weekly_km" else int(round(v))
    for key, s in (body.get("source_choice") or {}).items():
        if key not in KEYS or s not in SOURCES:
            return {}, f"잘못된 사용 값 선택: {key}={s}"
        out["source_choice"][key] = s
    if not out["overrides"] and not out["source_choice"]:
        return {}, "바꿀 값이 없어요"
    return out, None


def _merge(config: dict, changes: dict) -> dict:
    prof = config.setdefault("profile", {})
    ov, ch = _stored(config)
    for k, v in changes["overrides"].items():
        if v is None:
            ov.pop(k, None)
        else:
            ov[k] = v
    ch.update(changes["source_choice"])
    prof["overrides"], prof["source_choice"] = ov, ch
    return config


_LABEL = {"hrmax": "최대심박", "lthr": "젖산역치 심박", "threshold_pace": "역치 페이스",
          "resting_hr": "안정시 심박", "weekly_km": "주간 목표 거리"}
_SOURCE_LABEL = {"self": "자체 추정", "device": "기기 값", "manual": "직접 입력"}


def check_changes(conn: sqlite3.Connection, config: dict, changes: dict) -> tuple[str, str] | None:
    """변경을 적용했을 때의 상태 검사 → (오류코드, 문구) 또는 None. 저장하지 않는다.

    - D-08: 고른 출처(source_choice)에 값이 없으면 SOURCE_UNAVAILABLE(422).
    - D-07: 이번 변경이 HRmax·LTHR 를 건드렸고 사용값이 LTHR ≥ HRmax 이면 INVALID_PARAM(400).
    """
    import copy

    rows = {r["key"]: r for r in profile_rows(conn, _merge(copy.deepcopy(config), changes))}
    for key, src in changes["source_choice"].items():
        if rows[key].get(src) is None:
            return "SOURCE_UNAVAILABLE", f"{_LABEL[key]}: {_SOURCE_LABEL[src]}이 없어 고를 수 없어요"
    touched = set(changes["overrides"]) | set(changes["source_choice"])
    used = {k: rows[k][rows[k]["using"]]["value"] for k in ("hrmax", "lthr") if rows[k]["using"] != "none"}
    if touched & {"hrmax", "lthr"} and len(used) == 2 and used["lthr"] >= used["hrmax"]:
        return "INVALID_PARAM", (f"젖산역치 심박({used['lthr']:g}bpm)은 최대심박({used['hrmax']:g}bpm)보다 "
                                 "낮아야 해요")
    return None


def apply_changes(config: dict, user_id: str, changes: dict) -> dict:
    _merge(config, changes)
    save_config(config, user_id=user_id)
    return config
