"""데이터 내보내기 — 빠른 CSV 3종(활동·웰니스·부하)과 전체 아카이브 zip 작업. 작업 원장은 sync_jobs(service='export').

CSV는 사람용 열(h:mm:ss, m:ss/km)과 기계용 열(초)을 함께 낸다. 아카이브는 data/users/<uid>/exports/<job>.zip, 7일 뒤 만료.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
import zipfile
from datetime import date, datetime, timedelta
from pathlib import Path

from src.db_setup import SCHEMA_VERSION, get_db_path
from src.utils import sync_jobs

SERVICE = "export"
QUICK_KINDS = ("quick_activities", "quick_wellness", "quick_load")
KINDS = QUICK_KINDS + ("archive",)
EXPIRE_DAYS = 7
_SOURCES = ("garmin", "strava", "intervals", "runalyze")
_LOAD_METRICS = ("ctl", "atl", "tsb", "acwr")
_ARCHIVE_TABLES = ("activity_summaries", "daily_wellness", "metric_store")


def hms(sec) -> str:
    if sec is None:
        return ""
    s = int(round(sec))
    return f"{s // 3600}:{s % 3600 // 60:02d}:{s % 60:02d}"


def pace_str(sec_km) -> str:
    if not sec_km:
        return ""
    s = int(round(sec_km))
    return f"{s // 60}:{s % 60:02d}/km"


def parse_params(body: dict) -> tuple[dict, str | None]:
    kind = body.get("kind")
    if kind not in KINDS:
        return {}, f"kind는 {', '.join(KINDS)} 중 하나예요"
    out: dict = {"kind": kind, "from": None, "to": None}
    for k in ("from", "to"):
        if body.get(k) in (None, ""):
            continue
        try:
            out[k] = date.fromisoformat(str(body[k])).isoformat()
        except ValueError:
            return {}, f"{k}는 YYYY-MM-DD 형식이에요"
    if out["from"] and out["to"] and out["from"] > out["to"]:
        return {}, "from이 to보다 늦어요"
    return out, None


def _range_sql(col: str, frm: str | None, to: str | None) -> tuple[str, list]:
    sql, args = "", []
    if frm:
        sql += f" AND substr({col},1,10) >= ?"
        args.append(frm)
    if to:
        sql += f" AND substr({col},1,10) <= ?"
        args.append(to)
    return sql, args


def _activity_rows(conn, frm, to):
    cond, args = _range_sql("start_time", frm, to)
    cur = conn.execute(
        "SELECT COALESCE(matched_group_id, 'a' || id) AS g, source, start_time, name, activity_type, "
        "distance_m, duration_sec, avg_pace_sec_km, avg_hr, max_hr, avg_cadence, elevation_gain "
        f"FROM activity_summaries WHERE 1=1{cond} ORDER BY start_time, id", args)
    groups: dict[str, list[tuple]] = {}
    for r in cur:
        groups.setdefault(r[0], []).append(r)
    return groups


def activities_csv(conn: sqlite3.Connection, frm=None, to=None):
    """그룹(동일 활동)당 1행: 통합값(소스 우선순위 garmin>strava>intervals>runalyze) + 소스별 원값 열."""
    head = ["start_time", "name", "type", "sources", "distance_km", "duration_hms", "pace_per_km", "avg_hr",
            "max_hr", "cadence", "elevation_m", "duration_sec", "pace_sec_km"]
    raw_cols = [f"{m}_{s}" for s in _SOURCES for m in ("distance_m", "duration_sec", "avg_hr")]
    yield head + raw_cols
    for rows in _activity_rows(conn, frm, to).values():
        by_src = {r[1]: r for r in rows}
        main = next((by_src[s] for s in _SOURCES if s in by_src), rows[0])
        dist = main[5]
        raw = []
        for s in _SOURCES:
            r = by_src.get(s)
            raw += [r[5], r[6], r[8]] if r else ["", "", ""]
        yield [main[2], main[3], main[4], "+".join(sorted(by_src)),
               round(dist / 1000, 3) if dist else "", hms(main[6]), pace_str(main[7]), main[8] or "",
               main[9] or "", main[10] or "", main[11] if main[11] is not None else "",
               main[6] if main[6] is not None else "", main[7] if main[7] is not None else ""] + raw


def wellness_csv(conn: sqlite3.Connection, frm=None, to=None):
    cond, args = _range_sql("date", frm, to)
    cols = ["date", "sleep_score", "sleep_duration_sec", "hrv_weekly_avg", "hrv_last_night", "resting_hr",
            "body_battery_high", "body_battery_low", "avg_stress", "steps", "active_calories", "weight_kg"]
    yield cols[:3] + ["sleep_hms"] + cols[3:]
    for r in conn.execute(f"SELECT {','.join(cols)} FROM daily_wellness WHERE 1=1{cond} ORDER BY date", args):
        yield list(r[:3]) + [hms(r[2])] + list(r[3:])


def load_csv(conn: sqlite3.Connection, frm=None, to=None):
    """metric_store의 일별 primary CTL/ATL/TSB/ACWR를 날짜별 한 행으로 편다."""
    cond, args = _range_sql("scope_id", frm, to)
    marks = ",".join("?" * len(_LOAD_METRICS))
    days: dict[str, dict] = {}
    for sid, name, val in conn.execute(
            f"SELECT scope_id, metric_name, numeric_value FROM metric_store WHERE scope_type='daily' "
            f"AND is_primary=1 AND metric_name IN ({marks}) AND numeric_value IS NOT NULL{cond}",
            [*_LOAD_METRICS, *args]):
        days.setdefault(sid, {})[name] = val
    yield ["date", *_LOAD_METRICS]
    for d in sorted(days):
        yield [d, *(days[d].get(m, "") for m in _LOAD_METRICS)]


_QUICK = {"quick_activities": activities_csv, "quick_wellness": wellness_csv, "quick_load": load_csv}


def csv_text(rows) -> str:
    buf = io.StringIO()
    csv.writer(buf, lineterminator="\n").writerows(rows)
    return "﻿" + buf.getvalue()  # Excel 한글 호환 BOM


def quick_filename(kind: str) -> str:
    return f"runpulse_{kind.removeprefix('quick_')}_{date.today().isoformat()}.csv"


def quick_export(conn: sqlite3.Connection, kind: str, frm=None, to=None) -> str:
    return csv_text(_QUICK[kind](conn, frm, to))


def exports_dir(user_id: str) -> Path:
    return get_db_path(user_id).parent / "exports"


def _table_csv(conn, table: str):
    cur = conn.execute(f"SELECT * FROM {table}")  # noqa: S608 — 고정 상수 테이블명
    yield [d[0] for d in cur.description]
    yield from cur


def build_archive(conn: sqlite3.Connection, path: Path, frm=None, to=None) -> dict:
    """zip 작성 후 manifest 반환. 원본 payload는 소스별 jsonl."""
    counts: dict[str, int] = {}
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for t in _ARCHIVE_TABLES:
            rows = list(_table_csv(conn, t))
            counts[t] = len(rows) - 1
            z.writestr(f"tables/{t}.csv", csv_text(rows))
        for kind, fn in _QUICK.items():
            z.writestr(f"csv/{quick_filename(kind)}", csv_text(fn(conn, frm, to)))
        n = 0
        for src in _SOURCES:
            lines = [json.dumps({"entity_type": r[0], "entity_id": r[1], "entity_date": r[2], "fetched_at": r[3],
                                 "payload": _loads(r[4])}, ensure_ascii=False)
                     for r in conn.execute("SELECT entity_type, entity_id, entity_date, fetched_at, payload "
                                           "FROM source_payloads WHERE source=? ORDER BY fetched_at", (src,))]
            if lines:
                z.writestr(f"raw_payloads/{src}.jsonl", "\n".join(lines) + "\n")
                n += len(lines)
        counts["source_payloads"] = n
        manifest = {"schema_version": SCHEMA_VERSION, "created_at": datetime.now().isoformat(timespec="seconds"),
                    "row_counts": counts, "range": {"from": frm, "to": to}}
        z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
        files = z.namelist()
    return {"files": files, "row_counts": counts}


def _loads(text):
    try:
        return json.loads(text)
    except (TypeError, ValueError):
        return text


def _run(job_id: str, user_id: str, frm, to) -> None:
    from src.utils.sync_state import set_current_user

    set_current_user(user_id)
    try:
        sync_jobs.update_job(job_id, status="running")
        out_dir = exports_dir(user_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{job_id}.zip"
        conn = sqlite3.connect(str(get_db_path(user_id)), timeout=60)
        try:
            info = build_archive(conn, path, frm, to)
        finally:
            conn.close()
        info.update(size_bytes=path.stat().st_size, filename=f"runpulse_archive_{date.today().isoformat()}.zip",
                    expires_at=(datetime.now() + timedelta(days=EXPIRE_DAYS)).isoformat(timespec="seconds"))
        sync_jobs.update_job(job_id, status="completed", completed_days=1, total_days=1,
                             result_json=json.dumps(info, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001 — 원장에 실패 사유를 남긴다
        sync_jobs.update_job(job_id, status="failed", last_error=str(e)[:300], error_code="EXPORT_FAILED")


def start_archive(user_id: str, frm=None, to=None) -> tuple[dict, str | None]:
    active = sync_jobs.get_active_job(SERVICE)
    if active is not None:
        return {"job_id": active.id}, "EXPORT_RUNNING"
    today = date.today().isoformat()
    job = sync_jobs.create_job(SERVICE, frm or today, to or today)
    threading.Thread(target=_run, args=(job.id, user_id, frm, to), daemon=True, name=f"export-{job.id[:8]}").start()
    return {"job_id": job.id}, None


def job_view(job: sync_jobs.SyncJob, now: datetime | None = None) -> dict:
    state = {"pending": "queued", "running": "running", "completed": "done"}.get(job.status, "failed")
    result = json.loads(job.result_json) if job.result_json else None
    expired = bool(result and datetime.fromisoformat(result["expires_at"]) < (now or datetime.now()))
    if expired:
        state = "expired"
    return {"id": job.id, "state": state, "created_at": job.created_at, "finished_at": job.finished_at,
            "result": result, "error": job.last_error if state == "failed" else None}


def history(limit: int = 10) -> list[dict]:
    return [job_view(j) for j in sync_jobs.list_recent_jobs(SERVICE, limit)]
