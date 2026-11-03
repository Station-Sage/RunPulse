"""데이터 내보내기 — 빠른 CSV 3종(활동·웰니스·부하)과 전체 아카이브 zip 작업. 작업 원장은 sync_jobs(service='export').

CSV는 사람용 열(h:mm:ss, m:ss/km)과 기계용 열(초)을 함께 낸다. 아카이브는 data/users/<uid>/exports/<job>.zip, 24시간 뒤 만료.
"""
from __future__ import annotations

import csv
import io
import json
import sqlite3
import threading
import logging
from datetime import date, datetime, timedelta
from pathlib import Path

from src.db_setup import get_db_path
from src.services import export_groups
from src.utils import sync_jobs

log = logging.getLogger(__name__)

SERVICE = "export"
QUICK_KINDS = ("quick_activities", "quick_wellness", "quick_load")
KINDS = QUICK_KINDS + ("archive",)
EXPIRE_HOURS = 24
_SOURCES = ("garmin", "strava", "intervals", "runalyze")
_LOAD_METRICS = ("ctl", "atl", "tsb", "acwr")


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
    if kind == "archive":
        err = _parse_groups(body, out)
        if err:
            return {}, err
    return out, None


def _parse_groups(body: dict, out: dict) -> str | None:
    out["groups"], out["include_dismissed"] = None, False
    if "include_dismissed" in body:
        if not isinstance(body["include_dismissed"], bool):
            return "include_dismissed는 true/false예요"
        out["include_dismissed"] = body["include_dismissed"]
    if "groups" not in body:
        return None
    g = body["groups"]
    if not isinstance(g, list) or not g or not all(isinstance(k, str) for k in g):
        return "groups는 비어 있지 않은 문자열 목록이에요"
    if len(set(g)) != len(g):
        return "groups에 중복이 있어요"
    unknown = [k for k in g if k not in export_groups.GROUP_KEYS]
    if unknown:
        return f"알 수 없는 groups: {', '.join(unknown)}"
    out["groups"] = g
    return None


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


def _run(job_id: str, user_id: str, frm, to, groups, include_dismissed) -> None:
    from src.services import export_archive
    from src.utils.user_context import set_current_user

    set_current_user(user_id)
    path = None
    try:
        sync_jobs.update_job(job_id, status="running")
        out_dir = exports_dir(user_id)
        out_dir.mkdir(parents=True, exist_ok=True)
        path = out_dir / f"{job_id}.zip"
        conn = sqlite3.connect(f"file:{get_db_path(user_id)}?mode=ro", uri=True, timeout=60)
        try:
            info = export_archive.build_archive(conn, path, groups, frm, to, include_dismissed)
        finally:
            conn.close()
        now = datetime.now().astimezone()
        info.update(size_bytes=path.stat().st_size, filename=f"runpulse_export_{date.today().isoformat()}.zip",
                    include_dismissed=include_dismissed, download_count=0, last_downloaded_at=None,
                    expires_at=(now + timedelta(hours=EXPIRE_HOURS)).isoformat(timespec="seconds"))
        sync_jobs.update_job(job_id, status="completed", completed_days=1, total_days=1,
                             result_json=json.dumps(info, ensure_ascii=False))
        log.info("[export] done user=%s job=%s groups=%s size=%s", user_id, job_id, groups, info["size_bytes"])
    except Exception as e:  # noqa: BLE001 — 원장에 실패 사유를 남긴다
        code = getattr(e, "code", "EXPORT_FAILED")
        if path is not None:
            path.unlink(missing_ok=True)
        log.warning("[export] failed user=%s job=%s code=%s", user_id, job_id, code)
        sync_jobs.update_job(job_id, status="failed", last_error=str(e)[:300], error_code=code)


def start_archive(user_id: str, frm=None, to=None, groups=None, include_dismissed=False) -> tuple[dict, str | None]:
    purge_expired(user_id)
    active = sync_jobs.get_active_job(SERVICE)
    if active is not None:
        return {"job_id": active.id}, "EXPORT_RUNNING"
    today = date.today().isoformat()
    job = sync_jobs.create_job(SERVICE, frm or today, to or today)
    groups = tuple(groups) if groups else export_groups.LEGACY_GROUPS
    threading.Thread(target=_run, args=(job.id, user_id, frm, to, groups, include_dismissed), daemon=True,
                     name=f"export-{job.id[:8]}").start()
    return {"job_id": job.id}, None


def record_download(job: sync_jobs.SyncJob, user_id: str) -> None:
    """다운로드 감사: 횟수·마지막 시각을 원장에 남기고 로그 한 줄."""
    result = json.loads(job.result_json)
    result["download_count"] = result.get("download_count", 0) + 1
    result["last_downloaded_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    sync_jobs.update_job(job.id, result_json=json.dumps(result, ensure_ascii=False))
    log.info("[export] download user=%s job=%s groups=%s n=%s", user_id, job.id, result.get("groups"),
             result["download_count"])


def purge_expired(user_id: str, now: datetime | None = None) -> int:
    """만료된 완료 작업의 zip 을 지우고 원장 상태를 expired 로 바꾼다."""
    n = 0
    for job in sync_jobs.list_recent_jobs(SERVICE, 50):
        if job.status != "completed" or not job.result_json:
            continue
        if job_view(job, now)["state"] != "expired":
            continue
        (exports_dir(user_id) / f"{job.id}.zip").unlink(missing_ok=True)
        sync_jobs.update_job(job.id, status="expired")
        n += 1
    return n


def job_view(job: sync_jobs.SyncJob, now: datetime | None = None) -> dict:
    state = {"pending": "queued", "running": "running", "completed": "done", "expired": "expired"}.get(
        job.status, "failed")
    result = json.loads(job.result_json) if job.result_json else None
    cur = (now.astimezone() if now and now.tzinfo is None else now) or datetime.now().astimezone()
    exp = datetime.fromisoformat(result["expires_at"]) if result else None
    if exp is not None and exp.tzinfo is None:
        exp = exp.astimezone()
    if state == "done" and exp is not None and exp < cur:
        state = "expired"
    return {"id": job.id, "state": state, "created_at": job.created_at, "finished_at": job.finished_at,
            "result": result, "error": job.last_error if state == "failed" else None,
            "error_code": getattr(job, "error_code", None) if state == "failed" else None}


def history(limit: int = 10) -> list[dict]:
    return [job_view(j) for j in sync_jobs.list_recent_jobs(SERVICE, limit)]
