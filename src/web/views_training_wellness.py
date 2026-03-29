"""훈련탭 — 웰니스/컨디션 카드 렌더러.

S4: render_adjustment_card  (컨디션 조정, 하위 호환)
S4.5: render_checkin_card   (어제 훈련 체크인)
S4.6: render_interval_prescription_card (인터벌 처방)
"""
from __future__ import annotations

import html as _html

from src.web.views_training_shared import _TYPE_STYLE


def _esc(s: str) -> str:
    return _html.escape(str(s))


# ── S4: 컨디션 조정 ───────────────────────────────────────────────────

def render_adjustment_card(adj: dict | None, cirs_val: float | None = None,
                           utrs_val: float | None = None,
                           config: dict | None = None, conn=None) -> str:
    """오늘 컨디션 조정 카드 + 웰니스 상세 + CIRS/UTRS 반영."""
    if not adj:
        return ""

    wellness = adj.get("wellness", {})
    fatigue = adj.get("fatigue_level", "low")

    _FATIGUE_KO = {"low": "낮음", "moderate": "보통", "high": "높음"}
    fatigue_ko = _FATIGUE_KO.get(fatigue, fatigue)

    cirs_warning = ""
    if cirs_val is not None and cirs_val >= 75:
        cirs_warning = (
            f"<p style='color:#ff4444;font-weight:600;margin:0 0 6px;'>"
            f"⚠️ CIRS {cirs_val:.0f} — 부상 위험 높음. 훈련 강도를 낮추세요.</p>"
        )
        fatigue_ko = "높음"
    elif cirs_val is not None and cirs_val >= 50:
        cirs_warning = (
            f"<p style='color:#ffaa00;margin:0 0 6px;'>"
            f"CIRS {cirs_val:.0f} — 주의 필요. 워밍업/쿨다운 충실히.</p>"
        )

    utrs_note = ""
    if utrs_val is not None and utrs_val < 40:
        utrs_note = (
            f"<p style='color:#ff4444;margin:0 0 6px;'>"
            f"UTRS {utrs_val:.0f} — 회복이 필요합니다. 가벼운 활동만 권장.</p>"
        )

    well_items = []
    bb = wellness.get("body_battery")
    if bb is not None:
        c = "#00ff88" if bb >= 50 else "#ffaa00" if bb >= 30 else "#ff4444"
        well_items.append(f"<span style='color:{c};'>⚡ BB {bb}</span>")
    ss = wellness.get("sleep_score")
    if ss is not None:
        c = "#00ff88" if ss >= 60 else "#ffaa00" if ss >= 40 else "#ff4444"
        well_items.append(f"<span style='color:{c};'>😴 수면 {ss:.0f}</span>")
    hrv = wellness.get("hrv_value")
    if hrv is not None:
        well_items.append(f"<span style='color:var(--secondary);'>💓 HRV {hrv:.0f}</span>")
    tsb = adj.get("tsb")
    if tsb is not None:
        c = "#00ff88" if tsb > 0 else "#ffaa00" if tsb > -15 else "#ff4444"
        well_items.append(f"<span style='color:{c};'>📊 TSB {tsb:+.1f}</span>")

    wellness_html = (
        "<div style='display:flex;gap:12px;flex-wrap:wrap;margin-top:8px;"
        "font-size:0.82rem;'>" + " ".join(well_items) + "</div>"
    ) if well_items else ""

    if not adj.get("adjusted"):
        color = "#00ff88" if fatigue == "low" and not cirs_warning else "#ffaa00" if not cirs_warning else "#ff4444"
        boost = " 볼륨 부스트 가능! 💪" if adj.get("volume_boost") and not cirs_warning else ""
        msg = "계획대로 진행하세요." if not cirs_warning else "컨디션을 확인하세요."
        return (
            f"<div class='card' style='border-left:4px solid {color};'>"
            "<h3 style='margin:0 0 8px;'>오늘 컨디션</h3>"
            + cirs_warning + utrs_note
            + f"<p style='margin:0;'>피로도: <strong>{fatigue_ko}</strong> — {msg}{boost}</p>"
            + wellness_html
            + "</div>"
        )

    orig = adj.get("original_type", "")
    new_type = adj.get("adjusted_type", "")
    reason = adj.get("adjustment_reason", "")
    color = "#ff4444" if fatigue == "high" or cirs_warning else "#ffaa00"
    orig_label = _TYPE_STYLE.get(orig, ("", orig, ""))[1]
    new_label = _TYPE_STYLE.get(new_type, ("", new_type, ""))[1]

    return (
        f"<div class='card' style='border-left:4px solid {color};'>"
        "<h3 style='margin:0 0 8px;'>⚠️ 오늘 컨디션 조정</h3>"
        + cirs_warning + utrs_note
        + f"<p style='margin:0 0 4px;'>피로도: <strong>{fatigue_ko}</strong></p>"
        f"<p style='margin:0 0 4px;'>{orig_label} → <strong>{new_label}</strong>으로 변경</p>"
        + (f"<p class='muted' style='margin:0;font-size:0.85rem;'>{_esc(reason)}</p>"
           if reason else "")
        + wellness_html
        + "</div>"
    )


# ── S4.5: 어제 훈련 체크인 카드 ───────────────────────────────────────

def render_checkin_card(yesterday_pending: dict | None) -> str:
    """어제 미확인 훈련 체크인 카드.

    completed=0인 어제 계획이 있을 때만 표시.
    AJAX 방식: 완료 시 카드 제거, 건너뜀 시 재조정 diff 인라인 표시.
    """
    if not yesterday_pending:
        return ""

    wid = yesterday_pending["id"]
    wtype = yesterday_pending["workout_type"]
    dist = yesterday_pending.get("distance_km")
    d = yesterday_pending["date"]

    style_info = _TYPE_STYLE.get(wtype, _TYPE_STYLE["easy"])
    _, label_ko, icon = style_info

    dist_str = f" {dist:.1f}km" if dist else ""
    day_str = f"{d[5:7]}/{d[8:10]}"
    _grad = style_info[0]
    type_color = _grad.split(",")[1].strip() if "," in _grad else "#ffaa00"

    card_id = f"checkin-card-{wid}"

    script = f"""
<script>
(function() {{
  var card = document.getElementById('{card_id}');

  function _typeLabel(t) {{
    var m = {{easy:'이지런',tempo:'템포런',interval:'인터벌',long:'롱런',
              rest:'휴식',recovery:'회복조깅',race:'레이스'}};
    return m[t] || t;
  }}

  function _renderDiff(data) {{
    var html = '<div style="margin-top:14px;border-top:1px solid rgba(255,255,255,0.1);padding-top:12px;">';
    html += '<p style="margin:0 0 8px;font-size:0.88rem;color:#ffaa00;font-weight:600;">📋 재조정 결과</p>';
    html += '<p style="margin:0 0 10px;font-size:0.85rem;color:var(--muted);">' + data.message + '</p>';

    if (data.changes && data.changes.length > 0) {{
      html += '<table style="width:100%;border-collapse:collapse;font-size:0.82rem;margin-bottom:8px;">';
      html += '<tr><th style="text-align:left;color:var(--muted);padding:3px 6px;">날짜</th>'
            + '<th style="text-align:left;color:var(--muted);padding:3px 6px;">변경 전</th>'
            + '<th style="text-align:left;color:var(--muted);padding:3px 6px;">변경 후</th></tr>';
      data.changes.forEach(function(c) {{
        html += '<tr>'
              + '<td style="padding:3px 6px;color:#fff;">' + (c.date || '') + '</td>'
              + '<td style="padding:3px 6px;color:#aaa;">' + _typeLabel(c.before) + '</td>'
              + '<td style="padding:3px 6px;color:#00ff88;font-weight:600;">→ ' + _typeLabel(c.after) + '</td>'
              + '</tr>';
      }});
      html += '</table>';
    }}

    if (data.warnings && data.warnings.length > 0) {{
      data.warnings.forEach(function(w) {{
        html += '<p style="margin:4px 0;font-size:0.82rem;color:#ffaa00;">⚠️ ' + w + '</p>';
      }});
    }}

    html += '<button onclick="document.getElementById(\\'{card_id}\\').remove();" '
          + 'style="margin-top:10px;background:none;border:none;color:var(--muted);'
          + 'font-size:0.8rem;cursor:pointer;padding:0;">✕ 닫기</button>';
    html += '</div>';
    return html;
  }}

  document.getElementById('checkin-confirm-{wid}').addEventListener('click', function() {{
    this.disabled = true;
    fetch('/training/workout/{wid}/confirm', {{
      method: 'POST',
      headers: {{'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}}
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function() {{
      card.style.transition = 'opacity 0.3s';
      card.style.opacity = '0';
      setTimeout(function() {{ card.remove(); }}, 300);
    }})
    .catch(function() {{ location.reload(); }});
  }});

  document.getElementById('checkin-skip-{wid}').addEventListener('click', function() {{
    this.disabled = true;
    document.getElementById('checkin-confirm-{wid}').disabled = true;
    fetch('/training/workout/{wid}/skip', {{
      method: 'POST',
      headers: {{'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}}
    }})
    .then(function(r) {{ return r.json(); }})
    .then(function(data) {{
      var btnRow = document.getElementById('checkin-btns-{wid}');
      if (btnRow) btnRow.style.display = 'none';
      card.querySelector('.checkin-question').style.display = 'none';
      card.insertAdjacentHTML('beforeend', _renderDiff(data));
    }})
    .catch(function() {{ location.reload(); }});
  }});
}})();
</script>"""

    return (
        f"<div class='card' id='{card_id}' style='border-left:4px solid #ffaa00;'>"
        "<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>"
        "<span style='font-size:1.1rem;'>📋</span>"
        "<h3 style='margin:0;font-size:0.95rem;'>어제 훈련 확인</h3>"
        f"<span class='muted' style='font-size:0.78rem;'>({day_str})</span>"
        "</div>"
        f"<p class='checkin-question' style='margin:0 0 12px;font-size:0.9rem;'>"
        f"어제 계획된 <strong style='color:{type_color};'>"
        f"{icon} {label_ko}{dist_str}</strong>을 완료했나요?"
        "</p>"
        f"<div id='checkin-btns-{wid}' style='display:flex;gap:8px;flex-wrap:wrap;'>"
        f"<button id='checkin-confirm-{wid}' "
        "style='background:rgba(0,255,136,0.2);border:1px solid rgba(0,255,136,0.4);"
        "color:#00ff88;padding:6px 18px;border-radius:20px;font-size:0.85rem;cursor:pointer;font-weight:600;'>"
        "✅ 완료했어요</button>"
        f"<button id='checkin-skip-{wid}' "
        "style='background:rgba(255,68,68,0.15);border:1px solid rgba(255,68,68,0.3);"
        "color:#ff6b6b;padding:6px 18px;border-radius:20px;font-size:0.85rem;cursor:pointer;'>"
        "❌ 건너뜀</button>"
        "</div>"
        "</div>"
        + script
    )


# ── S4.6: 인터벌 처방 카드 ────────────────────────────────────────────

def render_interval_prescription_card(workout: dict) -> str:
    """인터벌 처방 상세 카드 렌더링.

    workout['interval_prescription'] JSON에서 처방 정보 표시.
    논문 출처: Billat 2001, Buchheit & Laursen 2013.
    """
    import json

    if not workout or workout.get("workout_type") != "interval":
        return ""
    rx_json = workout.get("interval_prescription")
    if not rx_json:
        return ""

    try:
        rx = json.loads(rx_json)
    except (json.JSONDecodeError, TypeError):
        return ""

    rep_m = rx.get("rep_m", 0)
    sets = rx.get("sets", 0)
    rest_sec = rx.get("rest_sec", 0)
    i_pace = rx.get("interval_pace", 0)
    rec_pace = rx.get("recovery_pace", 0)
    total_m = rx.get("total_volume_m", 0)
    session_min = rx.get("session_duration_min", 0)
    warning = rx.get("warning")

    def fmt_pace(sec_km: int) -> str:
        if not sec_km:
            return "—"
        return f"{sec_km // 60}:{sec_km % 60:02d}/km"

    def fmt_sec(sec: int) -> str:
        if not sec:
            return "—"
        m, s = divmod(sec, 60)
        return f"{m}:{s:02d}"

    warning_html = ""
    if warning:
        warning_html = (
            f"<p style='margin:8px 0 0;font-size:0.78rem;color:#ffaa00;"
            f"background:rgba(255,170,0,0.1);padding:6px 10px;border-radius:6px;'>"
            f"⚠️ {warning}</p>"
        )

    buchheit_range = rx.get("buchheit_range", {})
    vol_min = buchheit_range.get("vol_min_km", 0)
    vol_max = buchheit_range.get("vol_max_km", 0)
    intensity_pct = buchheit_range.get("intensity_pct", 0)

    items = [
        ("반복 구성", f"{rep_m}m × {sets}세트"),
        ("반복 페이스", fmt_pace(i_pace)),
        ("세트 간 휴식", f"{fmt_sec(rest_sec)} (회복 조깅 {fmt_pace(rec_pace)})"),
        ("총 인터벌 거리", f"{total_m/1000:.1f}km"),
        ("예상 세션 시간", f"~{session_min}분 (웜업+인터벌+쿨다운)"),
    ]
    rows_html = "".join(
        f"<div style='display:flex;justify-content:space-between;padding:5px 0;"
        f"border-bottom:1px solid rgba(255,255,255,0.06);font-size:0.85rem;'>"
        f"<span class='muted'>{k}</span><span style='font-weight:500;'>{v}</span></div>"
        for k, v in items
    )

    return (
        "<div class='card' style='border-left:3px solid rgba(255,68,68,0.5);"
        "margin-top:0.8rem;'>"
        "<div style='display:flex;align-items:center;gap:8px;margin-bottom:10px;'>"
        "<span style='font-size:1rem;'>🔴</span>"
        "<h3 style='margin:0;font-size:0.88rem;font-weight:600;'>인터벌 처방</h3>"
        f"<span class='muted' style='font-size:0.75rem;margin-left:auto;'>"
        f"~{intensity_pct}% vVO2max · 목표볼륨 {vol_min}~{vol_max}km"
        f"</span></div>"
        f"{rows_html}"
        f"{warning_html}"
        "<p style='margin:8px 0 0;font-size:0.72rem;color:var(--muted);'>"
        "출처: Buchheit &amp; Laursen 2013 세트 구성 · Billat 2001 휴식 비율</p>"
        "</div>"
    )
