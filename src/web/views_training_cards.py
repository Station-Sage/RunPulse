"""훈련 계획 뷰 — 카드 렌더러 (S1~S3).

S1: render_header_actions  (헤더 액션 버튼)
S2: render_goal_card       (활성 목표 카드)
S3: render_weekly_summary  (주간 요약)

하위 모듈 re-export (기존 import 경로 호환):
  S4~S4.6 → views_training_wellness
  S5      → views_training_week
  S6~S7   → views_training_plan_ui
"""
from __future__ import annotations

from datetime import date

from src.web.helpers import fmt_pace, fmt_duration, no_data_card
from src.web.views_training_shared import _TYPE_STYLE, _TYPE_BG, _esc

# ── 하위 모듈 re-export (기존 import 경로 호환) ──────────────────────
from src.web.views_training_wellness import (  # noqa: F401
    render_adjustment_card,
    render_checkin_card,
    render_interval_prescription_card,
)
from src.web.views_training_condition import render_condition_ai_card  # noqa: F401
from src.web.views_training_week import render_week_calendar  # noqa: F401
from src.web.views_training_plan_ui import (  # noqa: F401
    render_ai_recommendation,
    render_plan_overview,
    render_sync_status,
)

__all__ = [
    # S1~S3 (이 파일)
    "render_header_actions",
    "render_goal_card",
    "_render_goal_card_actions",
    "render_weekly_summary",
    # re-exports
    "render_adjustment_card",
    "render_checkin_card",
    "render_condition_ai_card",
    "render_interval_prescription_card",
    "render_week_calendar",
    "render_ai_recommendation",
    "render_plan_overview",
    "render_sync_status",
]


# ── S1: 헤더 액션 ─────────────────────────────────────────────────────

def render_header_actions(has_plan: bool) -> str:
    """타이틀 영역 액션 버튼 (내보내기 드롭다운 + 플랜 생성)."""
    label = "🗓️ 재생성" if has_plan else "🗓️ 플랜 생성"

    _dd_item = (
        "display:block;width:100%;text-align:left;background:none;border:none;"
        "color:rgba(255,255,255,0.85);padding:8px 14px;font-size:13px;"
        "cursor:pointer;white-space:nowrap;"
    )
    export_dd = ""
    if has_plan:
        export_dd = (
            "<div style='position:relative;' data-rp-export>"
            "<button onclick=\"var d=this.nextElementSibling;"
            "d.style.display=d.style.display==='block'?'none':'block';"
            "event.stopPropagation();\" "
            "style='background:rgba(255,255,255,0.1);border:none;color:#fff;"
            "padding:8px 16px;border-radius:20px;cursor:pointer;font-size:13px;'>"
            "📤 내보내기 ▾</button>"
            "<div data-rp-export-menu style='display:none;position:absolute;top:calc(100% + 6px);"
            "right:0;background:#1e2a35;border:1px solid rgba(255,255,255,0.15);"
            "border-radius:12px;padding:6px 0;min-width:200px;z-index:200;"
            "box-shadow:0 8px 24px rgba(0,0,0,0.5);'>"
            "<form method='POST' action='/training/push-garmin' style='margin:0;'>"
            f"<button type='submit' style='{_dd_item}'>⌚ Garmin 워크아웃</button></form>"
            "<form method='POST' action='/training/push-caldav' style='margin:0;'>"
            f"<button type='submit' style='{_dd_item}'>📅 CalDAV 캘린더</button></form>"
            f"<a href='/training/export.ics' style='{_dd_item}text-decoration:none;display:block;'>"
            "📁 ICS 파일 다운로드</a>"
            "<button onclick=\"navigator.clipboard&&navigator.clipboard.writeText("
            "window.location.href).then(function(){alert('링크 복사됨');});\" "
            f"style='{_dd_item}border-top:1px solid rgba(255,255,255,0.1);margin-top:4px;"
            "padding-top:10px;'>🔗 링크 복사</button>"
            "</div></div>"
            "<script>if(!window._rpExportInit){"
            "window._rpExportInit=true;"
            "document.addEventListener('click',function(e){"
            "if(!e.target.closest('[data-rp-export]')){"
            "var m=document.querySelector('[data-rp-export-menu]');"
            "if(m)m.style.display='none';}});}</script>"
        )

    return (
        "<div style='display:flex;justify-content:space-between;align-items:center;"
        "padding:16px 0;border-bottom:1px solid var(--card-border);margin-bottom:20px;'>"
        "<div style='font-size:18px;font-weight:bold;'>훈련 계획</div>"
        "<div style='display:flex;gap:10px;flex-wrap:wrap;align-items:center;'>"
        + export_dd
        + ("<a href='/training/fullplan' style='background:rgba(255,255,255,0.08);"
           "color:rgba(255,255,255,0.7);border:1px solid rgba(255,255,255,0.15);"
           "padding:8px 14px;border-radius:20px;font-size:13px;text-decoration:none;"
           "white-space:nowrap;'>📋 전체 일정</a>"
           if has_plan else "")
        + "<form method='POST' action='/training/generate' style='margin:0;'"
        " onsubmit=\"return confirm('전체 훈련 계획을 " + ("재" if has_plan else "") + "생성합니다. 기존 자동 생성 계획은 덮어씁니다.')\">"
        f"<button type='submit' style='background:linear-gradient(135deg,#00d4ff,#00ff88);"
        f"color:#000;border:none;padding:8px 16px;border-radius:20px;font-size:13px;"
        f"font-weight:bold;cursor:pointer;'>{label}</button></form>"
        "</div></div>"
    )


# ── S2: 목표 카드 ─────────────────────────────────────────────────────

def render_goal_card(
    goal: dict | None,
    utrs_val: float | None = None,
    today_workout: dict | None = None,
) -> str:
    """활성 목표 + UTRS 미니 표시 + 오늘 워크아웃 ✏️/✕/✓ 액션 버튼."""
    if not goal:
        return (
            "<div class='card' style='text-align:center;padding:1.5rem;'>"
            "<p class='muted' style='margin-bottom:1rem;'>설정된 목표가 없습니다.</p>"
            "<a href='/training/wizard'"
            " style='display:inline-block;background:linear-gradient(135deg,#00d4ff,#00ff88);"
            "color:#000;text-decoration:none;padding:0.6rem 1.4rem;border-radius:20px;"
            "font-weight:bold;font-size:0.9rem;'>🗓️ 훈련 계획 시작하기</a>"
            "</div>"
        )

    name = goal.get("name", "")
    dist = goal.get("distance_km", 0)
    race_date = goal.get("race_date")
    target_time = goal.get("target_time_sec")
    target_pace = goal.get("target_pace_sec_km")
    goal_id = goal.get("id")

    dday = ""
    if race_date:
        try:
            days_left = (date.fromisoformat(race_date) - date.today()).days
            if days_left > 0:
                dday = f"D-{days_left}"
            elif days_left == 0:
                dday = "D-Day!"
            else:
                dday = "완료"
        except ValueError:
            pass

    pace_str = fmt_pace(target_pace) + "/km" if target_pace else ""
    time_str = fmt_duration(target_time) if target_time else ""
    target_info = " / ".join(filter(None, [time_str, pace_str]))

    utrs_html = ""
    if utrs_val is not None:
        color = "#00ff88" if utrs_val >= 70 else "#ffaa00" if utrs_val >= 40 else "#ff4444"
        utrs_html = (
            f"<div style='display:flex;align-items:center;gap:6px;margin-top:8px;'>"
            f"<span style='font-size:0.75rem;color:var(--muted);'>훈련 준비도</span>"
            f"<span style='font-size:1rem;font-weight:bold;color:{color};'>"
            f"UTRS {utrs_val:.0f}</span></div>"
        )

    action_html = _render_goal_card_actions(goal_id, today_workout)

    return (
        "<div class='card' style='border-left:4px solid #00d4ff;'>"
        "<div style='display:flex;justify-content:space-between;align-items:flex-start;'>"
        f"<div><h3 style='margin:0 0 4px;'>🎯 {_esc(name)}</h3>"
        f"<span class='muted' style='font-size:0.85rem;'>{dist:.1f}km"
        + (f" · {target_info}" if target_info else "")
        + (f" · {race_date}" if race_date else "")
        + "</span>"
        + utrs_html
        + "</div>"
        + "<div style='display:flex;flex-direction:column;align-items:flex-end;gap:8px;'>"
        + (f"<span style='font-size:1.8rem;font-weight:bold;color:#00d4ff;'>{dday}</span>"
           if dday else "")
        + (f"<a href='/training/wizard?mode=edit&goal_id={goal_id}'"
           " title='목표 수정'"
           " style='background:rgba(255,255,255,0.08);border:1px solid rgba(255,255,255,0.15);"
           "color:rgba(255,255,255,0.7);font-size:0.8rem;padding:4px 10px;border-radius:12px;"
           "text-decoration:none;white-space:nowrap;cursor:pointer;'>✏️ 목표 수정</a>"
           if goal_id else "")
        + "</div>"
        + "</div>"
        + action_html
        + "</div>"
    )


def _render_goal_card_actions(
    goal_id: int | None,
    today_workout: dict | None,
) -> str:
    """목표 카드 하단 — 오늘 워크아웃 ✕/✓ 버튼 + 인라인 알림 영역."""
    if not today_workout:
        return ""

    wid = today_workout.get("id")
    if not wid:
        return ""

    completed = today_workout.get("completed", 0)
    wtype = today_workout.get("workout_type", "easy")
    wdist = today_workout.get("distance_km")
    label = f"{wtype}" + (f" {wdist:.1f}km" if wdist else "")

    if completed == 1:
        return (
            "<div style='border-top:1px solid rgba(255,255,255,0.08);margin-top:10px;"
            "padding-top:10px;display:flex;align-items:center;gap:10px;flex-wrap:wrap;'>"
            f"<span style='font-size:0.82rem;color:#00ff88;'>✓ 오늘 {_esc(label)} 완료</span>"
            "</div>"
        )
    if completed == -1:
        return (
            "<div style='border-top:1px solid rgba(255,255,255,0.08);margin-top:10px;"
            "padding-top:10px;'>"
            f"<span style='font-size:0.82rem;color:var(--muted);'>— 오늘 {_esc(label)} 건너뜀</span>"
            "</div>"
        )

    _btn = (
        "border:none;border-radius:12px;font-size:0.82rem;padding:5px 12px;"
        "cursor:pointer;font-weight:600;"
    )
    return (
        "<div id='rp-goal-actions' style='border-top:1px solid rgba(255,255,255,0.08);"
        "margin-top:10px;padding-top:10px;'>"
        f"<span style='font-size:0.82rem;color:var(--muted);margin-right:10px;'>"
        f"오늘: {_esc(label)}</span>"
        f"<button onclick='rpGoalConfirm({wid})'"
        f" style='{_btn}background:rgba(0,255,136,0.2);color:#00ff88;margin-right:6px;'"
        " title='오늘 훈련 완료 확인'>✓ 완료</button>"
        f"<button onclick='rpGoalSkip({wid})'"
        f" style='{_btn}background:rgba(255,68,68,0.15);color:#ff6b6b;'"
        " title='오늘 훈련 건너뜀'>✕ 건너뜀</button>"
        "<div id='rp-goal-msg' style='margin-top:8px;font-size:0.82rem;display:none;'></div>"
        "</div>"
        + _goal_card_js()
    )


def _goal_card_js() -> str:
    """목표 카드 ✓/✕ AJAX JS (페이지당 1번만 삽입)."""
    return """<script>
if(!window._rpGoalCardInit){window._rpGoalCardInit=true;
function _rpShowGoalMsg(html,color){
  var el=document.getElementById('rp-goal-msg');
  if(!el)return;
  el.innerHTML=html;el.style.color=color||'var(--cyan)';el.style.display='block';
}
function _rpGoalSpinner(on){
  var act=document.getElementById('rp-goal-actions');
  if(!act)return;
  var btns=act.querySelectorAll('button');
  btns.forEach(function(b){b.disabled=on;});
  if(on)_rpShowGoalMsg('<span>⏳ 처리 중...</span>','var(--muted)');
}
function rpGoalConfirm(wid){
  _rpGoalSpinner(true);
  fetch('/training/workout/'+wid+'/confirm',{
    method:'POST',
    headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
  }).then(function(r){return r.json();})
  .then(function(d){
    if(d.ok){
      var act=document.getElementById('rp-goal-actions');
      var matched=d.matched;
      var actInfo=d.activity_summary?(' — '+d.activity_summary):'';
      if(matched){
        if(act)act.innerHTML='<span style="color:#00ff88;font-size:0.85rem;">✓ 완료 & 활동 매칭됨'+actInfo+'</span>';
      } else {
        if(act)act.innerHTML=(
          '<span style="color:#00ff88;font-size:0.85rem;">✓ 완료 기록됨</span>'
          +' <span style="color:var(--muted);font-size:0.8rem;">실제 활동 미매칭 — 동기화 후 자동 연결됩니다</span>'
        );
      }
    } else {
      _rpGoalSpinner(false);
      _rpShowGoalMsg('오류: '+(d.error||'알 수 없음'),'#ff6b6b');
    }
  }).catch(function(){
    _rpGoalSpinner(false);
    _rpShowGoalMsg('네트워크 오류','#ff6b6b');
  });
}
function rpGoalSkip(wid){
  if(!confirm('오늘 훈련을 건너뜁니까? 잔여 주간 계획이 자동 재조정됩니다.'))return;
  _rpGoalSpinner(true);
  fetch('/training/workout/'+wid+'/skip',{
    method:'POST',
    headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
  }).then(function(r){return r.json();})
  .then(function(d){
    var msg=d.message||'건너뜀 처리 완료';
    var changes=d.changes&&d.changes.length?('<br><span style="font-size:0.78rem;">재조정: '+d.changes.join(' / ')+'</span>'):'';
    var act=document.getElementById('rp-goal-actions');
    if(act)act.innerHTML='<span style="color:#ffaa00;font-size:0.85rem;">— '+msg+changes+'</span>';
  }).catch(function(){
    _rpGoalSpinner(false);
    _rpShowGoalMsg('네트워크 오류','#ff6b6b');
  });
}
}
</script>"""


# ── S3: 주간 요약 (4칸 그리드) ────────────────────────────────────────

def render_weekly_summary(
    workouts: list[dict],
    utrs_val: float | None = None,
) -> str:
    """주간 요약: 완료율 / 목표km / 목표시간 / UTRS."""
    if not workouts:
        return ""

    non_rest = [w for w in workouts if w.get("workout_type") != "rest"]
    total_train = len(non_rest)
    completed = sum(1 for w in non_rest if w.get("completed"))
    total_km = sum(w.get("distance_km") or 0 for w in workouts)

    total_sec = 0
    for w in workouts:
        d = w.get("distance_km") or 0
        p_avg = None
        p_min = w.get("target_pace_min")
        p_max = w.get("target_pace_max")
        if p_min and p_max:
            p_avg = (p_min + p_max) / 2
        if d and p_avg:
            total_sec += d * p_avg
    hours = total_sec / 3600
    time_str = f"{hours:.1f}" if hours else "—"

    comp_pct = int(completed / total_train * 100) if total_train else 0
    km_pct = min(100, int(total_km / max(total_km, 1) * 100)) if total_km else 0
    utrs_pct = int(utrs_val) if utrs_val is not None else 0

    return (
        "<div class='card'>"
        "<div style='display:flex;align-items:center;gap:10px;margin-bottom:16px;'>"
        "<div style='width:4px;height:20px;background:linear-gradient(135deg,#00d4ff,#00ff88);"
        "border-radius:2px;'></div>"
        "<span style='font-size:16px;font-weight:bold;'>이번 주 요약</span></div>"
        "<div style='display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));"
        "gap:14px;'>"
        + _summary_stat("훈련 완료", f"{completed}/{total_train}", comp_pct)
        + _summary_stat("목표 km", f"{total_km:.1f}", km_pct)
        + _summary_stat("목표 시간", f"{time_str}h", min(100, int(hours / max(hours, 0.1) * 100)))
        + _summary_stat("UTRS", f"{utrs_val:.0f}" if utrs_val is not None else "—", utrs_pct)
        + "</div></div>"
    )


def _summary_stat(label: str, value: str, pct: int) -> str:
    return (
        "<div style='background:rgba(255,255,255,0.05);border-radius:16px;"
        "padding:18px;text-align:center;'>"
        f"<div style='font-size:24px;font-weight:bold;color:#00d4ff;'>{value}</div>"
        f"<div style='font-size:11px;color:rgba(255,255,255,0.6);margin-top:6px;'>{label}</div>"
        f"<div style='height:4px;background:rgba(255,255,255,0.1);border-radius:2px;"
        f"margin-top:10px;overflow:hidden;'>"
        f"<div style='height:100%;width:{pct}%;background:linear-gradient(90deg,#00d4ff,#00ff88);"
        f"border-radius:2px;'></div></div></div>"
    )
