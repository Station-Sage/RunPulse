"""Sprint 5 · V2-6-1 — Race Prediction (DARP) UI Blueprint.

참고 디자인: design/app-UI/race_prediction.html
"""
from __future__ import annotations
import json
import sqlite3
from flask import Blueprint, request
from src.web.helpers import (
    html_page, no_data_card, fmt_pace, fmt_duration, db_path,
    metric_row, render_sub_nav, svg_semicircle_gauge,
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


_KM_TO_DARP_KEY = {
    5.0: "DARP_5k", 10.0: "DARP_10k",
    21.0975: "DARP_half", 42.195: "DARP_full",
}


def _load_darp(conn, km):
    key = _KM_TO_DARP_KEY.get(km, f"DARP_{km}")
    val, mj = _load_metric(conn, key)
    if val is None:
        val, mj = _load_metric(conn, "DARP_half")
    return val, mj


def _render_distance_selector(active_km):
    html = (
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:24px;margin:20px 0">'
        '<div style="font-size:16px;margin-bottom:16px;color:rgba(255,255,255,0.7)">목표 레이스 선택</div>'
        '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:12px">'
    )
    for name, km, icon in DISTANCES:
        active = "border:2px solid #00d4ff;background:rgba(0,212,255,0.1)" if km == active_km else "border:2px solid transparent"
        href = f"/race?distance={km}" if km > 0 else "/race?distance=0"
        dist_label = f"{km}km" if km > 0 else "직접 입력"
        html += (
            f'<a href="{href}" style="text-decoration:none;color:#fff;{active};'
            f'background:rgba(255,255,255,0.1);border-radius:16px;padding:16px;text-align:center;'
            f'display:block;transition:all 0.3s">'
            f'<div style="font-size:32px;margin-bottom:8px">{icon}</div>'
            f'<div style="font-size:14px;font-weight:600">{name}</div>'
            f'<div style="font-size:12px;color:rgba(255,255,255,0.6)">{dist_label}</div></a>'
        )
    html += '</div></div>'
    return html


def _split_color(idx: int, total: int) -> str:
    """스플릿 인덱스에 따라 색상 지정 (앞쪽=green, 뒤쪽=yellow/orange)."""
    if total <= 1:
        return "#00ff88"
    ratio = idx / (total - 1)
    return "#00ff88" if ratio < 0.5 else "#ffaa00" if ratio < 0.8 else "#ff8844"


def _render_prediction_card(darp_val, darp_json, pace_sec):
    if darp_val is None:
        return no_data_card("DARP 예측", "데이터 수집 중입니다")
    time_str = fmt_duration(int(darp_val))
    pace_str = fmt_pace(pace_sec) if pace_sec else "-"
    splits = darp_json.get("splits", {})
    vdot = darp_json.get("vdot")
    percentile = darp_json.get("percentile")

    html = (
        '<div style="background:linear-gradient(135deg,rgba(0,212,255,0.1),rgba(0,255,136,0.1));'
        'border-radius:24px;padding:32px;margin:20px 0;border:1px solid rgba(0,212,255,0.3);text-align:center">'
        '<div style="font-size:16px;color:rgba(255,255,255,0.7);margin-bottom:16px">예상 완료 시간</div>'
        f'<div style="font-size:48px;font-weight:bold;background:linear-gradient(135deg,#00d4ff,#00ff88);'
        f'-webkit-background-clip:text;-webkit-text-fill-color:transparent;margin:16px 0">{time_str}</div>'
        f'<div style="font-size:20px;color:rgba(255,255,255,0.8);margin-bottom:24px">평균 페이스: {pace_str}/km</div>'
    )

    # 스플릿 + 추가 정보 (VDOT, 예상 순위)
    stat_items = []
    if splits:
        for i, (label, sval) in enumerate(splits.items()):
            color = _split_color(i, len(splits))
            stat_items.append((label, fmt_duration(int(sval)), color))
    if vdot is not None:
        stat_items.append(("VDOT", f"{float(vdot):.1f}", "#00d4ff"))
    if percentile is not None:
        stat_items.append(("예상 순위", f"상위 {int(percentile)}%", "#00d4ff"))

    if stat_items:
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:16px;margin-top:24px">'
        for label, val, color in stat_items:
            html += (
                f'<div style="background:rgba(0,0,0,0.3);border-radius:16px;padding:20px">'
                f'<div style="font-size:12px;color:rgba(255,255,255,0.7)">{label}</div>'
                f'<div style="font-size:24px;font-weight:bold;color:{color};margin:8px 0">{val}</div></div>'
            )
        html += '</div>'
    html += '</div>'
    return html


def _render_di_card(di_val, di_json):
    if di_val is None:
        return no_data_card("내구성 지수 (DI)", "90분+ 세션 데이터 필요 (8주 3회 이상)")
    score = min(100, max(0, int(di_val)))
    color = "#00ff88" if score >= 70 else "#ffaa00" if score >= 40 else "#ff4444"
    sessions = di_json.get("sessions_analyzed", "?")
    grade = "우수" if score >= 70 else "양호" if score >= 40 else "부족"
    desc = di_json.get("description", "")
    if not desc:
        desc = (
            f"최근 분석된 {sessions}개 장거리 세션 기반. "
            f"내구성 등급: <strong>{grade}</strong>."
        )
    html = (
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:24px;margin:20px 0">'
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:20px">'
        '<div style="font-size:18px;display:flex;align-items:center;gap:10px">'
        '<span>💪</span><span>내구성 지수 (DI)</span></div>'
        f'<div style="background:rgba(255,255,255,0.1);color:{color};'
        f'padding:8px 16px;border-radius:20px;font-size:16px;font-weight:bold">{score}/100</div></div>'
        # 3-zone gradient bar (참고 디자인 매칭)
        f'<div style="height:24px;background:linear-gradient(90deg,'
        f'rgba(255,68,68,0.3) 0%,rgba(255,170,0,0.3) 40%,rgba(0,255,136,0.3) 70%,rgba(0,255,136,0.3) 100%);'
        f'border-radius:12px;position:relative;margin-bottom:12px">'
        f'<div style="position:absolute;top:-6px;left:calc({score}% - 2px);width:4px;height:36px;'
        f'background:#fff;border-radius:2px;box-shadow:0 0 8px rgba(255,255,255,0.5)"></div></div>'
        '<div style="display:flex;justify-content:space-between;font-size:12px;color:rgba(255,255,255,0.6)">'
        '<span>부족</span><span>양호</span><span>우수</span></div>'
        f'<p style="margin-top:16px;font-size:14px;color:rgba(255,255,255,0.7)">{desc}</p>'
        '</div>'
    )
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
    if not dbp or not dbp.exists():
        body = render_sub_nav("race") + no_data_card("레이스 예측", "데이터 수집 중입니다. 동기화 후 확인하세요.")
        return html_page("레이스 예측", body, active_tab="report")

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            darp_val, darp_json = _load_darp(conn, active_km)
            di_val, di_json = _load_di(conn)
            pace_sec = darp_json.get("avg_pace_sec") if darp_json else None
            darp_key = _KM_TO_DARP_KEY.get(active_km, f"DARP_{active_km}")
            history = _load_prediction_history(conn, darp_key)
            body = (
                render_sub_nav("race")
                + '<div style="max-width:1200px;margin:0 auto;padding:20px;padding-bottom:100px">'
                '<div style="display:flex;align-items:center;padding:20px 0;'
                'border-bottom:1px solid rgba(255,255,255,0.1)">'
                '<span style="font-size:20px;font-weight:bold">레이스 예측 (DARP)</span></div>'
                + _render_distance_selector(active_km)
                + _render_prediction_card(darp_val, darp_json, pace_sec)
                + _render_di_card(di_val, di_json)
                + _render_pace_strategy(darp_json)
                + _render_htw_card(darp_json)
                + _render_training_adjust(darp_json)
                + _render_prediction_history(history)
                + '</div>'
            )
        finally:
            conn.close()
    except Exception as exc:
        import html as _html
        body = (
            "<div class='card'><p style='color:var(--red)'>오류가 발생했습니다: "
            + _html.escape(str(exc))
            + "</p><p class='muted'>데이터 수집 중이거나 DB에 문제가 있을 수 있습니다.</p></div>"
        )

    return html_page("레이스 예측", body, active_tab="report")


def _load_di(conn):
    return _load_metric(conn, "DI")


def _load_prediction_history(conn, key: str, limit: int = 10) -> list[dict]:
    """최근 DARP 예측 이력 로드."""
    rows = conn.execute(
        "SELECT date, metric_value, metric_json FROM computed_metrics "
        "WHERE metric_name=? ORDER BY date DESC LIMIT ?", (key, limit),
    ).fetchall()
    result = []
    for d, val, mj in rows:
        j = _safe_json(mj)
        result.append({"date": d, "time_sec": val, "pace": j.get("avg_pace_sec")})
    return result


def _render_prediction_history(history: list[dict]) -> str:
    """예측 이력 카드."""
    if not history:
        return ""
    rows_html = ""
    for h in history:
        t = fmt_duration(int(h["time_sec"])) if h["time_sec"] else "-"
        p = fmt_pace(h["pace"]) if h.get("pace") else "-"
        rows_html += (
            f"<tr><td style='padding:6px 10px;border-bottom:1px solid var(--row-border);'>{h['date']}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid var(--row-border);font-weight:600;color:#00d4ff;'>{t}</td>"
            f"<td style='padding:6px 10px;border-bottom:1px solid var(--row-border);'>{p}/km</td></tr>"
        )
    return (
        '<div style="background:rgba(255,255,255,0.05);border-radius:20px;padding:24px;margin:20px 0">'
        '<div style="font-size:18px;margin-bottom:16px;display:flex;align-items:center;gap:10px">'
        '<span style="width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);border-radius:2px;display:inline-block"></span>'
        '예측 이력</div>'
        '<div style="overflow-x:auto;">'
        '<table style="width:100%;border-collapse:collapse;font-size:0.85rem;">'
        '<thead><tr style="color:var(--muted);font-size:0.78rem;">'
        '<th style="text-align:left;padding:6px 10px;">날짜</th>'
        '<th style="text-align:left;padding:6px 10px;">예측 시간</th>'
        '<th style="text-align:left;padding:6px 10px;">평균 페이스</th>'
        '</tr></thead><tbody>'
        + rows_html
        + '</tbody></table></div></div>'
    )
