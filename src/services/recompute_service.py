"""지표 재계산 작업 — 시작·진행률·전후 비교(CTL·TSB·VDOT·마라톤 예측·UTRS). 작업 원장은 sync_jobs(service='recompute').

기준값 변경 미리보기(preview_profile)도 여기서 만든다: 존 경계 전후와 영향받는 활동 일수.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, timedelta

from src.db_setup import get_db_path
from src.utils import sync_jobs

SERVICE = "recompute"
SCOPES = ("90d", "all", "from")
# (slug, metric_name, 한글 라벨, 단위)
TRACKED = (
    ("ctl", "ctl", "CTL", ""), ("tsb", "tsb", "TSB", ""), ("vdot", "vdot", "VDOT", ""),
    ("marathon", "race_pred_marathon_sec", "마라톤 예측", "sec"), ("utrs", "utrs", "UTRS", ""),
)
_AFFECTED = {
    "hrmax": ["HR 존 시간", "TRIMP", "CTL/ATL/TSB"], "lthr": ["TRIMP", "CTL/ATL/TSB"],
    "resting_hr": ["TRIMP", "CTL/ATL/TSB"], "threshold_pace": ["훈련 페이스 제안"], "weekly_km": ["주간 목표 진척"],
}
_RECOMPUTE_KEYS = {"hrmax", "lthr", "resting_hr"}


def parse_scope(body: dict) -> tuple[dict, str | None]:
    scope = body.get("scope")
    if scope not in SCOPES:
        return {}, "scope는 90d, all, from 중 하나예요"
    frm = None
    if scope == "from":
        try:
            frm = date.fromisoformat(str(body.get("from")))
        except ValueError:
            return {}, "from은 YYYY-MM-DD 형식이에요"
        if frm > date.today():
            return {}, "from이 미래예요"
    reason = str(body.get("reason") or "manual")[:60]
    return {"scope": scope, "from": frm, "reason": reason}, None


def _days(scope: str, frm: date | None) -> int | None:
    if scope == "90d":
        return 90
    if scope == "from":
        return (date.today() - frm).days + 1
    return None


def snapshot(conn: sqlite3.Connection) -> dict[str, dict | None]:
    """대표 5개 지표의 최신 primary 값."""
    out: dict[str, dict | None] = {}
    for slug, name, _label, _unit in TRACKED:
        row = conn.execute(
            "SELECT numeric_value, scope_id FROM metric_store WHERE metric_name=? AND scope_type='daily' "
            "AND is_primary=1 AND numeric_value IS NOT NULL ORDER BY scope_id DESC LIMIT 1", (name,)).fetchone()
        out[slug] = {"value": float(row[0]), "date": row[1]} if row else None
    return out


def before_after(before: dict, after: dict) -> list[dict]:
    rows = []
    for slug, _n, label, unit in TRACKED:
        b, a = before.get(slug), after.get(slug)
        bv, av = (b or {}).get("value"), (a or {}).get("value")
        delta = round(av - bv, 2) if bv is not None and av is not None else None
        status = "unavailable" if bv is None and av is None else "new" if bv is None else \
            "lost" if av is None else "unchanged" if delta == 0 else "changed"
        rows.append({"slug": slug, "label": label, "unit": unit, "before": bv, "after": av,
                     "delta": delta, "status": status})
    return rows


def _run(job_id: str, user_id: str, days: int | None) -> None:
    from src.metrics.engine import recompute_all
    from src.utils.sync_state import set_current_user

    set_current_user(user_id)
    try:
        sync_jobs.update_job(job_id, status="running")
        conn = sqlite3.connect(str(get_db_path(user_id)), timeout=60)
        try:
            before = snapshot(conn)

            def progress(_d, done, total):
                sync_jobs.update_job(job_id, completed_days=done, total_days=max(total, 1))

            recompute_all(conn, days=days, on_progress=progress)
            conn.commit()
            after = snapshot(conn)
        finally:
            conn.close()
        result = {"before_after": before_after(before, after), "changed_days": (sync_jobs.get_job(job_id).total_days or 0),
                  "formula_changes": []}
        sync_jobs.update_job(job_id, status="completed", result_json=json.dumps(result, ensure_ascii=False))
    except Exception as e:  # noqa: BLE001 — 작업 원장에 실패 사유를 남기고 끝낸다
        sync_jobs.update_job(job_id, status="failed", last_error=str(e)[:300], error_code="RECOMPUTE_FAILED")


def start(user_id: str, scope: str, frm: date | None, reason: str) -> tuple[dict | None, str | None]:
    """재계산 시작. 이미 진행 중이면 (None, 'RECOMPUTE_RUNNING')."""
    active = sync_jobs.get_active_job(SERVICE)
    if active is not None:
        return {"job_id": active.id}, "RECOMPUTE_RUNNING"
    days = _days(scope, frm)
    today = date.today()
    start_d = today - timedelta(days=days - 1) if days else today
    job = sync_jobs.create_job(SERVICE, start_d.isoformat(), today.isoformat(), source_path=reason)
    threading.Thread(target=_run, args=(job.id, user_id, days), daemon=True, name=f"recompute-{job.id[:8]}").start()
    return {"job_id": job.id}, None


def job_view(job: sync_jobs.SyncJob) -> dict:
    state = {"pending": "queued", "running": "running", "completed": "done"}.get(job.status, "failed")
    return {
        "id": job.id, "state": state,
        "progress": {"done": job.completed_days, "total": job.total_days},
        "result": json.loads(job.result_json) if job.result_json else None,
        "error": job.last_error if state == "failed" else None,
        "started_at": job.started_at, "finished_at": job.finished_at,
    }


def preview_profile(conn: sqlite3.Connection, config: dict, changes: dict) -> dict:
    """변경 전/후 HR 존 상한과 영향받는 지표·일수(최근 90일 심박 있는 활동 일수)."""
    from copy import deepcopy

    from src.services import profile_service as ps
    from src.utils.zones import hr_zones

    after_cfg = deepcopy(config)
    prof = after_cfg.setdefault("profile", {})
    ov, ch = ps._stored(after_cfg)  # noqa: SLF001
    for k, v in changes["overrides"].items():
        ov.pop(k, None) if v is None else ov.__setitem__(k, v)
    ch.update(changes["source_choice"])
    prof["overrides"], prof["source_choice"] = ov, ch

    def uppers(cfg):
        v = ps.effective_value(cfg, "hrmax", conn)
        return [z[1] for z in hr_zones(int(v))[:4]] if v else None

    keys = set(changes["overrides"]) | set(changes["source_choice"])
    changed = [k for k in ps.KEYS if k in keys and ps.effective_value(config, k, conn) != ps.effective_value(after_cfg, k, conn)]
    since = (date.today() - timedelta(days=89)).isoformat()
    days = conn.execute(
        "SELECT count(DISTINCT substr(start_time,1,10)) FROM activity_summaries "
        "WHERE substr(start_time,1,10) >= ? AND avg_hr > 0", (since,)).fetchone()[0]
    metrics = sorted({m for k in changed for m in _AFFECTED.get(k, [])})
    return {"changed_keys": changed, "zones_before": uppers(config), "zones_after": uppers(after_cfg),
            "affected_days": days if set(changed) & _RECOMPUTE_KEYS else 0, "affected_metrics": metrics}
