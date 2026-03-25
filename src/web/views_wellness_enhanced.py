"""웰니스 보강 — 기준선 밴드, 패턴 인사이트, 주간 비교, 미니차트.

views_wellness.py에서 호출되는 신규 섹션 렌더러.
"""
from __future__ import annotations

import json
import sqlite3

from .helpers import no_data_card, safe_str


# ── 데이터 로더 ──────────────────────────────────────────────────────────────

def load_wellness_14d(conn: sqlite3.Connection, date_str: str) -> list[dict]:
    """최근 14일 웰니스 데이터."""
    rows = conn.execute(
        "SELECT date, sleep_score, hrv_value, body_battery, stress_avg, resting_hr "
        "FROM daily_wellness WHERE source='garmin' AND date <= ? "
        "ORDER BY date DESC LIMIT 14",
        (date_str,),
    ).fetchall()
    return [{"date": r[0], "sleep": r[1], "hrv": r[2], "bb": r[3],
             "stress": r[4], "rhr": r[5]} for r in reversed(rows)]


def load_sleep_times(conn: sqlite3.Connection, date_str: str, days: int = 7) -> list[dict]:
    """최근 N일 취침/기상 시각 (daily_detail_metrics)."""
    try:
        rows = conn.execute(
            """SELECT d.date, d.metric_name, d.metric_value
               FROM daily_detail_metrics d
               WHERE d.date <= ? AND d.date >= date(?, '-' || ? || ' days')
                 AND d.metric_name IN ('sleep_start_timestamp', 'sleep_end_timestamp')
               ORDER BY d.date""",
            (date_str, date_str, days),
        ).fetchall()
    except Exception:
        return []
    by_date: dict = {}
    for d, name, val in rows:
        by_date.setdefault(d, {})[name] = val
    result = []
    for d in sorted(by_date):
        entry = by_date[d]
        result.append({
            "date": d,
            "start": entry.get("sleep_start_timestamp"),
            "end": entry.get("sleep_end_timestamp"),
        })
    return result


def load_hrv_baseline(conn: sqlite3.Connection, date_str: str) -> dict:
    """HRV 개인 기준선 (Garmin daily_detail_metrics)."""
    row = conn.execute(
        """SELECT metric_name, metric_value FROM daily_detail_metrics
           WHERE date = ? AND metric_name IN ('hrv_baseline_low', 'hrv_baseline_high')""",
        (date_str,),
    ).fetchall()
    return {r[0]: float(r[1]) for r in row if r[1] is not None}


def load_weekly_comparison(conn: sqlite3.Connection, date_str: str) -> dict:
    """이번 주 vs 지난 주 웰니스 평균 비교."""
    from datetime import date as dt, timedelta
    td = dt.fromisoformat(date_str)
    monday = td - timedelta(days=td.weekday())
    prev_monday = monday - timedelta(days=7)

    def _avg(start: str, end: str) -> dict:
        row = conn.execute(
            """SELECT AVG(sleep_score), AVG(hrv_value), AVG(body_battery),
                      AVG(stress_avg), AVG(resting_hr)
               FROM daily_wellness WHERE source='garmin' AND date BETWEEN ? AND ?""",
            (start, end),
        ).fetchone()
        if not row or row[0] is None:
            return {}
        return {"sleep": row[0], "hrv": row[1], "bb": row[2],
                "stress": row[3], "rhr": row[4]}

    this_week = _avg(monday.isoformat(), date_str)
    last_week = _avg(prev_monday.isoformat(), (monday - timedelta(days=1)).isoformat())
    return {"this": this_week, "last": last_week}


# ── 섹션 2: 핵심 지표 대시 ───────────────────────────────────────────────────

def render_metrics_dash(raw: dict, data_14d: list[dict], baseline: dict) -> str:
    """BB/수면/HRV/스트레스/안정심박 + 3일 추세 + 기준선 배지."""
    if not raw:
        return ""

    def _trend_3d(key: str) -> str:
        vals = [d.get(key) for d in data_14d[-3:] if d.get(key) is not None]
        if len(vals) < 2:
            return ""
        diff = vals[-1] - vals[0]
        if abs(diff) < 0.5:
            return "<span style='color:var(--muted);'>→</span>"
        arrow = "↑" if diff > 0 else "↓"
        # 스트레스/안정심박은 올라가면 나쁨
        bad_up = key in ("stress", "rhr")
        color = "var(--red)" if (diff > 0) == bad_up else "var(--green)"
        return f"<span style='color:{color};'>{arrow}</span>"

    # 14일 평균을 개인 기준선으로 사용 (HRV 외 항목)
    def _avg_14d(key: str) -> float | None:
        vals = [d.get(key) for d in data_14d if d.get(key) is not None]
        return sum(vals) / len(vals) if vals else None

    avg_bb = _avg_14d("bb")
    avg_sleep = _avg_14d("sleep")
    avg_stress = _avg_14d("stress")
    avg_rhr = _avg_14d("rhr")

    def _baseline_badge(key: str, value) -> str:
        if value is None:
            return ""
        if key == "hrv":
            lo = baseline.get("hrv_baseline_low")
            hi = baseline.get("hrv_baseline_high")
            if lo is not None and hi is not None:
                if value < lo:
                    return "<span style='color:var(--red);font-size:0.65rem;'>기준↓</span>"
                elif value > hi:
                    return "<span style='color:var(--green);font-size:0.65rem;'>기준↑</span>"
                return "<span style='color:var(--muted);font-size:0.65rem;'>기준내</span>"
        # BB/수면: 14일 평균 대비 (높을수록 좋음)
        if key == "bb" and avg_bb is not None:
            d = value - avg_bb
            if d < -10:
                return "<span style='color:var(--red);font-size:0.65rem;'>평균↓</span>"
            elif d > 10:
                return "<span style='color:var(--green);font-size:0.65rem;'>평균↑</span>"
        if key == "sleep" and avg_sleep is not None:
            d = value - avg_sleep
            if d < -10:
                return "<span style='color:var(--red);font-size:0.65rem;'>평균↓</span>"
            elif d > 10:
                return "<span style='color:var(--green);font-size:0.65rem;'>평균↑</span>"
        # 스트레스/안정심박: 높을수록 나쁨 (반전)
        if key == "stress" and avg_stress is not None:
            d = value - avg_stress
            if d > 10:
                return "<span style='color:var(--red);font-size:0.65rem;'>평균↑</span>"
            elif d < -10:
                return "<span style='color:var(--green);font-size:0.65rem;'>평균↓</span>"
        if key == "rhr" and avg_rhr is not None:
            d = value - avg_rhr
            if d > 5:
                return "<span style='color:var(--red);font-size:0.65rem;'>평균↑</span>"
            elif d < -5:
                return "<span style='color:var(--green);font-size:0.65rem;'>평균↓</span>"
        return ""

    items = [
        ("🔋", "BB", raw.get("body_battery"), "bb", "var(--orange)"),
        ("😴", "수면", raw.get("sleep_score"), "sleep", "var(--cyan)"),
        ("💓", "HRV", raw.get("hrv_value"), "hrv", "var(--green)"),
        ("😰", "스트레스", raw.get("stress_avg"), "stress", "var(--red)"),
        ("❤️", "안정심박", raw.get("resting_hr"), "rhr", "var(--muted)"),
    ]

    parts = []
    for icon, label, val, key, color in items:
        val_str = f"{val}" if val is not None else "—"
        trend = _trend_3d(key)
        bl_badge = _baseline_badge(key, val)
        parts.append(
            f"<div style='text-align:center;min-width:60px;'>"
            f"<div style='font-size:1rem;'>{icon}</div>"
            f"<div style='font-size:1.1rem;font-weight:700;color:{color};'>{val_str}</div>"
            f"<div style='font-size:0.65rem;color:var(--muted);'>{label}</div>"
            f"<div>{trend} {bl_badge}</div></div>"
        )

    return (
        "<div class='card' style='padding:0.6rem 0.8rem;'>"
        "<div style='display:flex;flex-wrap:wrap;gap:0.8rem;justify-content:space-around;'>"
        + "".join(parts) +
        "</div></div>"
    )


# ── 섹션 3: 7일 차트 + 기준선 밴드 ──────────────────────────────────────────

def render_7day_chart_enhanced(data: list[dict], baseline: dict,
                               outlier_points: str = "[]") -> str:
    """7일 웰니스 차트 + HRV 기준선 밴드 + 이상치 빨간 점."""
    if not data:
        return ""
    dates = [d["date"][-5:] for d in data]
    sleep = [d.get("sleep") for d in data]
    hrv = [d.get("hrv") for d in data]
    bb = [d.get("bb") for d in data]
    stress = [d.get("stress") for d in data]
    rhr = [d.get("rhr") for d in data]

    hrv_lo = baseline.get("hrv_baseline_low")
    hrv_hi = baseline.get("hrv_baseline_high")

    dj = json.dumps(dates)
    sj = json.dumps(sleep)
    hj = json.dumps(hrv)
    bj = json.dumps(bb)
    stj = json.dumps(stress)
    rj = json.dumps(rhr)

    # HRV 기준선 밴드 markArea
    band_js = ""
    if hrv_lo is not None and hrv_hi is not None:
        band_js = (
            f",markArea:{{silent:true,data:[[{{yAxis:{hrv_lo},"
            f"itemStyle:{{color:'rgba(0,255,136,0.08)'}}}},{{yAxis:{hrv_hi}}}]]}}"
        )

    return f"""<div class='card'>
  <h2 style='font-size:1rem;margin-bottom:0.5rem;'>7일 웰니스 트렌드</h2>
  <div id='wellness7dE' style='height:260px;'></div>
  <p class='muted' style='font-size:0.7rem;margin:0.3rem 0 0;'>
    녹색 밴드 = HRV 개인 기준선 범위{f" ({hrv_lo:.0f}–{hrv_hi:.0f}ms)" if hrv_lo else ""}
  </p>
</div>
<script>
(function(){{
  var el=document.getElementById('wellness7dE');
  if(!el||typeof echarts==='undefined') return;
  var c=echarts.init(el,'dark',{{backgroundColor:'transparent'}});
  c.setOption({{backgroundColor:'transparent',
    tooltip:{{trigger:'axis'}},
    legend:{{top:0,textStyle:{{color:'rgba(255,255,255,0.7)',fontSize:10}}}},
    grid:{{left:40,right:10,bottom:25,top:32}},
    xAxis:{{type:'category',data:{dj},axisLabel:{{color:'rgba(255,255,255,0.6)',fontSize:11}}}},
    yAxis:{{type:'value',splitLine:{{lineStyle:{{color:'rgba(255,255,255,0.08)'}}}},
      axisLabel:{{color:'rgba(255,255,255,0.6)',fontSize:11}}}},
    series:[
      {{name:'수면',type:'line',data:{sj},smooth:true,symbol:'none',lineStyle:{{color:'#00d4ff',width:2}}}},
      {{name:'HRV',type:'line',data:{hj},smooth:true,symbol:'circle',symbolSize:4,
        lineStyle:{{color:'#00ff88',width:2}},itemStyle:{{color:'#00ff88'}}{band_js},
        markPoint:{{data:{outlier_points},symbol:'circle',symbolSize:8,
          itemStyle:{{color:'#ff4444',borderColor:'#fff',borderWidth:1}},
          label:{{show:false}}}}}},
      {{name:'BB',type:'line',data:{bj},smooth:true,symbol:'none',lineStyle:{{color:'#ffaa00',width:1.5}}}},
      {{name:'스트레스',type:'line',data:{stj},smooth:true,symbol:'none',lineStyle:{{color:'#ff4444',width:1}}}},
      {{name:'안정심박',type:'line',data:{rj},smooth:true,symbol:'none',lineStyle:{{color:'#cc88ff',width:1}}}}
    ]
  }});
  window.addEventListener('resize',function(){{c.resize();}});
}})();
</script>"""


# ── 섹션 4b: 수면 미니 바 차트 ───────────────────────────────────────────────

def render_sleep_mini_chart(data: list[dict]) -> str:
    """7일 수면 점수 미니 수평 바."""
    vals = [(d["date"][-5:], d.get("sleep")) for d in data[-7:]]
    if not any(v for _, v in vals):
        return ""
    bars = []
    for dt, v in vals:
        w = min(100, v or 0)
        clr = "var(--green)" if (v or 0) >= 70 else ("var(--orange)" if (v or 0) >= 50 else "var(--red)")
        val_str = f"{v}" if v is not None else "—"
        bars.append(
            f"<div style='display:flex;align-items:center;gap:0.4rem;font-size:0.75rem;'>"
            f"<span style='width:30px;color:var(--muted);'>{dt}</span>"
            f"<div style='flex:1;background:rgba(255,255,255,0.08);border-radius:3px;height:6px;'>"
            f"<div style='width:{w}%;background:{clr};border-radius:3px;height:6px;'></div></div>"
            f"<span style='width:24px;text-align:right;'>{val_str}</span></div>"
        )
    return "<div style='margin-top:0.5rem;'>" + "".join(bars) + "</div>"


# ── 섹션 5b: HRV 미니 차트 + 기준선 ─────────────────────────────────────────

def render_hrv_mini_chart(data: list[dict], baseline: dict) -> str:
    """7일 HRV 미니 라인 + 기준선 밴드 해석."""
    vals = [d.get("hrv") for d in data[-7:]]
    if not any(vals):
        return ""
    lo = baseline.get("hrv_baseline_low")
    hi = baseline.get("hrv_baseline_high")
    today_hrv = vals[-1] if vals else None

    interp = ""
    if today_hrv is not None and lo is not None and hi is not None:
        if today_hrv < lo:
            interp = f"<p style='color:var(--red);font-size:0.78rem;margin:0.3rem 0 0;'>기준선({lo:.0f}–{hi:.0f}ms) 하단 → 자율신경 피로</p>"
        elif today_hrv > hi:
            interp = f"<p style='color:var(--green);font-size:0.78rem;margin:0.3rem 0 0;'>기준선({lo:.0f}–{hi:.0f}ms) 상단 → 회복 양호</p>"
        else:
            interp = f"<p style='color:var(--muted);font-size:0.78rem;margin:0.3rem 0 0;'>기준선({lo:.0f}–{hi:.0f}ms) 이내 → 정상 범위</p>"

    bars = []
    for i, v in enumerate(vals):
        if v is None:
            bars.append("<div style='width:8px;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;'></div>")
            continue
        h = max(4, min(40, int(v * 0.6)))
        clr = "#00ff88"
        if lo is not None and v < lo:
            clr = "#ff4444"
        elif hi is not None and v > hi:
            clr = "#00d4ff"
        bars.append(f"<div style='width:8px;height:{h}px;background:{clr};border-radius:2px;' title='{v:.0f}ms'></div>")

    return (
        "<div style='margin-top:0.5rem;'>"
        "<div style='display:flex;gap:3px;align-items:flex-end;height:44px;'>"
        + "".join(bars) +
        "</div>" + interp + "</div>"
    )


# ── 섹션 6: 패턴 인사이트 ────────────────────────────────────────────────────

def render_pattern_insights(data_14d: list[dict], baseline: dict) -> str:
    """규칙 기반 패턴 감지 인사이트."""
    if len(data_14d) < 3:
        return ""
    insights: list[str] = []
    recent = data_14d[-7:]

    # HRV 연속 하락
    hrv_vals = [d.get("hrv") for d in data_14d[-5:] if d.get("hrv") is not None]
    if len(hrv_vals) >= 3:
        drops = sum(1 for i in range(1, len(hrv_vals)) if hrv_vals[i] < hrv_vals[i - 1])
        if drops >= 3:
            insights.append("HRV가 3일 이상 연속 하락 중 → 과훈련 초기 징후 가능. 강도 조절 권장.")

    # 수면 양호 유지
    sleep_vals = [d.get("sleep") for d in recent if d.get("sleep") is not None]
    if sleep_vals and all(s >= 70 for s in sleep_vals):
        insights.append(f"수면 점수 {min(sleep_vals):.0f}–{max(sleep_vals):.0f} 범위로 양호 유지 중.")
    elif sleep_vals and all(s < 50 for s in sleep_vals[-3:]):
        insights.append("최근 3일 수면 점수 50 미만 → 수면 환경 점검 필요.")

    # 스트레스 패턴
    stress_vals = [d.get("stress") for d in recent if d.get("stress") is not None]
    if len(stress_vals) >= 5:
        avg_stress = sum(stress_vals) / len(stress_vals)
        if avg_stress > 50:
            insights.append(f"주간 평균 스트레스 {avg_stress:.0f} → 회복 시간이 제한될 수 있음.")

    # BB 하락 추세
    bb_vals = [d.get("bb") for d in data_14d[-5:] if d.get("bb") is not None]
    if len(bb_vals) >= 3 and bb_vals[-1] < bb_vals[0] - 15:
        insights.append(f"바디 배터리 {bb_vals[0]:.0f}→{bb_vals[-1]:.0f} 하락 추세 → 충분한 휴식 필요.")

    # HRV 기준선 이탈
    lo = baseline.get("hrv_baseline_low")
    if lo and hrv_vals:
        below = sum(1 for v in hrv_vals[-3:] if v < lo)
        if below >= 2:
            insights.append(f"최근 3일 중 {below}일 HRV가 기준선 이하 → 누적 피로 주의.")

    if not insights:
        return ""

    items = "".join(
        f"<li style='margin-bottom:0.35rem;font-size:0.83rem;color:var(--secondary);'>{i}</li>"
        for i in insights
    )
    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.4rem;'>패턴 인사이트</h2>"
        f"<ul style='padding-left:1.2rem;margin:0;'>{items}</ul></div>"
    )


# ── 섹션 7: 주간 비교 ────────────────────────────────────────────────────────

def render_weekly_comparison(comp: dict) -> str:
    """이번 주 vs 지난 주 평균 비교 테이블."""
    this_w = comp.get("this", {})
    last_w = comp.get("last", {})
    if not this_w or not last_w:
        return ""

    def _row(label: str, key: str, unit: str = "", fmt: str = ".0f", invert: bool = False) -> str:
        cur = this_w.get(key)
        prev = last_w.get(key)
        if cur is None and prev is None:
            return ""
        cur_s = f"{cur:{fmt}}" if cur is not None else "—"
        prev_s = f"{prev:{fmt}}" if prev is not None else "—"
        delta = ""
        if cur is not None and prev is not None:
            d = cur - prev
            if abs(d) < 0.5:
                delta = "<span style='color:var(--muted);'>±0</span>"
            else:
                up = d > 0
                color = "var(--red)" if (up == invert) else "var(--green)"
                arrow = "↑" if up else "↓"
                delta = f"<span style='color:{color};'>{arrow}{abs(d):{fmt}}</span>"
        return (
            f"<tr><td style='padding:0.25rem 0.5rem;font-size:0.82rem;'>{label}</td>"
            f"<td style='padding:0.25rem 0.5rem;font-weight:600;'>{cur_s}{unit}</td>"
            f"<td style='padding:0.25rem 0.5rem;color:var(--muted);'>{prev_s}{unit}</td>"
            f"<td style='padding:0.25rem 0.5rem;'>{delta}</td></tr>"
        )

    rows = (
        _row("수면 평균", "sleep")
        + _row("HRV 평균", "hrv", "ms")
        + _row("BB 평균", "bb")
        + _row("스트레스", "stress", "", ".0f", invert=True)
        + _row("안정심박", "rhr", "bpm", ".0f", invert=True)
    )
    if not rows:
        return ""

    return (
        "<div class='card'>"
        "<h2 style='font-size:1rem;margin-bottom:0.4rem;'>주간 비교</h2>"
        "<table style='width:100%;border-collapse:collapse;'>"
        "<thead><tr style='border-bottom:1px solid rgba(255,255,255,0.1);'>"
        "<th style='text-align:left;padding:0.25rem 0.5rem;font-size:0.78rem;color:var(--muted);'>항목</th>"
        "<th style='padding:0.25rem 0.5rem;font-size:0.78rem;color:var(--muted);'>이번 주</th>"
        "<th style='padding:0.25rem 0.5rem;font-size:0.78rem;color:var(--muted);'>지난 주</th>"
        "<th style='padding:0.25rem 0.5rem;font-size:0.78rem;color:var(--muted);'>변화</th>"
        "</tr></thead><tbody>" + rows + "</tbody></table></div>"
    )


# ── #1: 메트릭 해설 접이식 ───────────────────────────────────────────────────

def render_wellness_glossary() -> str:
    """HRV/BB/SDNN/Training Readiness 해설 접이식."""
    entries = [
        ("HRV (Heart Rate Variability)란?",
         "심박 간격의 변동성을 측정한 값입니다. 자율신경계 상태를 반영하며, "
         "높을수록 회복이 잘 되고 있음을 의미합니다. "
         "개인차가 크므로 절대값보다 본인의 기준선 대비 변화를 추적하는 것이 중요합니다."),
        ("Body Battery란?",
         "Garmin이 HRV·스트레스·수면·활동량을 종합하여 0~100으로 산출하는 에너지 지표입니다. "
         "100에 가까울수록 충분히 충전된 상태, 낮을수록 피로가 누적된 상태입니다. "
         "아침 기상 직후 값이 당일 훈련 강도 결정에 유용합니다."),
        ("SDNN vs RMSSD",
         "SDNN은 심박 간격의 전체 표준편차로 장기적 자율신경 톤을 반영합니다. "
         "RMSSD는 연속 심박 간 차이의 제곱평균제곱근으로 부교감신경(회복) 활동을 반영합니다. "
         "야간 측정 시 RMSSD가 더 민감한 회복 지표입니다."),
        ("Training Readiness란?",
         "Garmin이 수면·HRV·스트레스·회복시간·훈련부하를 종합하여 0~100으로 산출합니다. "
         "70+ = 고강도 훈련 가능, 40~70 = 중강도 권장, 40 미만 = 회복 우선. "
         "RunPulse의 UTRS와 함께 참고하면 더 정확한 판단이 가능합니다."),
    ]
    items = ""
    for title, desc in entries:
        items += (
            f"<details style='margin-bottom:0.4rem;'>"
            f"<summary style='cursor:pointer;font-size:0.88rem;color:var(--cyan);padding:0.3rem 0;'>{title}</summary>"
            f"<p style='font-size:0.82rem;color:var(--secondary);margin:0.3rem 0 0.5rem 1rem;line-height:1.5;'>{desc}</p>"
            f"</details>"
        )
    return (
        "<div class='card' style='margin:20px 0;'>"
        "<h2 style='font-size:1rem;margin-bottom:0.5rem;'>메트릭 해설</h2>"
        + items +
        "</div>"
    )


# ── #2: 수면 시간대 패턴 ─────────────────────────────────────────────────────

def render_sleep_time_pattern(sleep_times: list[dict]) -> str:
    """평균 취침/기상 시각 표시."""
    if not sleep_times:
        return ""
    starts, ends = [], []
    for st in sleep_times:
        s, e = st.get("start"), st.get("end")
        if s is not None:
            starts.append(float(s))
        if e is not None:
            ends.append(float(e))
    if not starts and not ends:
        return ""

    def _ts_to_hm(epoch_ms: float) -> str:
        """epoch ms → HH:MM 변환."""
        import datetime
        try:
            dt = datetime.datetime.fromtimestamp(epoch_ms / 1000)
            return dt.strftime("%H:%M")
        except (OSError, ValueError, OverflowError):
            return "—"

    parts = []
    if starts:
        avg_start = sum(starts) / len(starts)
        parts.append(f"평균 취침 {_ts_to_hm(avg_start)}")
    if ends:
        avg_end = sum(ends) / len(ends)
        parts.append(f"기상 {_ts_to_hm(avg_end)}")

    if not parts:
        return ""
    return (
        f"<p style='font-size:0.78rem;color:var(--muted);margin:0.3rem 0 0;'>"
        f"최근 {len(sleep_times)}일: {' / '.join(parts)}</p>"
    )


# ── #3: 이상치 빨간 점 (markPoint JS) ────────────────────────────────────────

def build_outlier_mark_points(data: list[dict], baseline: dict) -> str:
    """HRV 기준선 이탈일의 ECharts markPoint data 배열 (JS 문자열)."""
    lo = baseline.get("hrv_baseline_low")
    hi = baseline.get("hrv_baseline_high")
    if lo is None or hi is None:
        return "[]"
    points = []
    for d in data:
        hrv = d.get("hrv")
        if hrv is not None and (hrv < lo or hrv > hi):
            points.append({"xAxis": d["date"][-5:], "yAxis": hrv})
    return json.dumps(points)


# ── #5: 패턴 기반 회복 권장 생성 ──────────────────────────────────────────────

def build_pattern_recovery_tips(data_14d: list[dict], baseline: dict) -> list[str]:
    """패턴 인사이트에서 감지된 항목 → 구체적 권장사항 리스트."""
    tips: list[str] = []
    if len(data_14d) < 3:
        return tips

    # HRV 연속 하락 → 강도 조절
    hrv_vals = [d.get("hrv") for d in data_14d[-5:] if d.get("hrv") is not None]
    if len(hrv_vals) >= 3:
        drops = sum(1 for i in range(1, len(hrv_vals)) if hrv_vals[i] < hrv_vals[i - 1])
        if drops >= 3:
            tips.append("HRV 연속 하락 감지 — 이번 주 고강도 세션을 1회 줄이고 회복 러닝으로 대체하세요.")

    # BB 연속 저조
    bb_vals = [d.get("bb") for d in data_14d[-3:] if d.get("bb") is not None]
    if len(bb_vals) >= 3 and all(b < 40 for b in bb_vals):
        tips.append("바디 배터리 3일 연속 40 미만 — 고강도 훈련을 중단하고 완전 휴식일을 가지세요.")

    # 수면 3일 저조
    sleep_vals = [d.get("sleep") for d in data_14d[-3:] if d.get("sleep") is not None]
    if len(sleep_vals) >= 3 and all(s < 50 for s in sleep_vals):
        tips.append("수면 점수 3일 연속 50 미만 — 취침 시간을 30분 앞당기고 전자기기 사용을 줄이세요.")

    # HRV 기준선 이하 지속
    lo = baseline.get("hrv_baseline_low")
    if lo and len(hrv_vals) >= 3:
        below = sum(1 for v in hrv_vals[-3:] if v < lo)
        if below >= 2:
            tips.append(f"HRV가 기준선({lo:.0f}ms) 이하 지속 — 누적 피로입니다. 수면 질 개선과 휴식을 우선하세요.")

    return tips
