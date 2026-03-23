"""통합 대시보드 뷰 — Flask Blueprint."""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, render_template

from .helpers import db_path
from .views_dashboard_cards import (
    _CIRS_COLORS,
    _UTRS_COLORS,
    _render_activity_list,
    _render_cirs_banner,
    _render_cirs_breakdown,
    _render_darp_mini,
    _render_fitness_mini,
    _render_gauge_card,
    _render_pmc_chart,
    _render_risk_pills,
    _render_rmr_card,
    _render_training_recommendation,
    _render_utrs_factors,
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
    result = []
    for r in rows:
        act_id, start_time, _, dist, dur, pace, hr = r
        fearp_row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE activity_id=? AND metric_name='FEARP' LIMIT 1",
            (act_id,),
        ).fetchone()
        re_row = conn.execute(
            "SELECT metric_value FROM computed_metrics WHERE activity_id=? AND metric_name='RelativeEffort' LIMIT 1",
            (act_id,),
        ).fetchone()
        result.append({
            "id": act_id, "start_time": start_time, "date": str(start_time)[:10],
            "distance_km": dist, "duration_sec": dur, "avg_pace_sec_km": pace, "avg_hr": hr,
            "fearp": float(fearp_row[0]) if fearp_row and fearp_row[0] else None,
            "relative_effort": float(re_row[0]) if re_row and re_row[0] else None,
        })
    return result


def _load_darp_data(conn: sqlite3.Connection, target_date: str) -> dict:
    """DARP_5k / _10k / _half / _full 메트릭 JSON 조회."""
    result = {}
    for key in ("DARP_5k", "DARP_10k", "DARP_half", "DARP_full"):
        row = conn.execute(
            """SELECT metric_value, metric_json FROM computed_metrics
               WHERE date <= ? AND metric_name = ? AND activity_id IS NULL
               ORDER BY date DESC LIMIT 1""",
            (target_date, key),
        ).fetchone()
        if row and row[0] is not None:
            dist_key = key.split("_", 1)[1]  # "5k", "10k", "half", "full"
            try:
                mj = json.loads(row[1]) if row[1] else {}
            except Exception:
                mj = {}
            result[dist_key] = mj or {"pace_sec_km": float(row[0])}
    return result


def _load_risk_pills(conn: sqlite3.Connection, target_date: str, pmc_data: list[dict]) -> dict:
    """위험 지표 pill 데이터 (ACWR / LSI / Monotony + TSB 최신값)."""
    acwr = _load_metric(conn, target_date, "ACWR")
    lsi = _load_metric(conn, target_date, "LSI")
    mono = _load_metric(conn, target_date, "Monotony")
    tsb = pmc_data[-1]["tsb"] if pmc_data and pmc_data[-1].get("tsb") is not None else None
    return {"acwr": acwr, "lsi": lsi, "monotony": mono, "tsb": tsb}


def _load_fitness_data(conn: sqlite3.Connection, target_date: str) -> tuple[float | None, float | None]:
    """VDOT + Marathon Shape 조회."""
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


# ── 메인 뷰 ─────────────────────────────────────────────────────────────────

@dashboard_bp.get("/dashboard")
def dashboard():
    db = db_path()
    if not db.exists():
        no_db = ("<div class='card'><p>DB가 초기화되지 않았습니다.</p>"
                 "<p><code>python src/db_setup.py</code> 후 동기화하세요.</p></div>")
        return render_template("dashboard.html", banner=no_db, recommendation_card="",
                               utrs_card="", cirs_card="", rmr_card="", risk_pills="",
                               darp_card="", fitness_card="", pmc_chart="",
                               activity_list="", active_tab="dashboard")

    today = date.today().isoformat()
    three_months_ago = (date.today() - timedelta(days=90)).isoformat()

    with sqlite3.connect(str(db)) as conn:
        utrs_val = _load_metric(conn, today, "UTRS")
        utrs_json = _load_metric_json(conn, today, "UTRS") or {}
        cirs_val = _load_metric(conn, today, "CIRS")
        cirs_json = _load_metric_json(conn, today, "CIRS") or {}
        rmr_json = _load_metric_json(conn, today, "RMR") or {}
        rmr_old_json = _load_metric_json(conn, three_months_ago, "RMR") or {}
        pmc_data = _load_pmc_data(conn, today, days=60)
        recent_acts = _load_recent_activities(conn, limit=5)
        darp_data = _load_darp_data(conn, today)
        risk_data = _load_risk_pills(conn, today, pmc_data)
        vdot, marathon_shape = _load_fitness_data(conn, today)

    tsb_last = pmc_data[-1]["tsb"] if pmc_data else None

    # CIRS 경고 배너
    banner = _render_cirs_banner(cirs_val or 0.0) if cirs_val is not None else ""

    # 훈련 권장 카드
    recommendation_card = _render_training_recommendation(utrs_val, utrs_json, cirs_val, tsb_last)

    # UTRS 게이지
    utrs_grade_map = {"rest": "휴식", "light": "경량", "moderate": "보통", "optimal": "최적"}
    utrs_grade_str = utrs_grade_map.get((utrs_json or {}).get("grade", ""), "")
    utrs_factors_html = _render_utrs_factors(utrs_json) if utrs_json else ""
    utrs_card = _render_gauge_card("UTRS 훈련 준비도", utrs_val, 100.0, _UTRS_COLORS,
                                   subtitle="통합 훈련 준비도 지수 (0-100)",
                                   extra_html=utrs_factors_html, grade_label=utrs_grade_str)

    # CIRS 게이지
    cirs_grade_map = {"safe": "안전", "caution": "주의", "warning": "경고", "danger": "위험"}
    cirs_grade_str = cirs_grade_map.get((cirs_json or {}).get("grade", ""), "")
    cirs_breakdown = _render_cirs_breakdown(cirs_json) if cirs_json else ""
    cirs_card = _render_gauge_card("CIRS 부상 위험도", cirs_val, 100.0, _CIRS_COLORS,
                                   subtitle="복합 부상 위험 점수 (낮을수록 안전)",
                                   extra_html=cirs_breakdown, grade_label=cirs_grade_str)

    # RMR 레이더
    rmr_axes = rmr_json.get("axes") if rmr_json else None
    rmr_compare = rmr_old_json.get("axes") if rmr_old_json else None
    rmr_card = _render_rmr_card(rmr_axes or {}, compare_axes=rmr_compare or None)

    # 위험 지표 pills
    risk_pills = _render_risk_pills(risk_data)

    # DARP + Fitness 카드
    darp_card = _render_darp_mini(darp_data)
    fitness_card = _render_fitness_mini(vdot, marathon_shape)

    # PMC 차트 + 활동 목록
    pmc_chart = _render_pmc_chart(pmc_data)
    activity_list = _render_activity_list(recent_acts)

    return render_template(
        "dashboard.html",
        banner=banner,
        recommendation_card=recommendation_card,
        utrs_card=utrs_card,
        cirs_card=cirs_card,
        rmr_card=rmr_card,
        risk_pills=risk_pills,
        darp_card=darp_card,
        fitness_card=fitness_card,
        pmc_chart=pmc_chart,
        activity_list=activity_list,
        active_tab="dashboard",
    )
