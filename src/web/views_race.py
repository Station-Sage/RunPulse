"""Sprint 5 · V2-6-1 — Race Prediction (DARP) UI Blueprint.

참고 디자인: design/app-UI/race_prediction.html
"""
from __future__ import annotations
import json
import sqlite3
from flask import Blueprint, request
from src.web.helpers import (
    html_page, bottom_nav, no_data_card, fmt_pace, fmt_duration, db_path,
    metric_row, svg_semicircle_gauge,
)

race_bp = Blueprint("race", __name__)

DISTANCES = [
    ("5K", 5.0, "🏃"),
    ("10K", 10.0, "🏃"),
    ("하프마라톤", 21.0975, "🏃"),
    ("마라톤", 42.195, "🏃"),
    ("커스텀", 0, "⚙️"),
]



def _safe_json(raw):
    if not raw:
        return {}
    try:
        return json.loads(raw) if isinstance(raw, str) else raw
    except (json.JSONDecodeError, TypeError):
        return {}


def _load_metric(conn, name):
    cur = conn.execute(
        "SELECT metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name=? ORDER BY date DESC LIMIT 1", (name,))
    row = cur.fetchone()
    if not row:
        return None, {}
    return row[0], _safe_json(row[1])


def _load_darp(conn, km):
    val, mj = _load_metric(conn, f"darp_{km}")
    if val is None:
        val, mj = _load_metric(conn, "darp_half")
    return val, mj


def _render_distance_selector(active_km):
    html = '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:12px;margin:20px 0">'
    for name, km, icon in DISTANCES:
        border = "border:2px solid #00d4ff;background:rgba(0,212,255,0.1)" if km == active_km else "border:2px solid transparent"
        href = f"/race?distance={km}" if km > 0 else "/race?distance=0"
        html += (
            f'<a href="{href}" style="text-decoration:none;color:#fff;{border};'
            f'background:rgba(255,255,255,0.1);border-radius:16px;padding:16px;text-align:center;display:block">'
            f'<div style="font-size:32px;margin-bottom:8px">{icon}</div>'
            f'<div style="font-size:14px;font-weight:600">{name}</div>'
            f'<div style="font-size:12px;color:rgba(255,255,255,0.6)">{km}km</div></a>'
        )
    html += '</div>'
    return html


def _render_prediction_card(darp_val, darp_json, pace_sec):
    if darp_val is None:
        return no_data_card("DARP 예측", "데이터 수집 중입니다")
    time_str = fmt_duration(int(darp_val))
    pace_str = fmt_pace(pace_sec) if pace_sec else "-"
    splits = darp_json.get("splits", {})
    html = (
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));'
        'border-radius:24px;padding:32px;margin:20px 0;border:1px solid rgba(0,212,255,0.3);text-align:center">'
        '<div style="font-size:16px;color:rgba(255,255,255,0.7);margin-bottom:16px">예상 완료 시간</div>'
        f'<div style="font-size:48px;font-weight:bold;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        f'-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:16px 0">{time_str}</div>'
        f'<div style="font-size:20px;color:rgba(255,255,255,0.8);margin-bottom:24px">평균 페이스: {pace_str}/km</div>'
    )
    if splits:
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-top:24px">'
        for label, sval in splits.items():
            html += (
                f'<div style="background:rgba(0,0,0,0.3);border-radius:16px;padding:16px">'
                f'<div style="font-size:12px;color:rgba(255,255,255,0.7)">{label}</div>'
                f'<div style="font-size:24px;font-weight:bold;color:#00ff88;margin:8px 0">{fmt_duration(int(sval))}</div></div>'
            )
        html += '</div>'
    html += '</div>'
    return html


def _render_di_card(di_val, di_json):
    if di_val is None:
        return no_data_card("내구성 지수 (DI)", "90분+ 세션 데이터 필요")
    score = min(100, max(0, int(di_val)))
    pct = score
    color = "#00ff88" if score >= 70 else "#ffaa00" if score >= 40 else "#ff4444"
    desc = di_json.get("description", "")
    html = (
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:24px;margin:20px 0">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
        '<div style="font-size:18px;display:flex;align-items:center;gap:10px">'
        '<span>💪</span><span>내구성 지수 (DI)</span></div>'
        f'<div style="background:rgba({",".join(str(int(color[i:i+2],16)) for i in (1,3,5))},0.2);'
        f'color:{color};padding:8px 16px;border-radius:20px;font-size:16px;font-weight:bold">{score}/100</div></div>'
        f'<div style="height:24px;background:linear-gradient(90deg,'
        f'rgba(255,68,68,0.3) 0%,rgba(255,170,0,0.3) 40%,rgba(0,255,136,0.3) 70%,rgba(0,255,136,0.3) 100%);'
        f'border-radius:12px;position:relative;margin-bottom:16px">'
        f'<div style="position:absolute;top:-4px;left:{pct}%;width:4px;height:32px;'
        f'background:#fff;border-radius:2px"></div></div>'
        '<div style="display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,0.6)">'
        '<span>부족</span><span>양호</span><span>우수</span></div>'
    )
    if desc:
        html += f'<p style="margin-top:16px;font-size:14px;color:rgba(255,255,255,0.7)">{desc}</p>'
    html += '</div>'
    return html


def _render_pace_strategy(darp_json):
    segments = darp_json.get("pace_segments", [])
    if not segments:
        return ""
    html = (
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:24px;margin:20px 0">'
        '<div style="font-size:18px;margin-bottom:20px;display:flex;align-items:center;gap:10px">'
        '<span style="width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);border-radius:2px;display:inline-block"></span>'
        '페이스 전략</div><div style="display:flex;flex-direction:column;gap:16px">'
    )
    for seg in segments:
        rng = seg.get("range", "")
        pace = seg.get("pace", 0)
        level = seg.get("level", "green")
        colors = {"green": "#00ff88,#00aa88", "yellow": "#ffaa00,#cc8800", "red": "#ff4444,#cc3333"}
        bg = colors.get(level, colors["green"])
        pace_str = fmt_pace(pace) if pace else "-"
        html += (
            f'<div style="display:flex;align-items:center;gap:16px">'
            f'<div style="width:80px;font-size:14px;color:rgba(255,255,255,0.7)">{rng}</div>'
            f'<div style="flex:1;height:40px;background:rgba(255,255,255,0.1);border-radius:8px;overflow:hidden">'
            f'<div style="height:100%;width:100%;background:linear-gradient(90deg,{bg});border-radius:8px;'
            f'display:flex;align-items:center;padding:0 12px;font-size:14px;font-weight:600">{pace_str}/km</div>'
            f'</div></div>'
        )
    html += '</div></div>'
    return html


def _render_htw_card(darp_json):
    prob = darp_json.get("htw_probability")
    if prob is None:
        return ""
    desc = darp_json.get("htw_description", "")
    html = (
        '<div style="background:linear-gradient(135deg,rgba(255,68,68,0.1),rgba(255,170,0,0.1));'
        'border-radius:20px;padding:24px;margin:20px 0;border:1px solid rgba(255,68,68,0.3)">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:16px">'
        '<div style="font-size:18px;font-weight:bold;color:#ff4444">⚠️ 히팅 더 월 위험</div>'
        f'<div style="background:rgba(255,68,68,0.2);color:#ff4444;padding:8px 16px;'
        f'border-radius:20px;font-size:18px;font-weight:bold">{prob}%</div></div>'
    )
    if desc:
        html += f'<div style="font-size:14px;color:rgba(255,255,255,0.8);line-height:1.6">{desc}</div>'
    html += '</div>'
    return html


def _render_training_adjust(darp_json):
    tips = darp_json.get("training_tips", "")
    if not tips:
        return ""
    html = (
        '<div style="background:rgba(0,212,255,0.1);border-radius:20px;padding:24px;margin:20px 0;'
        'border:1px solid rgba(0,212,255,0.3)">'
        '<div style="font-size:18px;margin-bottom:16px">🎯 훈련 플랜 조정 권장</div>'
        f'<div style="font-size:14px;color:rgba(255,255,255,0.8);line-height:1.6;margin-bottom:16px">{tips}</div>'
        '<button disabled style="background:linear-gradient(135deg,#00d4ff,#00ff88);border:none;color:#fff;'
        'padding:12px 24px;border-radius:24px;font-size:14px;font-weight:600;opacity:0.5;cursor:not-allowed" '
        'title="훈련 계획 기능 준비 중">훈련 플랜에 반영하기</button></div>'
    )
    return html


@race_bp.route("/race")
def race_page():
    dist_param = request.args.get("distance", "21.0975")
    try:
        active_km = float(dist_param)
    except (ValueError, TypeError):
        active_km = 21.0975

    dbp = db_path()
    if not dbp:
        body = no_data_card("레이스 예측", "데이터베이스를 찾을 수 없습니다")
        return html_page("레이스 예측", body + bottom_nav("report"))

    conn = sqlite3.connect(dbp)
    try:
        darp_val, darp_json = _load_darp(conn, active_km)
        di_val, di_json = _load_di(conn)
        pace_sec = darp_json.get("avg_pace_sec")
        body = (
            '<div style="max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px">'
            '<div style="display:flex;align-items:center;padding:20px 0;'
            'border-bottom:1px solid rgba(255,255,255,0.1)">'
            '<span style="font-size:20px;font-weight:bold">레이스 예측 (DARP)</span></div>'
            + _render_distance_selector(active_km)
            + _render_prediction_card(darp_val, darp_json, pace_sec)
            + _render_di_card(di_val, di_json)
            + _render_pace_strategy(darp_json)
            + _render_htw_card(darp_json)
            + _render_training_adjust(darp_json)
            + '</div>'
        )
    finally:
        conn.close()

    return html_page("레이스 예측", body + bottom_nav("report"))


def _load_di(conn):
    return _load_metric(conn, "di")
