"""통합 대시보드 뷰 — Flask Blueprint.

/dashboard
  - UTRS 반원 게이지 + 하위 요인 표시
  - CIRS 반원 게이지 + 경고 배너 (CIRS > 50/75)
  - RMR 레이더 차트 (5축, 3개월 전 비교 오버레이)
  - PMC 차트 (Chart.js, ATL/CTL/TSB 60일)
  - 최근 활동 목록 (FEARP/RelativeEffort 배지)
"""
from __future__ import annotations

import html as _html
import json
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, redirect, url_for

from .helpers import (
    bottom_nav,
    db_path,
    fmt_duration,
    fmt_pace,
    html_page,
    metric_row,
    no_data_card,
    safe_str,
    svg_radar_chart,
    svg_semicircle_gauge,
)

dashboard_bp = Blueprint("dashboard", __name__)

# ── 색상 상수 ───────────────────────────────────────────────────────────────
_UTRS_COLORS = [(0, "#e53935"), (40, "#fb8c00"), (60, "#43a047"), (80, "#00acc1")]
_CIRS_COLORS = [(0, "#43a047"), (20, "#fb8c00"), (50, "#ef6c00"), (75, "#e53935")]


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
    """ATL/CTL/TSB 시계열 (일별)."""
    td = date.fromisoformat(end_date)
    start = (td - timedelta(days=days - 1)).isoformat()
    rows = conn.execute(
        """SELECT date, ctl, atl, tsb FROM daily_fitness
           WHERE date BETWEEN ? AND ?
           ORDER BY date ASC""",
        (start, end_date),
    ).fetchall()
    return [{"date": r[0], "ctl": r[1], "atl": r[2], "tsb": r[3]} for r in rows]


def _load_recent_activities(conn: sqlite3.Connection, limit: int = 5) -> list[dict]:
    """최근 활동 + FEARP / RelativeEffort 배지용 데이터."""
    rows = conn.execute(
        """SELECT a.id, a.start_time, a.activity_type, a.distance_km,
                  a.duration_sec, a.avg_pace_sec_km, a.avg_hr
           FROM v_canonical_activities a
           WHERE a.activity_type = 'running'
           ORDER BY a.start_time DESC
           LIMIT ?""",
        (limit,),
    ).fetchall()

    result = []
    for r in rows:
        act_id, start_time, act_type, dist, dur, pace, hr = r
        activity_date = str(start_time)[:10]

        fearp_row = conn.execute(
            """SELECT metric_value FROM computed_metrics
               WHERE activity_id = ? AND metric_name = 'FEARP' LIMIT 1""",
            (act_id,),
        ).fetchone()
        re_row = conn.execute(
            """SELECT metric_value FROM computed_metrics
               WHERE activity_id = ? AND metric_name = 'RelativeEffort' LIMIT 1""",
            (act_id,),
        ).fetchone()

        result.append({
            "id": act_id,
            "start_time": start_time,
            "date": activity_date,
            "distance_km": dist,
            "duration_sec": dur,
            "avg_pace_sec_km": pace,
            "avg_hr": hr,
            "fearp": float(fearp_row[0]) if fearp_row and fearp_row[0] else None,
            "relative_effort": float(re_row[0]) if re_row and re_row[0] else None,
        })
    return result


# ── 렌더링 헬퍼 ─────────────────────────────────────────────────────────────

def _render_cirs_banner(cirs: float) -> str:
    if cirs >= 75:
        return (
            "<div style='background:#fdecea;color:#c62828;border-left:4px solid #e53935;"
            "padding:0.7rem 1rem;border-radius:6px;margin-bottom:1rem;'>"
            f"⚠️ <strong>부상 위험 (CIRS {cirs:.0f})</strong> — 훈련 강도를 즉시 낮추세요."
            "</div>"
        )
    if cirs >= 50:
        return (
            "<div style='background:#fff3e0;color:#e65100;border-left:4px solid #fb8c00;"
            "padding:0.7rem 1rem;border-radius:6px;margin-bottom:1rem;'>"
            f"⚡ <strong>부상 주의 (CIRS {cirs:.0f})</strong> — 회복·부하 관리가 필요합니다."
            "</div>"
        )
    return ""


def _render_utrs_factors(utrs_json: dict) -> str:
    """UTRS 하위 요인 6개 소형 표시."""
    factor_labels = {
        "sleep": "수면점수",
        "hrv": "HRV",
        "tsb_norm": "TSB",
        "rhr": "안정심박",
        "consistency": "수면일관성",
    }
    available = utrs_json.get("available_factors", [])
    rows = []
    for key, label in factor_labels.items():
        val = utrs_json.get(key)
        val_str = f"{val:.0f}" if val is not None else "—"
        active = "sleep" in key or key in available or key.replace("_norm", "") in available
        opacity = "1" if active else "0.45"
        rows.append(
            f"<div style='flex:1;min-width:80px;text-align:center;opacity:{opacity};'>"
            f"<div style='font-size:1.1rem;font-weight:700;'>{_html.escape(val_str)}</div>"
            f"<div style='font-size:0.75rem;color:var(--muted);'>{_html.escape(label)}</div>"
            f"</div>"
        )
    return (
        "<div style='display:flex;flex-wrap:wrap;gap:0.5rem;margin-top:0.8rem;'>"
        + "".join(rows)
        + "</div>"
    )


def _render_gauge_card(
    title: str,
    value: float | None,
    max_value: float,
    color_stops: list,
    subtitle: str = "",
    extra_html: str = "",
    grade_label: str = "",
) -> str:
    if value is None:
        return no_data_card(title)
    gauge = svg_semicircle_gauge(value, max_value, grade_label, color_stops, width=200)
    return (
        f"<div class='card' style='text-align:center;'>"
        f"<h2 style='margin-bottom:0.3rem;font-size:1rem;'>{_html.escape(title)}</h2>"
        f"<p class='muted' style='margin:0 0 0.5rem;font-size:0.8rem;'>{_html.escape(subtitle)}</p>"
        f"{gauge}"
        f"{extra_html}"
        f"</div>"
    )


def _render_rmr_card(axes: dict, compare_axes: dict | None = None) -> str:
    if not axes:
        return no_data_card("RMR 러너 성숙도 레이더")
    radar = svg_radar_chart(axes, max_value=100.0, compare_axes=compare_axes, width=260)
    overall = sum(axes.values()) / len(axes) if axes else 0
    compare_note = ""
    if compare_axes:
        compare_note = (
            "<p class='muted' style='margin:0.3rem 0 0;font-size:0.8rem;'>"
            "🟡 3개월 전 비교</p>"
        )
    return (
        "<div class='card' style='text-align:center;'>"
        "<h2 style='margin-bottom:0.3rem;font-size:1rem;'>RMR 러너 성숙도</h2>"
        f"<p class='muted' style='margin:0 0 0.5rem;font-size:0.8rem;'>종합 {overall:.1f}점</p>"
        f"{radar}"
        f"{compare_note}"
        "</div>"
    )


def _render_pmc_chart(pmc_data: list[dict]) -> str:
    """ECharts PMC 차트 (ATL/CTL/TSB, TSB 위험구간 배경 포함)."""
    if not pmc_data:
        return no_data_card("PMC 차트 (CTL/ATL/TSB)", "훈련 데이터 동기화 후 표시됩니다")

    labels = [r["date"] for r in pmc_data]
    ctl = [round(r["ctl"] or 0, 1) for r in pmc_data]
    atl = [round(r["atl"] or 0, 1) for r in pmc_data]
    tsb = [round(r["tsb"] or 0, 1) for r in pmc_data]

    labels_json = json.dumps(labels)
    ctl_json = json.dumps(ctl)
    atl_json = json.dumps(atl)
    tsb_json = json.dumps(tsb)

    # TSB 위험구간 markArea 계산 (< -20 주황, < -30 빨강)
    return f"""
<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.8rem;'>PMC 훈련 부하 차트</h2>
  <div id='pmcChart' style='height:240px;'></div>
  <p class='muted' style='font-size:0.78rem;margin:0.4rem 0 0;'>
    CTL(만성부하) · ATL(급성부하) · TSB(훈련 스트레스 균형) — 최근 60일
    &nbsp;|&nbsp; <span style='color:#ffaa00'>■</span> TSB&lt;-20 주의
    &nbsp;<span style='color:#ff4444'>■</span> TSB&lt;-30 위험
  </p>
</div>
<script>
(function() {{
  var el = document.getElementById('pmcChart');
  if (!el || typeof echarts === 'undefined') return;
  var chart = echarts.init(el, 'dark', {{backgroundColor: 'transparent'}});
  var labels = {labels_json};
  var shortLabels = labels.map(function(d) {{ return d.slice(5); }});
  var ctlData = {ctl_json};
  var atlData = {atl_json};
  var tsbData = {tsb_json};

  // TSB markArea: 위험구간 배경 (연속 구간 병합)
  var warningAreas = [], dangerAreas = [];
  var wStart = null, dStart = null;
  for (var i = 0; i < tsbData.length; i++) {{
    var v = tsbData[i];
    if (v < -30) {{
      if (dStart === null) dStart = i;
      if (wStart === null) wStart = i;
    }} else if (v < -20) {{
      if (wStart === null) wStart = i;
      if (dStart !== null) {{ dangerAreas.push([{{xAxis: shortLabels[dStart]}}, {{xAxis: shortLabels[i-1]}}]]); dStart = null; }}
    }} else {{
      if (wStart !== null) {{ warningAreas.push([{{xAxis: shortLabels[wStart]}}, {{xAxis: shortLabels[i-1]}}]]); wStart = null; }}
      if (dStart !== null) {{ dangerAreas.push([{{xAxis: shortLabels[dStart]}}, {{xAxis: shortLabels[i-1]}}]]); dStart = null; }}
    }}
  }}
  if (wStart !== null) warningAreas.push([{{xAxis: shortLabels[wStart]}}, {{xAxis: shortLabels[shortLabels.length-1]}}]);
  if (dStart !== null) dangerAreas.push([{{xAxis: shortLabels[dStart]}}, {{xAxis: shortLabels[shortLabels.length-1]}}]);

  var option = {{
    backgroundColor: 'transparent',
    tooltip: {{ trigger: 'axis', axisPointer: {{ type: 'cross' }},
      formatter: function(params) {{
        var s = params[0].axisValue + '<br>';
        params.forEach(function(p) {{ s += p.marker + p.seriesName + ': ' + (p.value==null?'—':p.value.toFixed(1)) + '<br>'; }});
        return s;
      }}
    }},
    legend: {{ top: 4, textStyle: {{ color: 'rgba(255,255,255,0.7)', fontSize: 11 }} }},
    grid: {{ left: 48, right: 48, bottom: 30, top: 36 }},
    xAxis: {{ type: 'category', data: shortLabels, axisLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.2)' }} }},
      axisLabel: {{ color: 'rgba(255,255,255,0.5)', fontSize: 10, interval: Math.floor(shortLabels.length/8) }} }},
    yAxis: [
      {{ type: 'value', name: 'CTL/ATL', nameTextStyle: {{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }},
        splitLine: {{ lineStyle: {{ color: 'rgba(255,255,255,0.08)' }} }},
        axisLabel: {{ color: 'rgba(255,255,255,0.5)', fontSize: 10 }} }},
      {{ type: 'value', name: 'TSB', nameTextStyle: {{ color: '#ffaa00', fontSize: 10 }},
        position: 'right', splitLine: {{ show: false }},
        axisLabel: {{ color: '#ffaa00', fontSize: 10 }} }}
    ],
    series: [
      {{ name: 'CTL', type: 'line', data: ctlData, smooth: true, symbol: 'none',
        lineStyle: {{ color: '#00d4ff', width: 2 }},
        areaStyle: {{ color: 'rgba(0,212,255,0.08)' }}, yAxisIndex: 0 }},
      {{ name: 'ATL', type: 'line', data: atlData, smooth: true, symbol: 'none',
        lineStyle: {{ color: '#00ff88', width: 2 }},
        areaStyle: {{ color: 'rgba(0,255,136,0.08)' }}, yAxisIndex: 0 }},
      {{ name: 'TSB', type: 'line', data: tsbData, smooth: true, symbol: 'none',
        lineStyle: {{ color: '#ffaa00', width: 1.5, type: 'dashed' }},
        yAxisIndex: 1,
        markArea: {{ silent: true, data: [
          ...warningAreas.map(function(a) {{ return [{{xAxis: a[0].xAxis, itemStyle: {{color:'rgba(255,170,0,0.12)'}}}}, {{xAxis: a[1].xAxis}}]; }}),
          ...dangerAreas.map(function(a) {{ return [{{xAxis: a[0].xAxis, itemStyle: {{color:'rgba(255,68,68,0.18)'}}}}, {{xAxis: a[1].xAxis}}]; }})
        ] }}
      }}
    ]
  }};
  chart.setOption(option);
  window.addEventListener('resize', function() {{ chart.resize(); }});
}})();
</script>"""


def _render_activity_list(activities: list[dict]) -> str:
    """최근 활동 카드 목록."""
    if not activities:
        return no_data_card("최근 활동", "동기화 후 표시됩니다")

    items = []
    for act in activities:
        dist = f"{act['distance_km']:.1f} km" if act["distance_km"] else "—"
        dur = fmt_duration(act["duration_sec"])
        pace = fmt_pace(act["avg_pace_sec_km"])
        hr = f"{act['avg_hr']} bpm" if act["avg_hr"] else "—"

        badges = []
        if act["fearp"] is not None:
            badges.append(
                f"<span style='background:#e3f2fd;color:#1565c0;border-radius:12px;"
                f"padding:0.15rem 0.55rem;font-size:0.78rem;'>FEARP {fmt_pace(act['fearp'])}</span>"
            )
        if act["relative_effort"] is not None:
            badges.append(
                f"<span style='background:#f3e5f5;color:#6a1b9a;border-radius:12px;"
                f"padding:0.15rem 0.55rem;font-size:0.78rem;'>RE {act['relative_effort']:.0f}</span>"
            )

        badge_html = " ".join(badges) if badges else ""
        act_id = act["id"]
        date_str = act["date"]

        items.append(
            f"<a href='/activity?id={act_id}' style='text-decoration:none;color:inherit;'>"
            f"<div class='card' style='display:flex;align-items:center;gap:1rem;"
            f"padding:0.8rem 1rem;margin:0.5rem 0;transition:background 0.15s;'>"
            f"<div style='font-size:1.6rem;'>🏃</div>"
            f"<div style='flex:1;min-width:0;'>"
            f"<div style='font-weight:600;font-size:0.95rem;'>{_html.escape(date_str)} · {_html.escape(dist)}</div>"
            f"<div class='muted' style='font-size:0.82rem;margin-top:0.15rem;'>"
            f"{_html.escape(dur)} · {_html.escape(pace)}/km · ♥ {_html.escape(hr)}</div>"
            f"<div style='margin-top:0.3rem;'>{badge_html}</div>"
            f"</div>"
            f"<div style='color:var(--muted);font-size:1.1rem;'>›</div>"
            f"</div>"
            f"</a>"
        )
    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.5rem;'>최근 활동</h2>"
        + "".join(items)
        + "</div>"
    )


# ── 메인 뷰 ─────────────────────────────────────────────────────────────────

@dashboard_bp.get("/dashboard")
def dashboard():
    db = db_path()
    if not db.exists():
        body = (
            "<div class='card'>"
            "<p>DB가 초기화되지 않았습니다.</p>"
            "<p><code>python src/db_setup.py</code> 후 동기화하세요.</p>"
            "</div>"
        )
        return html_page("대시보드", body, active_tab="dashboard")

    today = date.today().isoformat()
    three_months_ago = (date.today() - timedelta(days=90)).isoformat()

    with sqlite3.connect(str(db)) as conn:
        # 메트릭 조회
        utrs_val = _load_metric(conn, today, "UTRS")
        utrs_json = _load_metric_json(conn, today, "UTRS") or {}
        cirs_val = _load_metric(conn, today, "CIRS")
        cirs_json = _load_metric_json(conn, today, "CIRS") or {}
        rmr_json = _load_metric_json(conn, today, "RMR") or {}
        rmr_old_json = _load_metric_json(conn, three_months_ago, "RMR") or {}
        pmc_data = _load_pmc_data(conn, today, days=60)
        recent_acts = _load_recent_activities(conn, limit=5)

    # ── CIRS 경고 배너
    banner = _render_cirs_banner(cirs_val or 0.0) if cirs_val is not None else ""

    # ── UTRS 게이지
    utrs_grade_map = {"rest": "휴식", "light": "경량", "moderate": "보통", "optimal": "최적"}
    utrs_grade_str = utrs_grade_map.get(utrs_json.get("grade", ""), "")
    utrs_factors_html = _render_utrs_factors(utrs_json) if utrs_json else ""
    utrs_card = _render_gauge_card(
        "UTRS 훈련 준비도",
        utrs_val,
        100.0,
        _UTRS_COLORS,
        subtitle="통합 훈련 준비도 지수 (0-100)",
        extra_html=utrs_factors_html,
        grade_label=utrs_grade_str,
    )

    # ── CIRS 게이지
    cirs_grade_map = {"safe": "안전", "caution": "주의", "warning": "경고", "danger": "위험"}
    cirs_grade_str = cirs_grade_map.get(cirs_json.get("grade", ""), "")
    cirs_factors_html = ""
    if cirs_json:
        cirs_factors_html = (
            "<div style='font-size:0.8rem;color:var(--muted);margin-top:0.5rem;text-align:left;'>"
            + metric_row("ACWR 위험", f"{cirs_json.get('acwr_risk', 0):.0f}")
            + metric_row("단조로움 위험", f"{cirs_json.get('mono_risk', 0):.0f}")
            + metric_row("급증 위험", f"{cirs_json.get('spike_risk', 0):.0f}")
            + ("" if not cirs_json.get("has_asym_data") else metric_row("비대칭 위험", f"{cirs_json.get('asym_risk', 0):.1f}"))
            + "</div>"
        )
    cirs_card = _render_gauge_card(
        "CIRS 부상 위험도",
        cirs_val,
        100.0,
        _CIRS_COLORS,
        subtitle="복합 부상 위험 점수 (낮을수록 안전)",
        extra_html=cirs_factors_html,
        grade_label=cirs_grade_str,
    )

    # ── RMR 레이더
    rmr_axes = rmr_json.get("axes") if rmr_json else None
    rmr_compare = rmr_old_json.get("axes") if rmr_old_json else None
    rmr_card = _render_rmr_card(rmr_axes or {}, compare_axes=rmr_compare or None)

    # ── PMC 차트
    pmc_chart = _render_pmc_chart(pmc_data)

    # ── 활동 목록
    activity_list = _render_activity_list(recent_acts)

    body = f"""
{banner}
<div class='cards-row' style='align-items:stretch;'>
  {utrs_card}
  {cirs_card}
  {rmr_card}
</div>
{pmc_chart}
{activity_list}
"""
    return html_page("대시보드", body, active_tab="dashboard")


