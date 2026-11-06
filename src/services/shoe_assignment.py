"""활동 → 신발 배정 해석(읽기 시점, 저장 없음 — Q5). 설계 shoes.md §4.

대상: canonical 러닝 활동(`sport_family == 'running'`). 해석 단위는 matched_group(같은 활동의 소스 사본 전체).
우선순위: manual(activity_shoe origin='manual') > source(gear.shoe_id) > rule 이력(origin='rule')
> rule(활동 kind 의 기본 신발) > none. source·rule 은 개시일 이전·은퇴일 이후 활동에 배정하지 않는다.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field

from src.utils.activity_types import family_clause

_SOURCE_RANK = {"garmin": 1, "intervals": 2, "strava": 3, "runalyze": 4}
_GKEY = "COALESCE(matched_group_id, 'solo_'||id)"
_TRAIL = {"trail_running", "trailrun", "trail run", "trail_run"}
_TREADMILL = {"treadmill_running", "indoor_running", "treadmill", "virtualrun", "virtual run", "virtual_run"}


@dataclass
class Assignment:
    activity_id: int            # canonical id
    date: str
    distance_m: float
    shoe_id: int | None = None
    method: str = "none"        # manual | source | rule | none
    conflict: bool = False
    by_source: dict = field(default_factory=dict)   # source → shoe_id (gear 가 연결된 것만)


def kind_of(raw_type: str | None) -> str:
    """원본 활동 종류 → 기본 신발 kind(road·trail·treadmill). T1 확인값 기준."""
    key = (raw_type or "").strip().lower()
    if key in _TRAIL:
        return "trail"
    if key in _TREADMILL:
        return "treadmill"
    return "road"


def gear_lookup_sources(source: str, gear_id: str) -> list[str]:
    """활동 행의 gear_id 를 찾을 gear.source 후보. Intervals 의 `g…` 는 Strava gear id 를 그대로 옮긴 값."""
    if source == "strava":
        return ["strava", "strava_export"]
    if source == "intervals" and gear_id.startswith("g"):
        return ["intervals", "strava"]
    return [source]


def _in_window(shoe: dict, day: str, *, rule: bool) -> bool:
    if shoe.get("start_date") and day < shoe["start_date"]:
        return False
    if shoe.get("retired_at") and day > shoe["retired_at"]:
        return False
    return not (rule and shoe.get("default_since") and day < shoe["default_since"])


def load_shoes(conn: sqlite3.Connection) -> dict[int, dict]:
    cur = conn.execute("SELECT id, name, category, start_date, retired_at, default_for, default_since,"
                       " initial_distance_m, retire_km FROM user_shoes")
    cols = [d[0] for d in cur.description]
    return {r[0]: dict(zip(cols, r)) for r in cur.fetchall()}


def _canonical_runs(conn, only_ids):
    clause, params = family_clause("running", "activity_type")
    sql = (f"SELECT id, {_GKEY}, substr(start_time,1,10), COALESCE(distance_m,0) FROM v_canonical_activities"
           f" WHERE {clause}")
    if only_ids is not None:
        sql += f" AND id IN ({','.join('?' * len(only_ids))})"
        params = [*params, *only_ids]
    return conn.execute(sql, params).fetchall()


def _group_rows(conn, keys):
    """group key → [(source, gear_id, id)] (우선순위 정렬)."""
    out: dict[str, list] = {}
    rows = conn.execute(f"SELECT {_GKEY}, source, gear_id, id FROM activity_summaries").fetchall() \
        if keys is None else conn.execute(
            f"SELECT {_GKEY}, source, gear_id, id FROM activity_summaries WHERE {_GKEY} IN"
            f" ({','.join('?' * len(keys))})", list(keys)).fetchall()
    for k, src, gid, aid in rows:
        out.setdefault(k, []).append((src, gid, aid))
    for v in out.values():
        v.sort(key=lambda r: (_SOURCE_RANK.get(r[0], 5), r[2]))
    return out


def _raw_types(conn, ids: list[int]) -> dict[int, str]:
    if not ids:
        return {}
    ph = ",".join("?" * len(ids))
    rows = conn.execute(
        "SELECT a.id, COALESCE(json_extract(p.payload,'$.activityType.typeKey'),"
        " json_extract(p.payload,'$.sport_type'), json_extract(p.payload,'$.activity_type_raw'),"
        " json_extract(p.payload,'$.type')) FROM activity_summaries a JOIN source_payloads p"
        " ON p.source=a.source AND p.entity_id=a.source_id AND p.entity_type IN ('activity_summary','csv_export')"
        f" WHERE a.id IN ({ph})", ids).fetchall()
    out: dict[int, str] = {}
    for aid, raw in rows:
        if raw and isinstance(raw, str):
            out.setdefault(aid, raw)
    return out


def resolve(conn: sqlite3.Connection, only_ids: list[int] | None = None,
            shoes: dict[int, dict] | None = None) -> dict[int, Assignment]:
    """canonical 러닝 활동 id → Assignment. only_ids 는 canonical id 제한(None = 전체)."""
    shoes = load_shoes(conn) if shoes is None else shoes
    runs = _canonical_runs(conn, only_ids)
    if not runs:
        return {}
    keys = None if only_ids is None else {r[1] for r in runs}
    groups = _group_rows(conn, keys)
    gear = {(s, g): sid for s, g, sid in conn.execute(
        "SELECT source, source_gear_id, shoe_id FROM gear WHERE shoe_id IS NOT NULL")}
    stored = {aid: (sid, origin) for aid, sid, origin in conn.execute(
        "SELECT activity_id, shoe_id, origin FROM activity_shoe ORDER BY created_at, rowid")}
    defaults = {s["default_for"]: s for s in shoes.values() if s.get("default_for") and not s.get("retired_at")}
    out: dict[int, Assignment] = {}
    pending: list[Assignment] = []
    for cid, gkey, day, dist in runs:
        a = Assignment(cid, day or "", float(dist or 0))
        members = groups.get(gkey, [])
        manual = rule_hist = None
        for src, gid, aid in members:
            if aid in stored:
                sid, origin = stored[aid]
                if origin == "manual":
                    manual = (sid,)
                elif rule_hist is None:
                    rule_hist = sid
            if gid:
                for gs in gear_lookup_sources(src, str(gid)):
                    if (gs, str(gid)) in gear:
                        a.by_source.setdefault(src, gear[(gs, str(gid))])
                        break
        out[cid] = a
        if manual is not None:
            a.shoe_id, a.method = manual[0], "manual"
            continue
        ordered = list(a.by_source.values())
        a.conflict = len(set(ordered)) > 1
        if ordered and ordered[0] in shoes and _in_window(shoes[ordered[0]], a.date, rule=False):
            a.shoe_id, a.method = ordered[0], "source"
            continue
        if rule_hist in shoes and _in_window(shoes[rule_hist], a.date, rule=False):
            a.shoe_id, a.method = rule_hist, "rule"
            continue
        if defaults:
            pending.append(a)
    if pending:
        raws = _raw_types(conn, [a.activity_id for a in pending])
        for a in pending:
            shoe = defaults.get(kind_of(raws.get(a.activity_id)))
            if shoe and _in_window(shoe, a.date, rule=True):
                a.shoe_id, a.method = shoe["id"], "rule"
    return out


def resolve_one(conn: sqlite3.Connection, activity_id: int) -> Assignment | None:
    """임의 활동 id(사본 포함) → 그 그룹 canonical 의 Assignment. 비러닝·없음은 None."""
    from src.utils.canonical import canonical_activity_id
    cid = canonical_activity_id(conn, activity_id)
    return resolve(conn, [cid]).get(cid)


def aggregate(assignments: dict[int, Assignment]) -> tuple[dict[int, dict], int]:
    """신발별 {count, assigned_m, by_method{manual,source,rule}(m), last_used} + 미배정 건수."""
    stats: dict[int, dict] = {}
    unassigned = 0
    for a in assignments.values():
        if a.shoe_id is None:
            unassigned += a.method == "none"
            continue
        s = stats.setdefault(a.shoe_id, {"count": 0, "assigned_m": 0.0, "last_used": None,
                                         "by_method": {"manual": 0.0, "source": 0.0, "rule": 0.0}})
        s["count"] += 1
        s["assigned_m"] += a.distance_m
        s["by_method"][a.method] += a.distance_m
        if a.date and (s["last_used"] is None or a.date > s["last_used"]):
            s["last_used"] = a.date
    return stats, unassigned
