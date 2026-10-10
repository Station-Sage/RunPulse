"""데이터 가져오기 — 업로드 저장, 사본 DB 미리보기(dry-run), 실행 작업. 작업 원장은 sync_jobs(service='import').

미리보기는 DB 사본에 실제 임포터를 돌려 건수를 센다(임포터 로직을 그대로 재사용). 실행은 같은 임포터를 원본 DB에 적용한다.
"""
from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import tempfile
import threading
import uuid
import zipfile
from pathlib import Path

from src.db_setup import get_db_path
from src.utils import sync_jobs

SERVICE = "import"
FILE_EXTS = (".fit", ".gpx", ".tcx")
SOURCES = ("garmin", "strava")
MAX_BYTES = 500 * 1024 * 1024


def imports_dir(user_id: str) -> Path:
    return get_db_path(user_id).parent / "imports"


def _is_media(name: str) -> bool:
    n = name.lower().removesuffix(".gz")
    return n.endswith(FILE_EXTS)


def detect_kind(paths: list[Path]) -> tuple[str | None, str | None]:
    """업로드 파일들 → (kind, 오류). kind: strava_archive | strava_csv | garmin_csv | files."""
    if not paths:
        return None, "파일을 선택해 주세요"
    if len(paths) == 1 and paths[0].suffix.lower() == ".zip":
        try:
            with zipfile.ZipFile(paths[0]) as z:
                if any(n.endswith("activities.csv") for n in z.namelist()):
                    return "strava_archive", None
        except zipfile.BadZipFile:
            return None, "유효한 ZIP 파일이 아니에요"
        return None, "activities.csv가 없어요. Strava 아카이브 ZIP이 맞는지 확인해 주세요"
    if len(paths) == 1 and paths[0].suffix.lower() == ".csv":
        with open(paths[0], encoding="utf-8-sig", errors="replace") as f:
            head = next(csv.reader(f), [])
        return ("strava_csv" if "Activity Date" in head else "garmin_csv"), None
    if all(_is_media(p.name) for p in paths):
        return "files", None
    return None, "Strava ZIP·CSV 한 개, 또는 FIT/GPX/TCX(.gz) 파일만 올릴 수 있어요"


def save_upload(user_id: str, uploads: list[tuple[str, object]]) -> tuple[str, list[Path]]:
    """(파일명, werkzeug FileStorage) 목록 저장 → (upload_id, 경로들)."""
    from werkzeug.utils import secure_filename

    upload_id = uuid.uuid4().hex
    dest = imports_dir(user_id) / upload_id
    dest.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, fs in uploads:
        safe = secure_filename(name) or f"file_{len(paths)}"
        p = dest / safe
        fs.save(str(p))
        paths.append(p)
    return upload_id, paths


def upload_paths(user_id: str, upload_id: str) -> list[Path]:
    if not upload_id.isalnum():
        return []
    d = imports_dir(user_id) / upload_id
    return sorted(p for p in d.iterdir() if p.is_file()) if d.is_dir() else []


def _safe_extract(zip_path: Path, dest: Path) -> Path | None:
    with zipfile.ZipFile(zip_path) as z:
        root = dest.resolve()
        for n in z.namelist():
            if not (dest / n).resolve().is_relative_to(root):
                raise ValueError("ZIP 안에 허용되지 않는 경로가 있어요")
        z.extractall(dest)
    if (dest / "activities.csv").exists():
        return dest
    return next((s for s in sorted(dest.iterdir()) if s.is_dir() and (s / "activities.csv").exists()), None)


def apply_import(conn: sqlite3.Connection, kind: str, paths: list[Path], source: str = "garmin") -> dict:
    """임포터를 conn에 적용. 반환: {recognized, inserted, skipped, enriched, errors}."""
    if kind == "strava_archive":
        from src.import_export.strava_archive import import_strava_archive

        with tempfile.TemporaryDirectory(prefix="runpulse_archive_") as tmp:
            root = _safe_extract(paths[0], Path(tmp))
            if root is None:
                return {"recognized": 0, "inserted": 0, "skipped": 0, "enriched": 0, "errors": 1}
            s = import_strava_archive(conn, root)
        return {"recognized": s["csv_total"], "inserted": s["inserted"], "skipped": s["skipped"],
                "enriched": s["file_linked"], "errors": s["errors"]}
    if kind in ("strava_csv", "garmin_csv"):
        if kind == "strava_csv":
            from src.import_export.strava_csv import import_strava_activities as fn
        else:
            from src.import_export.garmin_csv import import_garmin_csv as fn
        s = fn(conn, paths[0])
        conn.commit()
        return {"recognized": s["inserted"] + s["skipped"] + s["errors"], "inserted": s["inserted"],
                "skipped": s["skipped"], "enriched": 0, "errors": s["errors"]}
    from src.import_history import import_file, parse_file_data

    ins = skip = err = 0
    for p in paths:
        if parse_file_data(p) is None:
            err += 1
        elif import_file(conn, p, source):
            ins += 1
        else:
            skip += 1
    conn.commit()
    return {"recognized": len(paths), "inserted": ins, "skipped": skip, "enriched": 0, "errors": err}


def _new_rows_info(conn: sqlite3.Connection, before_max: int) -> dict:
    lo, hi = conn.execute("SELECT MIN(substr(start_time,1,10)), MAX(substr(start_time,1,10)) "
                          "FROM activity_summaries WHERE id > ?", (before_max,)).fetchone()
    merged = conn.execute(
        "SELECT COUNT(*) FROM activity_summaries a WHERE a.id > ? AND a.matched_group_id IS NOT NULL AND "
        "(SELECT COUNT(*) FROM activity_summaries b WHERE b.matched_group_id = a.matched_group_id) > 1",
        (before_max,)).fetchone()[0]
    return {"from": lo, "to": hi, "merged": merged}


def run_on(conn: sqlite3.Connection, kind: str, paths: list[Path], source: str) -> dict:
    before = conn.execute("SELECT COALESCE(MAX(id), 0) FROM activity_summaries").fetchone()[0]
    stats = apply_import(conn, kind, paths, source)
    return {**stats, **_new_rows_info(conn, before)}


def preview(user_id: str, kind: str, paths: list[Path], source: str) -> dict:
    """DB 사본에 임포터를 돌려 인식·중복·신규·보강 건수와 기간을 센다. 원본은 건드리지 않는다."""
    with tempfile.TemporaryDirectory(prefix="runpulse_preview_") as tmp:
        copy = Path(tmp) / "preview.db"
        src = sqlite3.connect(str(get_db_path(user_id)), timeout=60)
        dst = sqlite3.connect(str(copy))
        try:
            src.backup(dst)
        finally:
            src.close()
        try:
            res = run_on(dst, kind, paths, source)
        finally:
            dst.close()
    return {"kind": kind, "source": source, "recognized": res["recognized"], "new": res["inserted"],
            "duplicates": res["skipped"], "enriched": res["enriched"], "errors": res["errors"],
            "merged": res["merged"], "period": {"from": res["from"], "to": res["to"]}}


def _run(job_id: str, user_id: str, upload_id: str, kind: str, source: str) -> None:
    from src.utils.user_context import set_current_user

    set_current_user(user_id)
    try:
        sync_jobs.update_job(job_id, status="running")
        conn = sqlite3.connect(str(get_db_path(user_id)), timeout=60)
        try:
            res = run_on(conn, kind, upload_paths(user_id, upload_id), source)
        finally:
            conn.close()
        out = {"recognized": res["recognized"], "new": res["inserted"], "skipped": res["skipped"],
               "enriched": res["enriched"], "errors": res["errors"], "period": {"from": res["from"], "to": res["to"]},
               "suggest_recompute": bool(res["inserted"] or res["enriched"])}
        shutil.rmtree(imports_dir(user_id) / upload_id, ignore_errors=True)
        sync_jobs.update_job(job_id, status="completed", completed_days=1, total_days=1,
                             result_json=json.dumps(out, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001 — 원장에 실패 사유를 남긴다
        sync_jobs.update_job(job_id, status="failed", last_error=str(e)[:300], error_code="IMPORT_FAILED")


def start(user_id: str, upload_id: str, source: str = "garmin") -> tuple[dict, str | None]:
    """반환 (data, 오류코드). 오류코드: IMPORT_RUNNING | UPLOAD_NOT_FOUND | INVALID_UPLOAD."""
    active = sync_jobs.get_active_job(SERVICE)
    if active is not None:
        return {"job_id": active.id}, "IMPORT_RUNNING"
    paths = upload_paths(user_id, upload_id)
    if not paths:
        return {}, "UPLOAD_NOT_FOUND"
    kind, err = detect_kind(paths)
    if err:
        return {}, "INVALID_UPLOAD"
    from datetime import date

    today = date.today().isoformat()
    job = sync_jobs.create_job(SERVICE, today, today)
    threading.Thread(target=_run, args=(job.id, user_id, upload_id, kind, source), daemon=True,
                     name=f"import-{job.id[:8]}").start()
    return {"job_id": job.id}, None


def job_view(job: sync_jobs.SyncJob) -> dict:
    state = {"pending": "queued", "running": "running", "completed": "done"}.get(job.status, "failed")
    return {"id": job.id, "state": state, "created_at": job.created_at, "finished_at": job.finished_at,
            "result": json.loads(job.result_json) if job.result_json else None,
            "error": job.last_error if state == "failed" else None}


def history(limit: int = 10) -> list[dict]:
    return [job_view(j) for j in sync_jobs.list_recent_jobs(SERVICE, limit)]
