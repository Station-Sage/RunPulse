"""활동 상세 — 카드/섹션 렌더링 함수."""
from __future__ import annotations

import html

from .helpers import (
    fmt_duration,
    fmt_min,
    fmt_pace,
    metric_row,
    readiness_badge,
    safe_str,
)


def _fmt_int(v, unit: str = "") -> str:
    if v is None:
        return "—"
    return f"{int(round(float(v)))}{unit}"


def _fmt_float1(v, unit: str = "") -> str:
    if v is None:
        return "—"
    return f"{float(v):.1f}{unit}"


def _fmt_min_sec(sec) -> str:
    """초 → 분'초\" 형식."""
    if sec is None:
        return "—"
    sec = float(sec)
    m = int(sec) // 60
    s = int(sec) % 60
    return f"{m}'{s:02d}\""


def _render_activity_summary(act: dict) -> str:
    """활동 기본 정보 카드."""
    pace = safe_str(act.get("avg_pace"))
    dist = act.get("distance_km")
    dist_str = f"{float(dist):.2f} km" if dist is not None else "—"
    return (
        "<div class='card'>"
        "<h2>활동 요약</h2>"
        + metric_row("날짜", act.get("date"))
        + metric_row("유형", act.get("type"))
        + metric_row("거리", dist_str)
        + metric_row("시간", fmt_duration(act.get("duration_sec")))
        + metric_row("평균 페이스", pace)
        + metric_row("평균 심박", _fmt_int(act.get("avg_hr"), " bpm"))
        + metric_row("최대 심박", _fmt_int(act.get("max_hr"), " bpm"))
        + metric_row("평균 케이던스", _fmt_int(act.get("avg_cadence"), " spm"))
        + metric_row("고도 상승", _fmt_int(act.get("elevation_gain"), " m"))
        + metric_row("칼로리", _fmt_int(act.get("calories"), " kcal"))
        + "</div>"
    )


# 서비스 소스 카드는 views_activity_source_cards.py로 분리 — re-export
from .views_activity_source_cards import (  # noqa: F401, E402
    _render_garmin_daily_detail,
    _render_garmin_metrics,
    _render_strava_metrics,
    _render_intervals_metrics,
    _render_runalyze_metrics,
    _render_source_comparison,
    _render_service_tabs,
)


def _render_fitness_context(ctx: dict) -> str:
    """피트니스 컨텍스트 카드 (CTL/ATL/TSB + VO2Max)."""
    return (
        "<div class='card'>"
        "<h2>피트니스 컨텍스트</h2>"
        + metric_row("CTL (만성 부하)", ctx.get("ctl"))
        + metric_row("ATL (급성 부하)", ctx.get("atl"))
        + metric_row("TSB (부하 균형)", ctx.get("tsb"))
        + metric_row("Garmin VO2Max", ctx.get("garmin_vo2max"))
        + metric_row("Runalyze eVO2Max", ctx.get("runalyze_evo2max"))
        + metric_row("Runalyze VDOT", ctx.get("runalyze_vdot"))
        + "</div>"
    )


def _render_splits(splits: list) -> str:
    """페이스 스플릿 테이블 카드."""
    if not splits:
        return ""
    rows = [
        (
            f"{item.get('km')} (부분)" if item.get("partial") else item.get("km"),
            item.get("pace") or "—",
            item.get("avg_hr") or "—",
        )
        for item in splits
    ]
    return (
        "<div class='card'>"
        "<h2>페이스 스플릿 (km)</h2>"
        + make_table(["km", "페이스", "평균 심박"], rows)
        + "</div>"
    )


def _render_efficiency(eff: dict) -> str:
    """효율 지표 카드."""
    if not eff:
        return ""
    return (
        "<div class='card'>"
        "<h2>효율 분석</h2>"
        + metric_row("Aerobic EF", eff.get("ef"))
        + metric_row("Cardiac Decoupling", eff.get("decoupling_pct"), "%")
        + metric_row("상태", eff.get("status"))
        + "</div>"
    )


# ── 이전/다음 네비게이션 ─────────────────────────────────────────────────


def _render_activity_nav(
    prev_row: tuple | None, next_row: tuple | None
) -> str:
    """이전/다음 활동 네비 바."""
    parts = []
    if prev_row:
        prev_date = str(prev_row[1])[:10]
        parts.append(
            f"<a href='/activity/deep?id={prev_row[0]}'>← {html.escape(prev_date)}</a>"
        )
    else:
        parts.append("<span class='muted'>← (없음)</span>")

    parts.append("<a href='/activities'>목록으로</a>")

    if next_row:
        next_date = str(next_row[1])[:10]
        parts.append(
            f"<a href='/activity/deep?id={next_row[0]}'>{html.escape(next_date)} →</a>"
        )
    else:
        parts.append("<span class='muted'>(없음) →</span>")

    return (
        "<div style='display:flex; justify-content:space-between; "
        "align-items:center; margin:0.5rem 0; flex-wrap:wrap; gap:0.5rem;'>"
        + " ".join(parts)
        + "</div>"
    )


# ── 2차 메트릭 / computed_metrics 조회 ─────────────────────────────────────


def _render_horizontal_scroll(act: dict, metrics: dict) -> str:
    """핵심 메트릭 수평 스크롤 바 (V2-4-6, 모바일 최적화)."""
    dist = act.get("distance_km")
    dist_str = f"{float(dist):.2f} km" if dist is not None else "—"
    pace_str = act.get("avg_pace") or "—"
    fearp_val = metrics.get("FEARP")
    gap_val = metrics.get("GAP")

    items = [
        ("🏃", "거리", dist_str),
        ("⏱", "시간", fmt_duration(act.get("duration_sec"))),
        ("⚡", "페이스", f"{pace_str}/km" if pace_str != "—" else "—"),
        ("❤️", "심박수", _fmt_int(act.get("avg_hr"), " bpm")),
        ("📈", "고도↑", _fmt_int(act.get("elevation_gain"), " m")),
        ("🔥", "칼로리", _fmt_int(act.get("calories"), " kcal")),
    ]
    if fearp_val is not None:
        items.append(("🌡", "FEARP", f"{fmt_pace(fearp_val)}/km"))
    if gap_val is not None:
        items.append(("⛰", "GAP", f"{fmt_pace(gap_val)}/km"))

    chips = "".join(
        f"<div style='display:inline-flex;flex-direction:column;align-items:center;"
        f"min-width:76px;padding:0.55rem 0.7rem;"
        f"background:rgba(255,255,255,0.06);border-radius:12px;margin:0 4px;'>"
        f"<span style='font-size:1.3rem;line-height:1;'>{icon}</span>"
        f"<span style='font-size:0.68rem;color:var(--muted);margin-top:3px;'>{label}</span>"
        f"<span style='font-size:0.88rem;font-weight:600;margin-top:2px;'>{val}</span>"
        f"</div>"
        for icon, label, val in items
    )
    return (
        "<div style='overflow-x:auto;white-space:nowrap;padding:0.5rem 0 0.8rem;"
        "-webkit-overflow-scrolling:touch;'>"
        + chips
        + "</div>"
    )


# 메트릭 메타 정보: {key: (title_tooltip, interpret_fn)}
# interpret_fn(value) → (text, color_css) | None
_METRIC_META: dict[str, tuple[str, object]] = {
    "FEARP":          ("환경 보정 페이스 — 기온·습도·경사·고도를 표준 조건(15°C, 50%, 평지, 0m)으로 환산한 등가 페이스. 낮을수록 실제로 빠름.",
                       lambda v: ("표준 조건 기준 빠름" if v < 270 else "표준 조건 기준 보통" if v < 360 else "표준 조건 기준 느림", "var(--green)" if v < 270 else "var(--orange)" if v < 360 else "var(--red)")),
    "GAP":            ("경사 보정 페이스 (Grade-Adjusted Pace) — 오르막·내리막 효과를 제거한 평지 등가 페이스.",
                       None),
    "NGP":            ("정규화 경사 페이스 (Normalized Graded Pace) — 강도 변화를 4차 멱승으로 가중 평균한 실효 페이스.",
                       None),
    "RelativeEffort": ("상대 노력도 — 심박존별 시간에 Strava 가중치(0.5/1.0/2.0/3.5/5.5)를 적용한 운동 강도 점수.",
                       lambda v: ("가벼운 운동" if v < 50 else "적당한 강도" if v < 100 else "높은 강도" if v < 200 else "매우 높은 강도", "var(--green)" if v < 50 else "var(--cyan)" if v < 100 else "var(--orange)" if v < 200 else "var(--red)")),
    "AerobicDecoupling": ("유산소 분리 (Aerobic Decoupling) — 후반 PA:HR 대비 전반 PA:HR 저하율. 낮을수록 심폐 효율 유지.",
                           lambda v: ("심폐 안정적" if v < 5 else "약간 분리" if v < 10 else "유산소 드리프트 큼", "var(--green)" if v < 5 else "var(--orange)" if v < 10 else "var(--red)")),
    "EF":             ("효율 계수 (Efficiency Factor) — 페이스÷심박수 비율. 높을수록 같은 심박에서 더 빠름.",
                       None),
    "TRIMP":          ("훈련 충격 점수 (TRIMP) — 심박존별 운동 시간에 지수 가중치를 적용한 훈련 부하 지수.",
                       lambda v: ("가벼운 부하" if v < 50 else "중간 부하" if v < 100 else "고부하" if v < 150 else "매우 고부하", "var(--green)" if v < 50 else "var(--cyan)" if v < 100 else "var(--orange)" if v < 150 else "var(--red)")),
    "WLEI":           ("날씨 가중 노력 지수 (WLEI) — TRIMP에 기온·습도 스트레스를 곱한 실제 신체 부담 지수. 더운 날은 동일 페이스도 WLEI가 더 높음.",
                       lambda v: ("낮은 날씨 부담" if v < 60 else "중간 날씨 부담" if v < 120 else "높은 날씨 부담", "var(--green)" if v < 60 else "var(--orange)" if v < 120 else "var(--red)")),
    "DI":             ("내구성 지수 (DI) — 90분+ 세션에서 후반 PA:HR 효율 / 전반 PA:HR 효율. 1.0 이상이면 끝까지 효율 유지.",
                       lambda v: ("내구성 우수" if v >= 1.0 else "내구성 보통" if v >= 0.9 else "내구성 저하", "var(--green)" if v >= 1.0 else "var(--orange)" if v >= 0.9 else "var(--red)")),
    "LSI":            ("부하 스파이크 지수 (LSI) — 오늘 TRIMP / 21일 평균 TRIMP. 1.5 초과 시 급격한 과부하.",
                       lambda v: ("정상 범위" if v < 1.3 else "주의 — 과부하 경향" if v < 1.5 else "위험 — 급격한 과부하", "var(--green)" if v < 1.3 else "var(--orange)" if v < 1.5 else "var(--red)")),
    "Monotony":       ("훈련 단조로움 (Monotony) — 최근 7일 TRIMP 평균÷표준편차. 낮을수록 변화 있는 훈련.",
                       lambda v: ("다양한 훈련" if v < 1.5 else "약간 단조로움" if v < 2.0 else "매우 단조로운 훈련", "var(--green)" if v < 1.5 else "var(--orange)" if v < 2.0 else "var(--red)")),
    "ACWR":           ("급성/만성 부하 비율 (ACWR) — 7일 부하÷28일 부하. 0.8~1.3이 안전 구간.",
                       lambda v: ("부하 부족" if v < 0.8 else "적절한 훈련량" if v <= 1.3 else "과부하 위험", "var(--cyan)" if v < 0.8 else "var(--green)" if v <= 1.3 else "var(--red)")),
    "ADTI":           ("유산소 분리 추세 (ADTI) — 8주 Decoupling 선형 회귀 기울기. 음수면 개선 추세.",
                       lambda v: ("유산소 개선 추세" if v < 0 else "유산소 정체" if v < 0.5 else "유산소 저하 추세", "var(--green)" if v < 0 else "var(--cyan)" if v < 0.5 else "var(--orange)")),
    "MarathonShape":  ("마라톤 상태 (Marathon Shape) — 주간 거리·장거리런 기준 훈련 준비도 (0~100%).",
                       lambda v: ("레이스 준비 미흡" if v < 40 else "기본 준비됨" if v < 70 else "레이스 준비 완료", "var(--red)" if v < 40 else "var(--orange)" if v < 70 else "var(--green)")),
    "RTTI":           ("러닝 내성 훈련 지수 (RTTI) — Garmin 권장 최대 부하 대비 실제 훈련 부하 비율. 100% = 권장 한계.",
                       lambda v: ("훈련 여유 있음" if v < 80 else "권장 범위 내" if v <= 100 else "권장 한계 초과", "var(--cyan)" if v < 80 else "var(--green)" if v <= 100 else "var(--red)")),
    "TPDI":           ("실내/야외 퍼포먼스 격차 (TPDI) — 실외 vs 실내 평균 FEARP 차이. 양수면 실외 더 빠름.",
                       lambda v: ("격차 없음" if abs(v) < 5 else "약간 격차" if abs(v) < 15 else "큰 격차", "var(--green)" if abs(v) < 5 else "var(--orange)" if abs(v) < 15 else "var(--red)")),
}


def _metric_tooltip_icon(key: str) -> str:
    """메트릭 설명 툴팁 아이콘 HTML."""
    meta = _METRIC_META.get(key)
    if not meta:
        return ""
    desc = html.escape(meta[0])
    return (
        f" <span style='cursor:help; color:var(--muted); font-size:0.75rem;' title='{desc}'>ⓘ</span>"
    )


def _metric_interp_badge(key: str, value: float) -> str:
    """현재 수치 해설 뱃지 HTML."""
    meta = _METRIC_META.get(key)
    if not meta or meta[1] is None:
        return ""
    try:
        text, color = meta[1](value)
        return (
            f" <span style='font-size:0.72rem; color:{color}; margin-left:6px;'>{text}</span>"
        )
    except Exception:
        return ""


def _tids_zone_bar(tids_json: dict) -> str:
    """TIDS 존 분포 CSS 스택 바 HTML."""
    z12 = tids_json.get("z12", 0.0)
    z3 = tids_json.get("z3", 0.0)
    z45 = tids_json.get("z45", 0.0)
    dominant = tids_json.get("dominant_model") or ""
    model_label = {"polarized": "폴라리제드", "pyramid": "피라미드", "health": "건강유지"}.get(dominant, dominant)
    model_color = {"polarized": "var(--cyan)", "pyramid": "var(--green)", "health": "var(--orange)"}.get(dominant, "var(--muted)")

    return (
        "<div style='margin-top:0.6rem;'>"
        "<div style='display:flex;justify-content:space-between;font-size:0.8rem;margin-bottom:4px;'>"
        "<span style='color:var(--muted);font-weight:600;'>TIDS 훈련 강도 분포</span>"
        + (f"<span style='font-size:0.73rem;color:{model_color};'>{model_label}</span>" if model_label else "")
        + "</div>"
        "<div style='display:flex;height:10px;border-radius:5px;overflow:hidden;'>"
        f"<div style='width:{z12:.1f}%;background:#4dabf7;' title='Zone 1-2: {z12:.1f}%'></div>"
        f"<div style='width:{z3:.1f}%;background:#69db7c;' title='Zone 3: {z3:.1f}%'></div>"
        f"<div style='width:{z45:.1f}%;background:#ff6b6b;' title='Zone 4-5: {z45:.1f}%'></div>"
        "</div>"
        "<div style='display:flex;gap:0.8rem;font-size:0.72rem;color:var(--muted);margin-top:3px;'>"
        f"<span><span style='color:#4dabf7;'>■</span> Z1-2: {z12:.0f}%</span>"
        f"<span><span style='color:#69db7c;'>■</span> Z3: {z3:.0f}%</span>"
        f"<span><span style='color:#ff6b6b;'>■</span> Z4-5: {z45:.0f}%</span>"
        "</div>"
        "</div>"
    )


def _render_secondary_metrics_card(
    metrics: dict,
    day_metrics: dict | None = None,
    service_metrics: dict | None = None,
    day_metric_jsons: dict | None = None,
) -> str:
    """RunPulse 분석 (primary) + 서비스 원본 (secondary subtab) 탭 카드."""
    dm = day_metrics or {}
    svc = service_metrics or {}
    dmj = day_metric_jsons or {}

    # ── RunPulse 1차/2차 메트릭 ──────────────────────────────────────
    act_pairs = [
        ("FEARP",          metrics.get("FEARP"),          "pace"),
        ("GAP",            metrics.get("GAP"),            "pace"),
        ("NGP",            metrics.get("NGP"),            "pace"),
        ("RelativeEffort", metrics.get("RelativeEffort"), "f0"),
        ("AerobicDecoupling", metrics.get("AerobicDecoupling"), "f1%"),
        ("EF",             metrics.get("EF"),             "f4"),
        ("TRIMP",          metrics.get("TRIMP"),          "f1"),
        ("WLEI",           metrics.get("WLEI"),           "f1"),
    ]
    day_pairs = [
        ("DI",          dm.get("DI"),          "f2"),
        ("LSI",         dm.get("LSI"),         "f2"),
        ("Monotony",    dm.get("Monotony"),    "f2"),
        ("ACWR",        dm.get("ACWR"),        "f2"),
        ("ADTI",        dm.get("ADTI"),        "f4"),
        ("MarathonShape", dm.get("MarathonShape"), "f1%"),
        ("RTTI",        dm.get("RTTI"),        "f1%"),
        ("TPDI",        dm.get("TPDI"),        "f1%"),
    ]

    def _fmt_val(val, fmt: str) -> str:
        v = float(val)
        if fmt == "pace":
            return f"{fmt_pace(val)}/km"
        if fmt == "f0":
            return f"{v:.0f}"
        if fmt == "f1%":
            return f"{v:.1f}%"
        if fmt == "f4":
            return f"{v:.4f}"
        return f"{v:.1f}"

    def _rp_row(key: str, val, fmt: str) -> str:
        if val is None:
            return ""
        v = float(val)
        val_str = _fmt_val(val, fmt)
        badge = _metric_interp_badge(key, v)
        icon = _metric_tooltip_icon(key)
        label_html = f"{key}{icon}"
        return (
            "<div style='display:flex; justify-content:space-between; align-items:center;"
            "padding:0.4rem 0; border-bottom:1px solid var(--row-border);'>"
            f"<span style='font-size:0.85rem; color:var(--muted);'>{label_html}</span>"
            f"<span style='font-size:0.9rem; font-weight:600;'>{val_str}{badge}</span>"
            "</div>"
        )

    rp_rows = [_rp_row(k, v, f) for k, v, f in act_pairs if v is not None]
    if any(dm.get(k) is not None for k, _, _ in day_pairs):
        rp_rows.append(
            "<p style='font-size:0.75rem;color:var(--muted);margin:0.5rem 0 0.2rem;"
            "font-weight:600;'>당일 종합 지표</p>"
        )
    rp_rows += [_rp_row(k, v, f) for k, v, f in day_pairs if v is not None]

    # TIDS 존 분포 바
    tids_json = dmj.get("TIDS")
    tids_bar = _tids_zone_bar(tids_json) if isinstance(tids_json, dict) else ""

    if not rp_rows and not tids_bar:
        rp_content = "<p class='muted' style='margin:0.5rem 0;'>메트릭 미계산 — 설정 → 재계산 후 확인하세요.</p>"
    else:
        rp_content = "".join(rp_rows) + tids_bar

    # ── 서비스 1차 메트릭 ────────────────────────────────────────────
    svc_html_parts = []
    _SVC_COLORS = {
        "Garmin": "#0055b3",
        "Strava": "#FC4C02",
        "Intervals.icu": "#00884e",
        "날씨 (서비스)": "#7b2d8b",
        "존 점수 (서비스)": "#666",
    }
    for svc_name, svc_data in svc.items():
        color = _SVC_COLORS.get(svc_name, "#555")
        inner = ""
        for label, (val, unit) in svc_data.items():
            val_str = f"{val:.1f}{unit}" if isinstance(val, float) else f"{val}{unit}"
            inner += (
                "<div style='display:flex; justify-content:space-between;"
                "padding:0.3rem 0; border-bottom:1px solid var(--row-border);'>"
                f"<span style='font-size:0.82rem; color:var(--muted);'>{label}</span>"
                f"<span style='font-size:0.85rem; font-weight:600;'>{val_str}</span>"
                "</div>"
            )
        svc_html_parts.append(
            f"<div style='margin-bottom:0.8rem;'>"
            f"<p style='font-size:0.75rem; font-weight:700; color:{color};"
            f"margin:0 0 0.3rem;'>{svc_name}</p>"
            f"{inner}</div>"
        )

    svc_content = "".join(svc_html_parts) if svc_html_parts else (
        "<p class='muted' style='margin:0.5rem 0;'>서비스 메트릭 없음 — 해당 서비스 동기화 후 확인하세요.</p>"
    )

    # ── 탭 HTML ──────────────────────────────────────────────────────
    card_id = "metrics-tab-card"
    return f"""<div class='card' id='{card_id}'>
  <div style='display:flex; justify-content:space-between; align-items:center; margin-bottom:0.75rem;'>
    <h2 style='margin:0;'>메트릭 분석</h2>
    <div style='display:flex; gap:4px;'>
      <button id='mtab-rp' onclick='switchMetricTab("rp")'
        style='padding:0.3rem 0.8rem; font-size:0.8rem; border:1px solid var(--cyan);
               background:var(--cyan); color:#000; border-radius:4px; cursor:pointer; font-weight:600;'>
        RunPulse
      </button>
      <button id='mtab-svc' onclick='switchMetricTab("svc")'
        style='padding:0.3rem 0.8rem; font-size:0.8rem; border:1px solid var(--card-border);
               background:none; color:var(--muted); border-radius:4px; cursor:pointer;'>
        서비스 원본
      </button>
    </div>
  </div>
  <div id='mtab-content-rp'>{rp_content}</div>
  <div id='mtab-content-svc' style='display:none;'>{svc_content}</div>
</div>
<script>
function switchMetricTab(tab) {{
  document.getElementById('mtab-content-rp').style.display = tab==='rp' ? 'block' : 'none';
  document.getElementById('mtab-content-svc').style.display = tab==='svc' ? 'block' : 'none';
  var btnRp = document.getElementById('mtab-rp');
  var btnSvc = document.getElementById('mtab-svc');
  if (tab==='rp') {{
    btnRp.style.background='var(--cyan)'; btnRp.style.color='#000'; btnRp.style.borderColor='var(--cyan)';
    btnSvc.style.background='none'; btnSvc.style.color='var(--muted)'; btnSvc.style.borderColor='var(--card-border)';
  }} else {{
    btnSvc.style.background='var(--cyan)'; btnSvc.style.color='#000'; btnSvc.style.borderColor='var(--cyan)';
    btnRp.style.background='none'; btnRp.style.color='var(--muted)'; btnRp.style.borderColor='var(--card-border)';
  }}
}}
</script>"""


def _gauge_bar(value: float | None, max_val: float, color: str, label: str, unit: str = "") -> str:
    """수평 게이지 바 HTML (0 ~ max_val 스케일)."""
    if value is None:
        return (
            "<div style='margin-bottom:0.75rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;"
            f"margin-bottom:3px;'><span style='color:var(--muted);'>{label}</span>"
            "<span style='color:var(--muted);'>—</span></div>"
            "<div style='background:var(--row-border);border-radius:4px;height:8px;'></div>"
            "</div>"
        )
    pct = min(100.0, max(0.0, float(value) / max_val * 100))
    val_str = f"{float(value):.0f}{unit}"
    return (
        "<div style='margin-bottom:0.75rem;'>"
        f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;"
        f"margin-bottom:3px;'><span style='color:var(--muted);'>{label}</span>"
        f"<span style='font-weight:600;color:{color};'>{val_str}</span></div>"
        f"<div style='background:var(--row-border);border-radius:4px;height:8px;overflow:hidden;'>"
        f"<div style='height:100%;width:{pct:.1f}%;background:{color};border-radius:4px;"
        f"transition:width 0.5s;'></div></div>"
        "</div>"
    )


def _render_daily_scores_card(day_metrics: dict) -> str:
    """당일 UTRS/CIRS/ACWR 점수 카드 — 시각적 게이지 바 포함."""
    utrs = day_metrics.get("UTRS")
    cirs = day_metrics.get("CIRS")
    acwr = day_metrics.get("ACWR")
    cirs_val = day_metrics.get("CIRS")

    if all(v is None for v in (utrs, cirs, acwr)):
        return (
            "<div class='card'>"
            "<h2>당일 훈련 지수</h2>"
            "<p class='muted' style='margin:0;'>데이터 수집 중입니다</p>"
            "</div>"
        )

    # UTRS: 0~100, 높을수록 좋음
    utrs_color = "var(--green)" if utrs and float(utrs) >= 70 else "var(--orange)" if utrs and float(utrs) >= 40 else "var(--red)"
    # CIRS: 0~100, 낮을수록 좋음 → 바는 위험 수준 표시
    cirs_color = "var(--green)" if cirs_val and float(cirs_val) < 30 else "var(--orange)" if cirs_val and float(cirs_val) < 60 else "var(--red)"
    # ACWR: 0.8~1.3 정상. 100기준으로 0~150 범위 표시
    acwr_pct_val = float(acwr) * 100 if acwr is not None else None
    acwr_color = "var(--green)" if acwr and 0.8 <= float(acwr) <= 1.3 else "var(--orange)" if acwr and float(acwr) < 1.5 else "var(--red)"

    acwr_interp = ""
    if acwr is not None:
        av = float(acwr)
        if av < 0.8:
            acwr_interp = " <span style='font-size:0.72rem;color:var(--cyan);'>훈련량 부족</span>"
        elif av <= 1.3:
            acwr_interp = " <span style='font-size:0.72rem;color:var(--green);'>적절한 훈련량</span>"
        elif av <= 1.5:
            acwr_interp = " <span style='font-size:0.72rem;color:var(--orange);'>과부하 주의</span>"
        else:
            acwr_interp = " <span style='font-size:0.72rem;color:var(--red);'>과부하 위험</span>"

    utrs_interp = ""
    if utrs is not None:
        uv = float(utrs)
        if uv >= 70:
            utrs_interp = "<span style='font-size:0.72rem;color:var(--green);'>컨디션 최적 — 고강도 훈련 가능</span>"
        elif uv >= 50:
            utrs_interp = "<span style='font-size:0.72rem;color:var(--cyan);'>보통 — 일반 훈련 적합</span>"
        elif uv >= 30:
            utrs_interp = "<span style='font-size:0.72rem;color:var(--orange);'>피로 누적 — 경량 훈련 권장</span>"
        else:
            utrs_interp = "<span style='font-size:0.72rem;color:var(--red);'>휴식 필요 — 회복에 집중</span>"

    cirs_interp = ""
    if cirs_val is not None:
        cv = float(cirs_val)
        if cv < 30:
            cirs_interp = "<span style='font-size:0.72rem;color:var(--green);'>안전 수준</span>"
        elif cv < 50:
            cirs_interp = "<span style='font-size:0.72rem;color:var(--cyan);'>낮은 위험</span>"
        elif cv < 75:
            cirs_interp = "<span style='font-size:0.72rem;color:var(--orange);'>주의 — 부상 위험 증가</span>"
        else:
            cirs_interp = "<span style='font-size:0.72rem;color:var(--red);'>경고 — 강도 즉시 낮추기</span>"

    return (
        "<div class='card'>"
        "<h2>당일 훈련 지수</h2>"
        + _gauge_bar(utrs, 100, utrs_color, "UTRS — 훈련 준비도")
        + (f"<div style='margin:-0.5rem 0 0.6rem;'>{utrs_interp}</div>" if utrs_interp else "")
        + _gauge_bar(cirs_val, 100, cirs_color, "CIRS — 부상 위험도")
        + (f"<div style='margin:-0.5rem 0 0.6rem;'>{cirs_interp}</div>" if cirs_interp else "")
        + "<div style='margin-bottom:0.75rem;'>"
        + f"<div style='display:flex;justify-content:space-between;font-size:0.82rem;margin-bottom:3px;'>"
        + f"<span style='color:var(--muted);'>ACWR — 급성/만성 부하비</span>"
        + f"<span style='font-weight:600;color:{acwr_color};'>"
        + (f"{float(acwr):.2f}" if acwr is not None else "—")
        + acwr_interp
        + "</span></div>"
        + "<div style='background:var(--row-border);border-radius:4px;height:8px;overflow:hidden;position:relative;'>"
        # 정상 구간 표시 (80~130% → 53~87% 위치)
        + "<div style='position:absolute;left:53%;width:34%;height:100%;background:rgba(0,255,136,0.15);'></div>"
        + (f"<div style='height:100%;width:{min(100,float(acwr)/1.5*100):.1f}%;background:{acwr_color};"
           f"border-radius:4px;transition:width 0.5s;'></div>" if acwr is not None else "")
        + "</div>"
        + "<div style='display:flex;justify-content:space-between;font-size:0.7rem;color:var(--muted);margin-top:2px;'>"
        + "<span>0.0</span><span style='margin-left:53%;'>0.8</span><span>1.5+</span>"
        + "</div>"
        + "</div>"
        + "</div>"
    )


# ── 신규 분석 카드 ─────────────────────────────────────────────────────────


def _render_activity_classification_badge(act: dict) -> str:
    """활동 유형 자동 분류 뱃지 (easy/tempo/interval/long/recovery/race)."""
    duration = act.get("duration_sec") or 0
    avg_hr = act.get("avg_hr") or 0
    if duration >= 90 * 60:
        cls, icon, desc = "장거리런", "&#127959;", "90분+ 장거리 훈련"
    elif avg_hr >= 175:
        cls, icon, desc = "인터벌/경기", "&#9889;", "고강도 — 인터벌 또는 레이스 수준"
    elif avg_hr >= 160:
        cls, icon, desc = "템포런", "&#128293;", "유산소 역치 훈련"
    elif avg_hr and avg_hr < 135:
        cls, icon, desc = "회복런", "&#128564;", "가벼운 회복 조깅"
    elif avg_hr:
        cls, icon, desc = "유산소런", "&#127939;", "기본 유산소 훈련"
    else:
        return ""
    return (
        f"<div style='padding:0.3rem 0;'>"
        f"<span style='background:rgba(0,212,255,0.12);color:var(--cyan);"
        f"border-radius:16px;padding:0.28rem 0.8rem;font-size:0.8rem;'>"
        f"{icon} {cls} — {desc}</span></div>"
    )


def _render_pmc_sparkline_card(pmc: dict) -> str:
    """TRIMP_daily + ACWR 60일 ECharts 스파크라인 카드."""
    if not pmc or not pmc.get("dates"):
        return (
            "<div class='card'><h2>훈련 부하 추이 (PMC)</h2>"
            "<p class='muted' style='margin:0;'>데이터 수집 중 — 메트릭 재계산 후 표시됩니다.</p>"
            "</div>"
        )
    import json as _json
    dates = pmc["dates"]
    trimp = pmc["trimp"]
    acwr = pmc["acwr"]
    target = pmc.get("target_date", "")

    # 오늘 날짜 markLine
    mark_line = ""
    if target in dates:
        mark_line = f', markLine: {{data:[{{xAxis:"{target}",lineStyle:{{color:"#fff",type:"dashed",opacity:0.4}}}}]}}'

    dates_json = _json.dumps(dates)
    trimp_json = _json.dumps(trimp)
    acwr_json = _json.dumps(acwr)

    return f"""<div class='card'>
  <h2>훈련 부하 추이 (60일)</h2>
  <div id="pmc-chart" style="height:180px;"></div>
  <script>
  (function() {{
    var ec = echarts.init(document.getElementById('pmc-chart'), 'dark', {{backgroundColor:'transparent'}});
    ec.setOption({{
      grid: {{top:20, bottom:30, left:36, right:50}},
      legend: {{top:0, right:0, textStyle:{{fontSize:10, color:'#aaa'}}, itemWidth:10, itemHeight:6}},
      tooltip: {{trigger:'axis', axisPointer:{{type:'cross'}}}},
      xAxis: {{type:'category', data:{dates_json}, axisLabel:{{fontSize:9, color:'#888',
        formatter:function(v){{return v.slice(5);}} }}, axisLine:{{lineStyle:{{color:'#444'}}}}}},
      yAxis: [
        {{type:'value', name:'TRIMP', nameTextStyle:{{fontSize:9,color:'#74c0fc'}},
          axisLabel:{{fontSize:9, color:'#74c0fc'}}, splitLine:{{lineStyle:{{color:'#2a2a3a'}}}}}},
        {{type:'value', name:'ACWR', nameTextStyle:{{fontSize:9,color:'#ffd43b'}},
          axisLabel:{{fontSize:9, color:'#ffd43b'}}, min:0, max:2.0, splitLine:{{show:false}},
          markArea:{{silent:true, data:[[{{yAxis:0.8,itemStyle:{{color:'rgba(0,255,136,0.06)'}}}},{{yAxis:1.3}}]]}} }}
      ],
      series: [
        {{name:'TRIMP', type:'bar', data:{trimp_json}, itemStyle:{{color:'rgba(116,192,252,0.6)'}}{mark_line}}},
        {{name:'ACWR', type:'line', yAxisIndex:1, data:{acwr_json},
          lineStyle:{{color:'#ffd43b', width:2}}, symbol:'none',
          markLine:{{silent:true, data:[
            {{yAxis:0.8, lineStyle:{{color:'rgba(0,255,136,0.4)',type:'dashed'}}}},
            {{yAxis:1.3, lineStyle:{{color:'rgba(255,68,68,0.4)',type:'dashed'}}}}
          ]}}}}
      ]
    }});
    window.addEventListener('resize', function(){{ec.resize();}});
  }})();
  </script>
</div>"""


def _render_di_card(day_metrics: dict) -> str:
    """DI (내구성 지수) 카드 — 장거리 지구력 평가."""
    di = day_metrics.get("DI")
    if di is None:
        return (
            "<div class='card'><h2>DI 내구성 지수</h2>"
            "<p class='muted' style='margin:0;'>90분 이상 세션 3회+ 필요. 장거리 훈련 후 표시됩니다.</p></div>"
        )
    di_f = float(di)
    if di_f >= 1.0:
        badge, badge_color, interp = "&#10003; 우수", "var(--green)", "후반에도 페이스·심박 효율 유지. 내구성 양호."
    elif di_f >= 0.9:
        badge, badge_color, interp = "&#9888; 보통", "var(--orange)", "후반 효율 소폭 저하. 장거리 훈련으로 개선 가능."
    else:
        badge, badge_color, interp = "&#10007; 부족", "var(--red)", "후반 페이스 저하 뚜렷. 지구력 강화 훈련 필요."
    return (
        "<div class='card'><h2>DI 내구성 지수</h2>"
        "<div style='display:flex;align-items:center;gap:1rem;margin-bottom:0.5rem;'>"
        f"<span style='font-size:2rem;font-weight:700;color:var(--cyan);'>{di_f:.3f}</span>"
        f"<span style='background:rgba(255,255,255,0.08);color:{badge_color};"
        f"border-radius:12px;padding:0.2rem 0.6rem;font-size:0.82rem;'>{badge}</span></div>"
        f"<p style='font-size:0.82rem;color:var(--secondary);margin:0;'>{interp}</p>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>&#8805;1.0 우수 / 0.9-1.0 보통 / &lt;0.9 부족 | 최근 8주 90분+ 세션 평균</p>"
        "</div>"
    )


def _render_fearp_breakdown_card(metric_jsons: dict) -> str:
    """FEARP 환경 요인 분해 카드."""
    mj = metric_jsons.get("FEARP")
    if not mj:
        return ""
    actual = mj.get("actual_pace") or 0
    fearp = mj.get("fearp") or actual
    diff = fearp - actual if actual > 0 else 0
    diff_str = (f"+{fmt_pace(abs(diff))}/km 느린 조건" if diff > 0
                else f"{fmt_pace(abs(diff))}/km 빠른 조건") if diff else "표준 조건"

    def _factor_bar(label: str, factor: float, baseline: float = 1.0) -> str:
        deviation = (factor - baseline) / baseline * 100 if baseline else 0
        if abs(deviation) < 0.5:
            clr, effect = "#00ff88", "영향 없음"
        elif deviation > 0:
            clr, effect = "#ffaa00", f"+{deviation:.1f}% 불리"
        else:
            clr, effect = "#00d4ff", f"{deviation:.1f}% 유리"
        pct = min(100, abs(deviation) * 5)
        return (
            f"<div style='margin-bottom:0.3rem;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.78rem;margin-bottom:0.1rem;'>"
            f"<span style='color:var(--secondary);'>{label}</span>"
            f"<span style='color:{clr};'>{effect} ({factor:.4f})</span></div>"
            f"<div style='background:rgba(255,255,255,0.08);border-radius:3px;height:5px;'>"
            f"<div style='width:{pct}%;background:{clr};border-radius:3px;height:5px;'></div></div></div>"
        )

    bars = (
        _factor_bar("기온 영향 (temp_factor)", mj.get("temp_factor", 1.0))
        + _factor_bar("습도 영향 (humidity_factor)", mj.get("humidity_factor", 1.0))
        + _factor_bar("고도 영향 (altitude_factor)", mj.get("altitude_factor", 1.0))
        + _factor_bar("경사 영향 (grade_factor)", mj.get("grade_factor", 1.0))
    )
    return (
        "<div class='card'><h2>FEARP 환경 요인 분해</h2>"
        "<div style='display:flex;gap:1.5rem;margin-bottom:0.6rem;'>"
        f"<div style='text-align:center;'><div style='font-size:1.4rem;font-weight:700;color:var(--cyan);'>"
        f"{fmt_pace(fearp)}/km</div><div class='muted' style='font-size:0.74rem;'>FEARP (보정)</div></div>"
        f"<div style='text-align:center;'><div style='font-size:1.4rem;font-weight:700;'>"
        f"{fmt_pace(actual)}/km</div><div class='muted' style='font-size:0.74rem;'>실제 페이스</div></div>"
        f"<div style='text-align:center;font-size:0.82rem;color:var(--orange);align-self:center;'>{diff_str}</div>"
        f"</div>{bars}</div>"
    )


def _render_decoupling_detail_card(metrics: dict, metric_jsons: dict) -> str:
    """Aerobic Decoupling 해석 카드 (EF + aerobic stability 판단)."""
    dec = metrics.get("AerobicDecoupling")
    mj = metric_jsons.get("AerobicDecoupling") or {}
    ef = mj.get("ef") or metrics.get("EF")
    grade = mj.get("grade", "")
    if dec is None and ef is None:
        return ""
    dec_f = float(dec) if dec is not None else None
    ef_f = float(ef) if ef is not None else None
    if dec_f is None:
        badge, badge_color = "—", "var(--muted)"
        comment = "랩 데이터 부족 — 분할 기록이 있을 경우 표시됩니다."
    elif grade == "good" or dec_f < 5.0:
        badge, badge_color = "&#128994; 양호 (Decoupling &lt;5%)", "var(--green)"
        comment = "전/후반 심박 효율이 잘 유지됨. 장거리 적합 유산소 베이스."
    elif grade == "moderate" or dec_f < 10.0:
        badge, badge_color = "&#128993; 보통 (5-10%)", "var(--orange)"
        comment = "후반 효율 소폭 저하. 기본 유산소 훈련 지속 권장."
    else:
        badge, badge_color = "&#128308; 낮음 (&gt;10%)", "var(--red)"
        comment = "후반 급격한 효율 저하. 유산소 베이스 강화 필요."
    dec_str = f"{dec_f:.1f}%" if dec_f is not None else "—"
    ef_str = f"{ef_f:.4f}" if ef_f is not None else "—"
    return (
        "<div class='card'><h2>유산소 디커플링 분석</h2>"
        "<div style='display:flex;gap:1.5rem;margin-bottom:0.5rem;'>"
        f"<div style='text-align:center;'><div style='font-size:1.5rem;font-weight:700;color:var(--cyan);'>{dec_str}</div>"
        f"<div class='muted' style='font-size:0.74rem;'>Decoupling</div></div>"
        f"<div style='text-align:center;'><div style='font-size:1.5rem;font-weight:700;'>{ef_str}</div>"
        f"<div class='muted' style='font-size:0.74rem;'>EF (m/min/bpm)</div></div>"
        "</div>"
        f"<div style='background:rgba(255,255,255,0.06);border-radius:10px;padding:0.5rem 0.7rem;margin-bottom:0.4rem;'>"
        f"<span style='color:{badge_color};font-size:0.84rem;'>{badge}</span></div>"
        f"<p style='font-size:0.8rem;color:var(--secondary);margin:0;'>{comment}</p>"
        "<p class='muted' style='font-size:0.74rem;margin-top:0.4rem;'>EF = NGP / avg_HR | Decoupling = (EF전반-EF후반)/EF전반 × 100</p>"
        "</div>"
    )


def _render_map_placeholder(activity_id: int | None = None) -> str:
    """활동 경로 지도 (Leaflet + OpenStreetMap)."""
    if not activity_id:
        return (
            "<div class='card' style='text-align:center;min-height:120px;"
            "display:flex;flex-direction:column;align-items:center;justify-content:center;'>"
            "<div style='font-size:2.5rem;margin-bottom:0.4rem;'>&#128506;</div>"
            "<h2 style='font-size:0.95rem;margin-bottom:0.3rem;'>활동 경로 지도</h2>"
            "<p class='muted' style='font-size:0.8rem;margin:0;'>활동을 선택하세요.</p></div>"
        )
    # GPS 스트림 로드
    import json
    import sqlite3
    from .helpers import db_path
    coords = []
    try:
        with sqlite3.connect(str(db_path())) as conn:
            rows = conn.execute(
                "SELECT data_json FROM activity_streams WHERE activity_id=? AND stream_type='latlng' LIMIT 1",
                (activity_id,),
            ).fetchone()
            # 그룹 내 다른 소스에서 GPS 탐색
            if not rows or not rows[0]:
                grp = conn.execute(
                    "SELECT matched_group_id FROM activity_summaries WHERE id=?",
                    (activity_id,),
                ).fetchone()
                if grp and grp[0]:
                    rows = conn.execute(
                        "SELECT s.data_json FROM activity_streams s "
                        "JOIN activity_summaries a ON a.id=s.activity_id "
                        "WHERE a.matched_group_id=? AND s.stream_type='latlng' LIMIT 1",
                        (grp[0],),
                    ).fetchone()
            if rows and rows[0]:
                data = json.loads(rows[0]) if isinstance(rows[0], str) else rows[0]
                if isinstance(data, list) and len(data) >= 2 and isinstance(data[0], (list, tuple)):
                    coords = [[float(p[0]), float(p[1])] for p in data if len(p) >= 2]
                elif isinstance(data, dict):
                    lats = data.get("lat", data.get("latitude", []))
                    lngs = data.get("lng", data.get("longitude", []))
                    if lats and lngs:
                        coords = [[float(la), float(lo)] for la, lo in zip(lats, lngs)]
    except Exception:
        pass
    if not coords or len(coords) < 2:
        return (
            "<div class='card' style='text-align:center;min-height:120px;"
            "display:flex;flex-direction:column;align-items:center;justify-content:center;'>"
            "<div style='font-size:2.5rem;margin-bottom:0.4rem;'>&#128506;</div>"
            "<h2 style='font-size:0.95rem;margin-bottom:0.3rem;'>활동 경로 지도</h2>"
            "<p class='muted' style='font-size:0.8rem;margin:0;'>GPS 데이터가 없습니다.</p></div>"
        )
    # 다운샘플링
    if len(coords) > 500:
        step = len(coords) // 500
        coords = coords[::step]
    coords_json = json.dumps(coords)
    mid = coords[len(coords) // 2]
    return (
        "<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>"
        "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>"
        "<div class='card' style='padding:0;overflow:hidden;border-radius:20px;'>"
        f"<div id='activity-map' style='height:300px;width:100%;'></div></div>"
        "<script>"
        "(function(){"
        "var el=document.getElementById('activity-map');"
        "if(!el||typeof L==='undefined')return;"
        f"var coords={coords_json};"
        f"var map=L.map('activity-map',{{zoomControl:false}}).setView([{mid[0]},{mid[1]}],13);"
        "L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{"
        "attribution:'&copy; OSM',maxZoom:18"
        "}).addTo(map);"
        "var latlngs=coords.map(function(c){return [c[0],c[1]];});"
        "var polyline=L.polyline(latlngs,{color:'#00d4ff',weight:3,opacity:0.9}).addTo(map);"
        "map.fitBounds(polyline.getBounds(),{padding:[20,20]});"
        "L.marker(latlngs[0],{title:'시작'}).addTo(map);"
        "L.marker(latlngs[latlngs.length-1],{title:'종료'}).addTo(map);"
        "})();</script>"
    )
