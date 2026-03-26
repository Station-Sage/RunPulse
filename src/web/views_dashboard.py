"""통합 대시보드 뷰 — Flask Blueprint.

7개 섹션: 상태스트립 / 훈련권장 / 주간요약 / 피트니스추세 / 레이스&피트니스 / 리스크상세 / 최근활동.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, render_template

from src.db_setup import get_needs_resync

from .helpers import db_path
from .views_dashboard_cards import (
    _CIRS_COLORS,
    _UTRS_COLORS,
    _render_activity_list,
    _render_cirs_banner,
    _render_cirs_breakdown,
    _render_darp_mini,
    _render_fitness_mini,
    _render_rmr_card,
    _render_training_recommendation,
    _render_utrs_factors,
    render_daily_status_strip,
    render_fitness_trends_chart,
    render_risk_pills_v2,
    render_weekly_summary,
)
from .views_dashboard_loaders import (
    load_fitness_trends,
    load_risk_7day_trends,
    load_weekly_summary,
    load_wellness_mini,
)
from .views_perf import (
    cached_page,
    load_activity_metrics_batch,
    load_darp_batch,
    load_latest_metric_date,
    load_metrics_batch,
    load_metrics_json_batch,
)

dashboard_bp = Blueprint("dashboard", __name__)


import logging as _logging

_log = _logging.getLogger(__name__)


def _load_last_sync_time(conn: sqlite3.Connection) -> str | None:
    """마지막 동기화 완료 시간 (sync_jobs.db에서 조회)."""
    try:
        from src.utils.sync_jobs import list_recent_jobs
        jobs = list_recent_jobs(limit=1)
        if jobs and jobs[0].updated_at:
            return jobs[0].updated_at
        return None
    except Exception:
        return None


def _ensure_today_metrics(conn: sqlite3.Connection, today: str) -> None:
    """오늘 날짜 메트릭이 없으면 자동 계산."""
    row = conn.execute(
        "SELECT 1 FROM computed_metrics WHERE date=? AND metric_name='UTRS' "
        "AND activity_id IS NULL LIMIT 1",
        (today,),
    ).fetchone()
    if row:
        return
    try:
        from src.metrics.engine import run_for_date
        _log.info("오늘(%s) 메트릭 자동 계산 시작", today)
        run_for_date(conn, today, include_weekly=False)
        conn.commit()
        _log.info("오늘 메트릭 계산 완료")
    except Exception as exc:
        _log.warning("오늘 메트릭 자동 계산 실패: %s", exc)


# ── 데이터 조회 ─────────────────────────────────────────────────────────────

def _load_metric(conn: sqlite3.Connection, target_date: str, metric_name: str) -> float | None:
    row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date <= ? AND metric_name = ? AND activity_id IS NULL
           ORDER BY date DESC LIMIT 1""",
        (target_date, metric_name),
    ).fetchone()
    return float(row[0]) if row and row[0] is not None else None


def _load_metric_json(conn: sqlite3.Connection, target_date: str, metric_name: str) -> dict | None:
    row = conn.execute(
        """SELECT metric_json FROM computed_metrics
           WHERE date <= ? AND metric_name = ? AND activity_id IS NULL
           ORDER BY date DESC LIMIT 1""",
        (target_date, metric_name),
    ).fetchone()
    if row and row[0]:
        try:
            return json.loads(row[0])
        except Exception:
            return None
    return None


def _load_pmc_data(conn: sqlite3.Connection, end_date: str, days: int = 60) -> list[dict]:
    start = (date.fromisoformat(end_date) - timedelta(days=days - 1)).isoformat()
    rows = conn.execute(
        "SELECT date, ctl, atl, tsb FROM daily_fitness WHERE date BETWEEN ? AND ? ORDER BY date ASC",
        (start, end_date),
    ).fetchall()
    return [{"date": r[0], "ctl": r[1], "atl": r[2], "tsb": r[3]} for r in rows]


def _load_recent_activities(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    from .route_svg import render_route_svg
    rows = conn.execute(
        """SELECT a.id, a.start_time, a.activity_type, a.distance_km,
                  a.duration_sec, a.avg_pace_sec_km, a.avg_hr, a.name
           FROM v_canonical_activities a WHERE a.activity_type = 'running'
           ORDER BY a.start_time DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    if not rows:
        return []
    act_ids = [r[0] for r in rows]
    metrics = load_activity_metrics_batch(conn, act_ids, ["FEARP", "RelativeEffort"])
    result = []
    for r in rows:
        act_id, start_time, _, dist, dur, pace, hr, name = r
        m = metrics.get(act_id, {})
        svg = render_route_svg(conn, act_id, width=60, height=40)
        result.append({
            "id": act_id, "start_time": start_time, "date": str(start_time)[:10],
            "distance_km": dist, "duration_sec": dur, "avg_pace_sec_km": pace, "avg_hr": hr,
            "name": name or "",
            "route_svg": svg,
            "fearp": m.get("FEARP"),
            "relative_effort": m.get("RelativeEffort"),
        })
    return result


def _load_darp_data(conn: sqlite3.Connection, target_date: str) -> dict:
    return load_darp_batch(conn, target_date)


def _load_fitness_data(conn: sqlite3.Connection, target_date: str) -> tuple[float | None, float | None]:
    # VDOT: computed_metrics 우선, 없으면 daily_fitness (Runalyze > Garmin)
    vdot = None
    cm_row = conn.execute(
        "SELECT metric_value FROM computed_metrics WHERE metric_name='VDOT' "
        "AND metric_value IS NOT NULL AND date<=? ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if cm_row and cm_row[0]:
        vdot = float(cm_row[0])
    else:
        vdot_row = conn.execute(
            "SELECT runalyze_vdot, garmin_vo2max FROM daily_fitness "
            "WHERE (runalyze_vdot IS NOT NULL OR garmin_vo2max IS NOT NULL) "
            "AND date<=? ORDER BY date DESC LIMIT 1",
            (target_date,),
        ).fetchone()
        if vdot_row:
            vdot = float(vdot_row[0]) if vdot_row[0] is not None else (
                float(vdot_row[1]) if vdot_row[1] is not None else None
            )
    shape_row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date <= ? AND metric_name = 'MarathonShape' AND activity_id IS NULL
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    shape = float(shape_row[0]) if shape_row and shape_row[0] is not None else None
    return vdot, shape


def _load_weekly_target(conn: sqlite3.Connection) -> float:
    """config에서 주간 거리 목표 조회."""
    from src.utils.config import load_config
    try:
        cfg = load_config()
        return float(cfg.get("user", {}).get("weekly_distance_target", 40.0))
    except Exception:
        return 40.0


# ── 메인 뷰 ─────────────────────────────────────────────────────────────────

@dashboard_bp.get("/dashboard")
def dashboard():
    db = db_path()
    if not db.exists():
        no_db = ("<div class='card'><p>DB가 초기화되지 않았습니다.</p>"
                 "<p><code>python src/db_setup.py</code> 후 동기화하세요.</p></div>")
        return render_template("dashboard.html", body=no_db, active_tab="dashboard")

    # AI 분석 업데이트 요청 시 AI 캐시 무효화
    from flask import request as _req
    if _req.args.get("refresh_ai"):
        try:
            import sqlite3 as _sql
            with _sql.connect(str(db)) as _c:
                from src.ai.ai_cache import invalidate
                invalidate(_c, "dashboard")
        except Exception:
            pass
        from .views_perf import invalidate_cache
        invalidate_cache(str(db))

    body = cached_page("dashboard", str(db), lambda: _build_dashboard(db))
    return render_template("dashboard.html", body=body, active_tab="dashboard")


def _build_dashboard(db) -> str:
    """대시보드 body HTML 생성 (캐시 builder)."""
    today = date.today().isoformat()
    three_months_ago = (date.today() - timedelta(days=90)).isoformat()

    with sqlite3.connect(str(db), timeout=10) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        # 오늘 메트릭이 없으면 자동 계산
        _ensure_today_metrics(conn, today)

        # 배치 메트릭 로드 (개별 쿼리 9→2회)
        _val_names = ["UTRS", "CIRS", "ACWR", "RTTI", "Monotony", "LSI", "Strain"]
        vals = load_metrics_batch(conn, today, _val_names)
        utrs_val = vals["UTRS"]
        cirs_val = vals["CIRS"]
        acwr_val = vals["ACWR"]
        rtti_val = vals["RTTI"]
        mono_val = vals["Monotony"]
        lsi_val = vals["LSI"]
        strain_val = vals["Strain"]

        metric_date = load_latest_metric_date(conn, today, "UTRS")
        jsons = load_metrics_json_batch(conn, today, ["UTRS", "CIRS", "RMR"])
        utrs_json = jsons.get("UTRS") or {}
        cirs_json = jsons.get("CIRS") or {}
        rmr_json = jsons.get("RMR") or {}
        rmr_old_json = load_metrics_json_batch(conn, three_months_ago, ["RMR"]).get("RMR") or {}

        pmc_data = _load_pmc_data(conn, today, days=60)
        recent_acts = _load_recent_activities(conn, limit=5)
        darp_data = _load_darp_data(conn, today)
        vdot, marathon_shape = _load_fitness_data(conn, today)
        # v0.3 신규 메트릭
        _v3 = load_metrics_batch(conn, today, ["eFTP", "REC", "RRI", "VDOT_ADJ", "TEROI", "SAPI", "DI"])
        # 신규 로더
        wellness = load_wellness_mini(conn, today)
        weekly = load_weekly_summary(conn, today)
        trends = load_fitness_trends(conn, today, days=60)
        risk_7d = load_risk_7day_trends(conn, today)
        weekly_target = _load_weekly_target(conn)
        # resync + 마지막 동기화 시간
        needs_resync = False
        try:
            needs_resync = get_needs_resync(conn)
        except Exception:
            pass
        last_sync = _load_last_sync_time(conn)

    tsb_last = pmc_data[-1]["tsb"] if pmc_data else None

    # sync_bar는 AI 호출 후에 빌드 (캐시 나이 표시 위해 아래에서 생성)

    # ── 섹션 1: 오늘의 상태 스트립 ────────────────────────────────────────
    status_strip = render_daily_status_strip(
        utrs_val, utrs_json, cirs_val, cirs_json, acwr_val, rtti_val, wellness,
        metric_date=metric_date)

    # ── AI 탭별 통합 호출 (1회) ──────────────────────────────────────────
    _cfg = None
    _ai_data = {}
    try:
        from src.utils.config import load_config as _lc
        _cfg = _lc()
        from src.ai.ai_message import get_tab_ai
        _ai_data = get_tab_ai("dashboard", conn, _cfg) or {}
    except Exception:
        pass

    # ── 동기화 상태 바 (AI 캐시 나이 포함) ────────────────────────────────
    sync_time_str = last_sync[:16] if last_sync else "없음"
    _ai_age = _ai_data.get("_ai_cache_age", "")
    _ai_age_html = (
        f"<span style='font-size:0.65rem;color:var(--muted);white-space:nowrap;'>AI {_ai_age}</span>"
        if _ai_age else ""
    )
    sync_bar = (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:8px 12px;margin-bottom:12px;font-size:0.78rem;color:var(--muted);'>"
        f"<span>마지막 동기화: {sync_time_str}</span>"
        "<div style='display:flex;gap:8px;align-items:center;'>"
        "<form method='POST' action='/trigger-sync' style='margin:0;'>"
        "<input type='hidden' name='mode' value='basic'/>"
        "<button type='submit' style='background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "color:#000;border:none;padding:6px 14px;border-radius:16px;font-size:0.75rem;"
        "font-weight:600;cursor:pointer;display:flex;align-items:center;gap:4px;'>"
        "🔄 동기화</button></form>"
        "<a href='/dashboard?refresh_ai=1' style='background:rgba(0,212,255,0.12);"
        "color:var(--cyan);border:1px solid rgba(0,212,255,0.3);padding:5px 12px;"
        "border-radius:16px;font-size:0.73rem;text-decoration:none;display:flex;"
        "align-items:center;gap:4px;'>✨ AI 분석 업데이트</a>"
        + _ai_age_html +
        "<a href='/settings' style='color:var(--muted);font-size:0.73rem;text-decoration:none;'>⚙️</a>"
        "</div></div>"
    )

    # ── 배너 ─────────────────────────────────────────────────────────────
    banner = sync_bar
    if needs_resync:
        banner = (
            "<div class='card' style='background:var(--orange,#ffaa00);color:#000;"
            "padding:12px 16px;margin-bottom:12px;border-radius:8px;'>"
            "<strong>DB 스키마가 업데이트되었습니다.</strong> "
            "새 데이터를 채우려면 <a href='/settings' style='color:#000;"
            "text-decoration:underline;font-weight:bold'>전체 동기화</a>를 실행하세요."
            "</div>"
        )
    cirs_banner = _render_cirs_banner(cirs_val or 0.0) if cirs_val is not None else ""
    banner += cirs_banner

    # ── 섹션 2: 훈련 권장 ─────────────────────────────────────────────────
    recommendation = _render_training_recommendation(utrs_val, utrs_json, cirs_val, tsb_last,
                                                     config=_cfg, conn=conn,
                                                     ai_override=_ai_data.get("recommendation"))

    # ── 섹션 3: 이번 주 훈련 요약 ─────────────────────────────────────────
    weekly_card = render_weekly_summary(weekly, weekly_target)

    # ── 섹션 4: 피트니스 추세 ─────────────────────────────────────────────
    fitness_chart = render_fitness_trends_chart(pmc_data, trends)

    # ── 섹션 5: 레이스 & 피트니스 ─────────────────────────────────────────
    darp_card = _render_darp_mini(darp_data, vdot=vdot, di=_v3.get("DI"))
    fitness_card = _render_fitness_mini(
        vdot, marathon_shape,
        eftp=_v3.get("eFTP"), rec=_v3.get("REC"),
        rri=_v3.get("RRI"), vdot_adj=_v3.get("VDOT_ADJ"),
        config=_cfg, conn=conn,
        ai_override=_ai_data.get("fitness"))
    rmr_axes = rmr_json.get("axes") if rmr_json else None
    rmr_compare = rmr_old_json.get("axes") if rmr_old_json else None
    rmr_card = _render_rmr_card(rmr_axes or {}, compare_axes=rmr_compare or None,
                                config=_cfg, conn=conn,
                                ai_override=_ai_data.get("rmr"))

    # ── 섹션 6: 리스크 상세 ───────────────────────────────────────────────
    risk_data = {"acwr": acwr_val, "lsi": lsi_val, "monotony": mono_val,
                 "strain": strain_val, "tsb": tsb_last}
    risk_pills = render_risk_pills_v2(risk_data, risk_7d, config=_cfg, conn=conn,
                                      ai_override=_ai_data.get("risk"))

    # ── 섹션 7: 최근 활동 ─────────────────────────────────────────────────
    activity_list = _render_activity_list(recent_acts)

    # ── 조립 ──────────────────────────────────────────────────────────────
    body = (
        banner
        + status_strip
        + recommendation
        + weekly_card
        + fitness_chart
        + "<div class='cards-row' style='align-items:stretch;'>"
        + darp_card + fitness_card + rmr_card
        + "</div>"
        + risk_pills
        + activity_list
    )

    return body
