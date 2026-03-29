"""훈련 계획 Wizard — HTML 렌더러 (Phase C).

views_training_wizard.py 라우트에서 import.
"""
from __future__ import annotations

import html as _html
import json
from datetime import date

_DAYS = ["월", "화", "수", "목", "금", "토", "일"]
_DIST_OPTS = [
    ("5k", "5K"), ("10k", "10K"),
    ("half", "Half Marathon (21.1km)"), ("full", "Full Marathon (42.2km)"),
    ("1.5k", "1.5K"), ("3k", "3K"), ("custom", "기타 (직접 입력)"),
]
_S = ("padding:0.4rem;background:var(--input-bg,#1a2035);"
      "border:1px solid var(--card-border);color:var(--text);border-radius:4px;")
_W = _S + "width:100%;box-sizing:border-box;"
_NEXT = ("background:var(--cyan);color:#000;border:none;"
         "padding:0.5rem 1.5rem;border-radius:6px;font-weight:600;cursor:pointer;")
_BACK = ("background:rgba(255,255,255,0.08);color:var(--text);border:none;"
         "padding:0.5rem 1.2rem;border-radius:6px;cursor:pointer;")


def _fmt_time(sec: int) -> str:
    h, r = divmod(int(sec), 3600)
    m, s = divmod(r, 60)
    return f"{h}:{m:02d}:{s:02d}"


def _fmt_pace(sec_km: int) -> str:
    return f"{sec_km // 60}:{sec_km % 60:02d}"


def _hidden(d: dict) -> str:
    return (f"<input type='hidden' name='wizard_data' "
            f"value='{_html.escape(json.dumps(d, ensure_ascii=False))}'>")


def _steps(cur: int) -> str:
    labels = ["목표", "환경", "분석", "확인"]
    items = ""
    for i, lab in enumerate(labels, 1):
        c = "#00ff88" if i < cur else "var(--cyan)" if i == cur else "rgba(255,255,255,0.25)"
        items += (
            f"<div style='display:flex;flex-direction:column;align-items:center;gap:4px;'>"
            f"<div style='width:28px;height:28px;border-radius:50%;background:{c};"
            f"display:flex;align-items:center;justify-content:center;"
            f"font-size:0.75rem;font-weight:bold;color:#000;'>{i}</div>"
            f"<span style='font-size:0.7rem;color:{c};'>{lab}</span></div>"
        )
        if i < 4:
            sep = "#00ff88" if i < cur else "rgba(255,255,255,0.15)"
            items += f"<div style='flex:1;height:2px;background:{sep};margin:12px 4px 0;'></div>"
    return f"<div style='display:flex;align-items:flex-start;margin-bottom:1.5rem;'>{items}</div>"


def _day_checks(mask: int, prefix: str) -> str:
    return "".join(
        f"<label style='display:flex;align-items:center;gap:3px;cursor:pointer;"
        f"font-size:0.88rem;user-select:none;'>"
        f"<input type='checkbox' name='{prefix}{i}' value='{1 << i}' "
        f"{'checked' if (mask & (1 << i)) else ''} style='accent-color:var(--cyan);'>"
        f" {d}</label>"
        for i, d in enumerate(_DAYS)
    )


# ── Step 렌더러 ─────────────────────────────────────────────────────────


def render_step1(data: dict) -> str:
    """Step 1: 레이스 목표 입력 폼."""
    dist_opts = "".join(
        f"<option value='{v}' {'selected' if data.get('distance_label') == v else ''}>"
        f"{lbl}</option>"
        for v, lbl in _DIST_OPTS
    )
    is_cust = data.get("distance_label") == "custom"
    today = date.today().isoformat()
    cust_style = _W if is_cust else _W + "display:none;"
    return (
        f"<div id='wizard-container'>{_steps(1)}"
        f"<h3 style='margin:0 0 1rem;'>Step 1 — 레이스 목표</h3>"
        f"<form onsubmit='wizardNext(event,1)'>"
        f"<div style='margin-bottom:1rem;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>목표 이름</label>"
        f"<input type='text' name='goal_name' value='{_html.escape(data.get('goal_name', ''))}'"
        f" placeholder='예: 2026 서울 하프마라톤' style='{_W}' required></div>"
        f"<div style='margin-bottom:1rem;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>종목</label>"
        f"<select name='distance_label' id='wiz-dist' onchange='wizDistChange(this.value)'"
        f" style='{_S}'>{dist_opts}</select>"
        f"<input type='number' name='custom_km' id='wiz-custom'"
        f" value='{_html.escape(str(data.get('custom_km', '')))}'"
        f" min='1' max='200' step='0.1' placeholder='거리 (km)' style='{cust_style}'></div>"
        f"<div style='margin-bottom:1rem;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>레이스 날짜</label>"
        f"<input type='date' name='race_date' value='{_html.escape(data.get('race_date', ''))}'"
        f" min='{today}' style='{_W}' required></div>"
        f"<div style='display:flex;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap;'>"
        f"<div style='flex:1;min-width:140px;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>"
        f"목표 완주 시간 <span class='muted'>(H:MM:SS)</span></label>"
        f"<input type='text' name='target_time' value='{_html.escape(data.get('target_time', ''))}'"
        f" placeholder='예: 1:50:00' style='{_W}'></div>"
        f"<div style='flex:1;min-width:140px;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>"
        f"목표 페이스 <span class='muted'>(MM:SS/km)</span></label>"
        f"<input type='text' name='target_pace' value='{_html.escape(data.get('target_pace', ''))}'"
        f" placeholder='예: 5:14' style='{_W}'></div></div>"
        f"<div style='display:flex;justify-content:flex-end;'>"
        f"<button type='submit' style='{_NEXT}'>다음 →</button>"
        f"</div></form></div>"
    )


def render_step2(data: dict, rec: dict) -> str:
    """Step 2: 훈련 환경 설정 + 기간 선택."""
    opt_min = rec.get("optimal_min", 12)
    min_w = rec.get("min", 6)
    plan_w = data.get("plan_weeks") or opt_min
    rep_m = data.get("interval_rep_m", 1000)
    rep_opts = "".join(
        f"<option value='{v}' {'selected' if v == rep_m else ''}>{v}m</option>"
        for v in [200, 300, 400, 600, 800, 1000, 1200, 1600]
    )
    return (
        f"<div id='wizard-container'>{_steps(2)}"
        f"<h3 style='margin:0 0 1rem;'>Step 2 — 훈련 환경</h3>"
        f"<form onsubmit='wizardNext(event,2)'>{_hidden(data)}"
        f"<div style='margin-bottom:1rem;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:6px;'>휴식 요일</label>"
        f"<div style='display:flex;gap:10px;flex-wrap:wrap;'>{_day_checks(data.get('rest_mask', 0), 'rest_day_')}</div></div>"
        f"<div style='margin-bottom:1rem;'>"
        f"<label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:6px;'>"
        f"롱런 요일 <span class='muted'>(0개=자동)</span></label>"
        f"<div style='display:flex;gap:10px;flex-wrap:wrap;'>{_day_checks(data.get('long_mask', 0), 'long_day_')}</div></div>"
        f"<div style='display:flex;gap:1rem;flex-wrap:wrap;margin-bottom:1rem;'>"
        f"<div><label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>인터벌 거리</label>"
        f"<select name='interval_rep_m' style='{_S}'>{rep_opts}</select></div>"
        f"<div><label style='font-size:0.85rem;font-weight:600;display:block;margin-bottom:4px;'>"
        f"훈련 기간 (주)"
        f"<span class='muted' style='font-weight:normal;font-size:0.78rem;'> 추천 {rec.get('optimal_min', '?')}~{rec.get('optimal_max', '?')}주</span>"
        f"</label>"
        f"<input type='number' name='plan_weeks' id='wiz-weeks' value='{plan_w}' min='1' max='52'"
        f" style='width:80px;{_S}' oninput='wizWeeksCheck(this,{min_w})'>"
        f"<span id='wiz-weeks-warn' style='font-size:0.78rem;color:#ffaa00;margin-left:6px;display:none;'>"
        f"⚠️ 최솟값({min_w}주)보다 짧습니다</span></div></div>"
        f"<div style='display:flex;justify-content:space-between;margin-top:1rem;'>"
        f"<button type='button' onclick='wizardBack()' style='{_BACK}'>← 이전</button>"
        f"<button type='submit' style='{_NEXT}'>분석 →</button>"
        f"</div></form></div>"
    )


def render_step3(data: dict, r: dict) -> str:
    """Step 3: readiness 분석 결과 표시."""
    pct = r.get("achievability_pct", 0)
    bar_c = "#00ff88" if pct >= 75 else "#ffaa00" if pct >= 50 else "#ff4444"
    now_t = _fmt_time(r["projected_time_now"]) if r.get("projected_time_now") else "—"
    end_t = _fmt_time(r["projected_time_end"]) if r.get("projected_time_end") else "—"
    goal_t = _fmt_time(data["time_sec"]) if data.get("time_sec") else "—"
    rec = r.get("recommended_weeks", {})
    warns_html = "".join(
        f"<li style='color:#ffaa00;font-size:0.82rem;'>{_html.escape(w)}</li>"
        for w in r.get("warnings", [])
    )
    vdot_row = ""
    if r.get("current_vdot"):
        req_str = f" → 목표 {r['required_vdot']:.1f}" if r.get("required_vdot") else ""
        vdot_row = (
            f"<tr><td class='muted' style='padding:3px 8px;'>현재 VDOT</td>"
            f"<td style='padding:3px 8px;font-weight:600;'>{r['current_vdot']:.1f}{req_str}</td></tr>"
        )
    data_out = {**data, "current_vdot": r.get("current_vdot")}
    return (
        f"<div id='wizard-container'>{_steps(3)}"
        f"<h3 style='margin:0 0 1rem;'>Step 3 — 현재 상태 분석</h3>"
        f"<div class='card' style='padding:1rem;margin-bottom:1rem;'>"
        f"<table style='width:100%;border-collapse:collapse;font-size:0.88rem;'>"
        f"{vdot_row}"
        f"<tr><td class='muted' style='padding:3px 8px;'>현재 기준 예상 기록</td>"
        f"<td style='padding:3px 8px;font-weight:600;'>{now_t}</td></tr>"
        f"<tr><td class='muted' style='padding:3px 8px;'>훈련 완료 시 예상 기록</td>"
        f"<td style='padding:3px 8px;font-weight:600;color:var(--cyan);'>{end_t}</td></tr>"
        f"<tr><td class='muted' style='padding:3px 8px;'>목표 기록</td>"
        f"<td style='padding:3px 8px;font-weight:600;'>{goal_t}</td></tr>"
        f"<tr><td class='muted' style='padding:3px 8px;'>추천 훈련 기간</td>"
        f"<td style='padding:3px 8px;'>"
        f"{rec.get('optimal_min', '?')}~{rec.get('optimal_max', '?')}주 (최솟값 {rec.get('min', '?')}주)"
        f"</td></tr></table>"
        f"<div style='margin:1rem 0 4px;font-size:0.85rem;font-weight:600;'>"
        f"목표 달성 가능률 {pct:.0f}%</div>"
        f"<div style='background:rgba(255,255,255,0.1);border-radius:4px;height:10px;'>"
        f"<div style='width:{max(4, int(pct))}%;background:{bar_c};height:100%;border-radius:4px;'></div></div>"
        + (f"<ul style='margin:0.8rem 0 0;padding-left:1.2rem;'>{warns_html}</ul>" if warns_html else "")
        + f"<p style='margin:0.8rem 0 0;font-size:0.82rem;color:var(--muted);'>"
        f"{_html.escape(r.get('status_summary', ''))}</p></div>"
        f"<form onsubmit='wizardNext(event,3)'>{_hidden(data_out)}"
        f"<div style='display:flex;justify-content:space-between;margin-top:1rem;'>"
        f"<button type='button' onclick='wizardBack()' style='{_BACK}'>← 이전</button>"
        f"<button type='submit' style='{_NEXT}'>확인 →</button>"
        f"</div></form></div>"
    )


def render_step4(data: dict, mode: str = "create") -> str:
    """Step 4: 플랜 요약 + 생성 버튼. edit 모드이면 재생성 여부 체크박스 표시."""
    from src.training.readiness import (
        get_taper_weeks, get_phase_for_week, recommend_weekly_km,
    )
    dist_km = data.get("dist_km", 10.0)
    weeks = int(data.get("plan_weeks") or 12)
    label = data.get("distance_label", "custom")
    vdot = float(data.get("current_vdot") or 40.0)
    taper_w = get_taper_weeks(dist_km)
    phases: dict[str, int] = {}
    km_list: list[float] = []
    for w in range(weeks):
        ph = get_phase_for_week(w, weeks, taper_w)
        phases[ph] = phases.get(ph, 0) + 1
        km_list.append(recommend_weekly_km(vdot, label, ph, w, weeks))
    phase_str = " / ".join(
        f"{k.capitalize()} {v}주" for k, v in phases.items() if v > 0
    )
    km_min = min(km_list) if km_list else 0
    km_max = max(km_list) if km_list else 0
    goal_lines = ""
    if data.get("time_sec"):
        goal_lines += (
            f"<p style='margin:0.3rem 0;font-size:0.88rem;'>"
            f"목표 기록: <strong>{_fmt_time(data['time_sec'])}</strong></p>"
        )
    if data.get("pace_sec"):
        goal_lines += (
            f"<p style='margin:0.3rem 0;font-size:0.88rem;'>"
            f"목표 페이스: <strong>{_fmt_pace(data['pace_sec'])}/km</strong></p>"
        )
    is_edit = mode == "edit" or data.get("_mode") == "edit"
    regen_html = ""
    if is_edit:
        regen_html = (
            f"<label style='display:flex;align-items:center;gap:8px;margin:1rem 0;"
            f"font-size:0.88rem;cursor:pointer;'>"
            f"<input type='checkbox' name='_regen_plan_check' id='wiz-regen-cb'"
            f" style='accent-color:var(--cyan);width:16px;height:16px;'>"
            f"이번 주 훈련 플랜도 재생성 <span class='muted'>(기존 일정 덮어씀)</span></label>"
        )
    submit_label = "✅ 목표 수정 완료" if is_edit else "✅ 플랜 생성"
    confirm_msg = "목표를 수정합니다." if is_edit else "이 설정으로 훈련 계획을 생성합니다."
    return (
        f"<div id='wizard-container'>{_steps(4)}"
        f"<h3 style='margin:0 0 1rem;'>Step 4 — {'목표 수정 확인' if is_edit else '플랜 확인 및 생성'}</h3>"
        f"<div class='card' style='padding:1rem;margin-bottom:1rem;'>"
        f"<h4 style='margin:0 0 0.8rem;'>🎯 {_html.escape(data.get('goal_name', ''))}</h4>"
        f"<p style='margin:0.3rem 0;font-size:0.88rem;'>"
        f"거리: <strong>{dist_km:.1f}km</strong> · "
        f"레이스: <strong>{_html.escape(data.get('race_date', ''))}</strong></p>"
        + goal_lines
        + f"<p style='margin:0.3rem 0;font-size:0.88rem;'>"
        f"훈련 기간: <strong>{weeks}주</strong> ({phase_str})</p>"
        f"<p style='margin:0.3rem 0;font-size:0.88rem;'>"
        f"주간 예상 km: <strong>{km_min:.0f}~{km_max:.0f}km</strong></p></div>"
        f"{regen_html}"
        f"<form method='post' action='/training/wizard/complete'"
        f" onsubmit=\"return confirm('{confirm_msg}');\">"
        f"{_hidden(data)}"
        f"<input type='hidden' id='wiz-regen-hidden' name='_regen_plan_val' value='0'>"
        f"<div style='display:flex;justify-content:space-between;margin-top:1rem;'>"
        f"<button type='button' onclick='wizardBack()' style='{_BACK}'>← 이전</button>"
        f"<button type='submit' style='{_NEXT}'>{submit_label}</button>"
        f"</div></form></div>"
        + (
            "<script>"
            "(function(){var cb=document.getElementById('wiz-regen-cb');"
            "var hd=document.getElementById('wiz-regen-hidden');"
            "if(cb&&hd)cb.addEventListener('change',function(){hd.value=cb.checked?'1':'0';});})();"
            "</script>"
            if is_edit else ""
        )
    )


def wizard_js() -> str:
    """위저드 전용 JS (페이지에 한 번만 삽입)."""
    return """<script>
const _wizHistory = [];
function wizardNext(e, step) {
  e.preventDefault();
  const card = document.getElementById('wizard-card');
  if (card) _wizHistory.push(card.innerHTML);
  const fd = new FormData(e.target);
  fd.append('step', step);
  fetch('/training/wizard/step', {method: 'POST', body: fd})
    .then(r => r.json())
    .then(d => {
      if (d.html && card) { card.innerHTML = d.html; wizardInitStep(); }
    })
    .catch(err => console.error('wizard step error', err));
}
function wizardBack() {
  const card = document.getElementById('wizard-card');
  if (card && _wizHistory.length > 0) {
    card.innerHTML = _wizHistory.pop();
    wizardInitStep();
  } else { window.location.href = '/training'; }
}
function wizardInitStep() {
  const dd = document.getElementById('wiz-dist');
  if (dd) wizDistChange(dd.value);
  const ww = document.getElementById('wiz-weeks');
  if (ww) wizWeeksCheck(ww, parseInt(ww.getAttribute('oninput').match(/,([0-9]+)/)?.[1] || '6'));
}
function wizDistChange(val) {
  const c = document.getElementById('wiz-custom');
  if (c) c.style.display = val === 'custom' ? '' : 'none';
}
function wizWeeksCheck(el, minVal) {
  const w = document.getElementById('wiz-weeks-warn');
  if (w) w.style.display = parseInt(el.value) < (minVal || 6) ? '' : 'none';
}
</script>"""


def render_wizard_page(
    step: int = 1,
    data: dict | None = None,
    mode: str = "create",
    goal_id: int | None = None,
) -> str:
    """Wizard 전체 페이지 (html_page 래퍼)."""
    from src.web.helpers import html_page
    title = "목표 수정" if mode == "edit" else "훈련 계획 시작"
    body = (
        f"<div style='max-width:600px;margin:0 auto;'>"
        f"<div class='card' id='wizard-card'>"
        f"{render_step1(data or {})}"
        f"</div></div>"
        f"{wizard_js()}"
    )
    return html_page(title, body, active_tab="training")
