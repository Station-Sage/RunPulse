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
    load_metrics_batch,
    load_metrics_json_batch,
)

dashboard_bp = Blueprint("dashboard", __name__)


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
    rows = conn.execute(
        """SELECT a.id, a.start_time, a.activity_type, a.distance_km,
                  a.duration_sec, a.avg_pace_sec_km, a.avg_hr
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
        act_id, start_time, _, dist, dur, pace, hr = r
        m = metrics.get(act_id, {})
        result.append({
            "id": act_id, "start_time": start_time, "date": str(start_time)[:10],
            "distance_km": dist, "duration_sec": dur, "avg_pace_sec_km": pace, "avg_hr": hr,
            "fearp": m.get("FEARP"),
            "relative_effort": m.get("RelativeEffort"),
        })
    return result


def _load_darp_data(conn: sqlite3.Connection, target_date: str) -> dict:
    return load_darp_batch(conn, target_date)


def _load_fitness_data(conn: sqlite3.Connection, target_date: str) -> tuple[float | None, float | None]:
    vdot_row = conn.execute(
        "SELECT runalyze_vdot FROM daily_fitness WHERE runalyze_vdot IS NOT NULL AND date<=? ORDER BY date DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    shape_row = conn.execute(
        """SELECT metric_value FROM computed_metrics
           WHERE date <= ? AND metric_name = 'MarathonShape' AND activity_id IS NULL
           ORDER BY date DESC LIMIT 1""",
        (target_date,),
    ).fetchone()
    vdot = float(vdot_row[0]) if vdot_row else None
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

    body = cached_page("dashboard", str(db), lambda: _build_dashboard(db))
    return render_template("dashboard.html", body=body, active_tab="dashboard")


def _build_dashboard(db) -> str:
    """대시보드 body HTML 생성 (캐시 builder)."""
    today = date.today().isoformat()
    three_months_ago = (date.today() - timedelta(days=90)).isoformat()

    with sqlite3.connect(str(db)) as conn:
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

        jsons = load_metrics_json_batch(conn, today, ["UTRS", "CIRS", "RMR"])
        utrs_json = jsons.get("UTRS") or {}
        cirs_json = jsons.get("CIRS") or {}
        rmr_json = jsons.get("RMR") or {}
        rmr_old_json = load_metrics_json_batch(conn, three_months_ago, ["RMR"]).get("RMR") or {}

        pmc_data = _load_pmc_data(conn, today, days=60)
        recent_acts = _load_recent_activities(conn, limit=5)
        darp_data = _load_darp_data(conn, today)
        vdot, marathon_shape = _load_fitness_data(conn, today)
        # 신규 로더
        wellness = load_wellness_mini(conn, today)
        weekly = load_weekly_summary(conn, today)
        trends = load_fitness_trends(conn, today, days=60)
        risk_7d = load_risk_7day_trends(conn, today)
        weekly_target = _load_weekly_target(conn)
        # resync
        needs_resync = False
        try:
            needs_resync = get_needs_resync(conn)
        except Exception:
            pass

    tsb_last = pmc_data[-1]["tsb"] if pmc_data else None

    # ── 배너 ─────────────────────────────────────────────────────────────
    banner = ""
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

    # ── 섹션 1: 오늘의 상태 스트립 ────────────────────────────────────────
    status_strip = render_daily_status_strip(
        utrs_val, utrs_json, cirs_val, cirs_json, acwr_val, rtti_val, wellness)

    # ── 섹션 2: 훈련 권장 ─────────────────────────────────────────────────
    recommendation = _render_training_recommendation(utrs_val, utrs_json, cirs_val, tsb_last)

    # ── 섹션 3: 이번 주 훈련 요약 ─────────────────────────────────────────
    weekly_card = render_weekly_summary(weekly, weekly_target)

    # ── 섹션 4: 피트니스 추세 ─────────────────────────────────────────────
    fitness_chart = render_fitness_trends_chart(pmc_data, trends)

    # ── 섹션 5: 레이스 & 피트니스 ─────────────────────────────────────────
    darp_card = _render_darp_mini(darp_data)
    fitness_card = _render_fitness_mini(vdot, marathon_shape)
    rmr_axes = rmr_json.get("axes") if rmr_json else None
    rmr_compare = rmr_old_json.get("axes") if rmr_old_json else None
    rmr_card = _render_rmr_card(rmr_axes or {}, compare_axes=rmr_compare or None)

    # ── 섹션 6: 리스크 상세 ───────────────────────────────────────────────
    risk_data = {"acwr": acwr_val, "lsi": lsi_val, "monotony": mono_val,
                 "strain": strain_val, "tsb": tsb_last}
    risk_pills = render_risk_pills_v2(risk_data, risk_7d)

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
