"""훈련 목표 관리 패널 렌더러 (Phase G: G-1 ~ G-4).

render_goals_panel()        — G-1 목표 리스트 (수행률 포함)
render_goal_detail_html()   — G-2 드릴다운 (주차별 수행도 + G-3 삭제 + G-4 가져오기)
"""
from __future__ import annotations

import html as _html
from datetime import date

from src.web.helpers import fmt_duration, fmt_pace

_STATUS_BADGE: dict[str, str] = {
    "active": (
        "<span style='background:rgba(0,212,255,0.2);color:#00d4ff;"
        "font-size:10px;padding:2px 8px;border-radius:10px;'>활성</span>"
    ),
    "completed": (
        "<span style='background:rgba(0,255,136,0.15);color:#00ff88;"
        "font-size:10px;padding:2px 8px;border-radius:10px;'>완료</span>"
    ),
    "cancelled": (
        "<span style='background:rgba(255,255,255,0.1);color:var(--muted);"
        "font-size:10px;padding:2px 8px;border-radius:10px;'>취소</span>"
    ),
}


# ── G-1: 목표 리스트 ─────────────────────────────────────────────────────

def render_goals_panel(goals: list[dict]) -> str:
    """목표 관리 패널 (접이식 details).

    Args:
        goals: load_goals_with_stats() 반환값 (completed_count, total_count 포함).
    """
    has_active = any(g.get("status") == "active" for g in goals)
    open_attr = "" if has_active else " open"

    items = (
        "".join(_render_goal_item(g) for g in goals)
        if goals
        else "<p class='muted' style='padding:8px 0;'>설정된 목표가 없습니다.</p>"
    )
    add_btn = (
        "<div style='margin-top:12px;padding-top:12px;"
        "border-top:1px solid rgba(255,255,255,0.08);'>"
        "<a href='/training/wizard' style='display:inline-flex;align-items:center;gap:6px;"
        "background:linear-gradient(135deg,#00d4ff,#00ff88);color:#000;text-decoration:none;"
        "padding:7px 16px;border-radius:20px;font-weight:bold;font-size:13px;'>"
        "🗓️ 새 목표 만들기</a></div>"
    )
    return (
        f"<details style='margin-bottom:16px;'{open_attr}>"
        "<summary style='cursor:pointer;background:rgba(255,255,255,0.05);"
        "border-radius:12px;padding:12px 16px;font-size:14px;font-weight:600;"
        "list-style:none;'>🎯 목표 관리</summary>"
        "<div class='card' style='margin-top:8px;'>"
        + items + add_btn + _goals_js()
        + "</div></details>"
    )


def _render_goal_item(g: dict) -> str:
    """목표 1개 행 (클릭 → 드릴다운 AJAX)."""
    gid = g.get("id")
    name = _html.escape(g.get("name") or "")
    dist = g.get("distance_km", 0)
    race_date = g.get("race_date") or ""
    status = g.get("status", "active")
    target_time = g.get("target_time_sec")
    target_pace = g.get("target_pace_sec_km")
    completed = g.get("completed_count", 0)
    total = g.get("total_count", 0)
    pct = int(completed / total * 100) if total > 0 else 0

    # D-day
    dday = ""
    if race_date:
        try:
            days_left = (date.fromisoformat(race_date) - date.today()).days
            if days_left > 0:
                dday = f"D-{days_left}"
            elif days_left == 0:
                dday = "D-Day!"
            else:
                dday = f"D+{abs(days_left)}"
        except ValueError:
            pass

    badge = _STATUS_BADGE.get(status, "")
    parts: list[str] = [f"{dist:.1f}km"]
    if target_time:
        parts.append(fmt_duration(target_time))
    if target_pace:
        parts.append(fmt_pace(target_pace) + "/km")
    if race_date:
        parts.append(race_date)
    meta = " · ".join(parts)

    bar_color = "#00ff88" if pct >= 80 else "#ffaa00" if pct >= 50 else "#00d4ff"
    progress_html = ""
    if total > 0:
        progress_html = (
            f"<div style='margin-top:4px;background:rgba(255,255,255,0.1);"
            f"border-radius:4px;height:4px;'>"
            f"<div style='width:{pct}%;background:{bar_color};height:4px;"
            f"border-radius:4px;'></div></div>"
            f"<span style='font-size:9px;color:var(--muted);'>"
            f"{completed}/{total} 완료 {pct}%</span>"
        )

    edit_link = ""
    if status == "active" and gid:
        edit_link = (
            f"<a href='/training/wizard?mode=edit&goal_id={gid}' title='목표 수정' "
            "style='font-size:11px;color:rgba(255,255,255,0.5);text-decoration:none;"
            "padding:3px 8px;border:1px solid rgba(255,255,255,0.1);"
            "border-radius:10px;'>✏️</a>"
        )

    # 취소된 목표: 삭제 버튼
    cancel_delete_btn = ""
    if status == "cancelled" and gid:
        cancel_delete_btn = (
            f"<button onclick='event.stopPropagation();rpGoalDeleteEntry({gid})' "
            "title='목표 기록 삭제' "
            "style='background:rgba(255,68,68,0.15);color:#ff6b6b;"
            "border:1px solid rgba(255,68,68,0.3);"
            "padding:3px 8px;border-radius:10px;font-size:11px;cursor:pointer;'>"
            "삭제</button>"
        )

    return (
        f"<div id='goal-row-{gid}'>"
        f"<div onclick='rpGoalToggle({gid})' "
        "style='cursor:pointer;display:flex;justify-content:space-between;"
        "align-items:flex-start;padding:10px 2px;"
        "border-bottom:1px solid rgba(255,255,255,0.06);' "
        f"onmouseover=\"this.style.background='rgba(255,255,255,0.03)'\" "
        f"onmouseout=\"this.style.background=''\">"
        "<div style='flex:1;min-width:0;'>"
        "<div style='display:flex;align-items:center;gap:8px;flex-wrap:wrap;'>"
        f"<span style='font-weight:600;'>{name}</span>{badge}</div>"
        f"<div style='font-size:11px;color:var(--muted);margin-top:2px;'>{meta}</div>"
        + progress_html
        + "</div>"
        "<div style='display:flex;align-items:center;gap:8px;margin-left:12px;"
        "flex-shrink:0;'>"
        + (f"<span style='font-size:1rem;font-weight:bold;color:#00d4ff;"
           f"white-space:nowrap;'>{dday}</span>" if dday else "")
        + edit_link
        + cancel_delete_btn
        + f"<span id='goal-arrow-{gid}' "
          "style='color:var(--muted);font-size:11px;'>▼</span>"
        + "</div></div>"
        f"<div id='goal-detail-{gid}' style='display:none;padding:6px 0;'></div>"
        "</div>"
    )


# ── G-2/G-3/G-4: 드릴다운 HTML ──────────────────────────────────────────

def render_goal_detail_html(
    goal: dict,
    weeks: list[dict],
    all_goals: list[dict],
) -> str:
    """드릴다운 HTML partial — AJAX 응답용.

    Args:
        goal: 해당 목표 dict (id, status 포함).
        weeks: load_goal_weeks() 반환값.
        all_goals: 가져오기 소스 선택용 전체 목표 목록.
    """
    gid = goal.get("id")
    status = goal.get("status", "active")

    # 주차별 수행도 테이블
    week_rows = ""
    for i, w in enumerate(weeks, 1):
        ws = w["week_start"]
        km = w.get("total_km", 0.0)
        cnt = w.get("total_count", 0)
        done = w.get("completed_count", 0)
        is_cur = w.get("is_current", False)
        bar_w = int(done / cnt * 100) if cnt > 0 else 0
        bar_c = "#00ff88" if bar_w >= 80 else "#ffaa00" if bar_w >= 50 else "#00d4ff"
        cur_mark = (" <span style='color:#00d4ff;font-size:9px;'>◀</span>"
                    if is_cur else "")
        week_rows += (
            f"<tr style='border-bottom:1px solid rgba(255,255,255,0.04);'>"
            f"<td style='padding:4px 8px;font-size:11px;color:var(--muted);"
            f"white-space:nowrap;'>W{i} {ws.strftime('%m/%d')}{cur_mark}</td>"
            f"<td style='padding:4px 8px;font-size:11px;'>{km:.1f}km</td>"
            f"<td style='padding:4px 8px;font-size:11px;'>{done}/{cnt}</td>"
            f"<td style='padding:4px 8px;width:72px;'>"
            f"<div style='background:rgba(255,255,255,0.08);border-radius:3px;height:5px;'>"
            f"<div style='width:{bar_w}%;background:{bar_c};height:5px;"
            f"border-radius:3px;'></div></div></td></tr>"
        )

    no_data = ("<tr><td colspan='4' style='padding:10px;text-align:center;"
               "color:var(--muted);font-size:11px;'>플랜 데이터 없음</td></tr>")
    table_html = (
        "<table style='width:100%;border-collapse:collapse;margin-bottom:10px;'>"
        "<thead><tr>"
        + "".join(
            f"<th style='padding:4px 8px;font-size:10px;color:var(--muted);"
            f"text-align:left;font-weight:500;'>{h}</th>"
            for h in ["주차", "거리", "완료", "달성도"]
        )
        + "</tr></thead><tbody>"
        + (week_rows or no_data)
        + "</tbody></table>"
    )

    # G-3: 목표 취소 + 계획 삭제 버튼
    delete_btn = ""
    delete_plan_btn = ""
    if status == "active" and gid:
        delete_btn = (
            f"<button onclick='rpGoalDelete({gid})' title='목표 취소 (플랜 유지)' "
            "style='background:rgba(255,68,68,0.15);color:#ff6b6b;"
            "border:1px solid rgba(255,68,68,0.3);"
            "padding:5px 12px;border-radius:12px;font-size:11px;cursor:pointer;'>"
            "🗑️ 목표 취소</button>"
        )
        delete_plan_btn = (
            f"<button onclick='rpDeletePlan({gid})' title='AI 자동 생성 훈련 계획 삭제' "
            "style='background:rgba(255,100,0,0.15);color:#ff8844;"
            "border:1px solid rgba(255,100,0,0.3);"
            "padding:5px 12px;border-radius:12px;font-size:11px;cursor:pointer;'>"
            "📅 훈련 계획 삭제</button>"
        )

    # G-4: 가져오기 패널
    import_sources = [g for g in all_goals if g.get("id") != gid and g.get("name")]
    import_panel = _render_import_panel(gid, import_sources) if import_sources else ""
    import_btn = ""
    if import_sources:
        import_btn = (
            f"<button onclick=\"var p=document.getElementById('import-panel-{gid}');"
            f"p.style.display=p.style.display==='none'?'block':'none'\" "
            "style='background:rgba(255,165,0,0.15);color:#ffaa00;"
            "border:1px solid rgba(255,165,0,0.3);"
            "padding:5px 12px;border-radius:12px;font-size:11px;cursor:pointer;'>"
            "📥 훈련 가져오기</button>"
        )

    return (
        "<div style='background:rgba(255,255,255,0.02);border-radius:8px;"
        "padding:10px;border:1px solid rgba(255,255,255,0.06);'>"
        + table_html
        + "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'>"
        + delete_btn + delete_plan_btn + import_btn
        + "</div>"
        + import_panel
        + "</div>"
    )


def _render_import_panel(gid: int | None, sources: list[dict]) -> str:
    """G-4 가져오기 서브패널 HTML."""
    src_opts = "".join(
        f"<option value='{g['id']}'>"
        f"{_html.escape(g.get('name',''))} ({g.get('distance_km',0):.0f}km, "
        f"{g.get('status','?')})</option>"
        for g in sources
    )
    today = date.today().isoformat()
    return (
        f"<div id='import-panel-{gid}' style='display:none;margin-top:8px;"
        "padding:12px;background:rgba(255,255,255,0.03);border-radius:8px;"
        "border:1px solid rgba(255,255,255,0.08);'>"
        "<div style='font-size:12px;font-weight:600;margin-bottom:10px;color:#ffaa00;'>"
        "📥 훈련 가져오기</div>"
        # 소스 목표
        "<div style='margin-bottom:8px;'>"
        "<label style='font-size:11px;color:var(--muted);display:block;margin-bottom:3px;'>"
        "소스 목표</label>"
        f"<select id='import-src-{gid}' style='width:100%;font-size:12px;'>"
        f"{src_opts}</select></div>"
        # 새 시작일
        "<div style='margin-bottom:8px;'>"
        "<label style='font-size:11px;color:var(--muted);display:block;margin-bottom:3px;'>"
        "새 시작일 <span style='font-size:10px;'>(첫 워크아웃이 놓일 날짜)</span></label>"
        f"<input type='date' id='import-start-{gid}' value='{today}' "
        "style='font-size:12px;'/></div>"
        # 범위 선택
        "<div style='margin-bottom:8px;'>"
        "<label style='font-size:11px;color:var(--muted);display:block;margin-bottom:5px;'>"
        "범위</label>"
        "<div style='display:flex;gap:14px;flex-wrap:wrap;font-size:12px;'>"
        f"<label><input type='radio' name='import-range-{gid}' value='all' checked "
        f"onchange='rpImportRange({gid},\"all\")'> 전체</label>"
        f"<label><input type='radio' name='import-range-{gid}' value='date' "
        f"onchange='rpImportRange({gid},\"date\")'> 특정일</label>"
        f"<label><input type='radio' name='import-range-{gid}' value='period' "
        f"onchange='rpImportRange({gid},\"period\")'> 기간</label>"
        "</div></div>"
        # 특정일 입력 (date 선택 시)
        f"<div id='import-date-wrap-{gid}' style='display:none;margin-bottom:8px;'>"
        "<label style='font-size:11px;color:var(--muted);display:block;margin-bottom:3px;'>"
        "원본 날짜 (소스 기준)</label>"
        f"<input type='date' id='import-src-date-{gid}' style='font-size:12px;'/></div>"
        # 기간 입력 (period 선택 시)
        f"<div id='import-period-wrap-{gid}' style='display:none;margin-bottom:8px;'>"
        "<label style='font-size:11px;color:var(--muted);display:block;margin-bottom:3px;'>"
        "원본 기간 (소스 날짜 기준)</label>"
        "<div style='display:flex;gap:6px;align-items:center;'>"
        f"<input type='date' id='import-from-{gid}' style='font-size:12px;'/>"
        "<span style='color:var(--muted);font-size:11px;'>~</span>"
        f"<input type='date' id='import-to-{gid}' style='font-size:12px;'/>"
        "</div></div>"
        # 버튼
        "<div style='display:flex;gap:8px;flex-wrap:wrap;margin-bottom:8px;'>"
        f"<button onclick='rpImportPreview({gid})' "
        "style='background:rgba(0,212,255,0.15);color:#00d4ff;"
        "border:1px solid rgba(0,212,255,0.3);"
        "padding:5px 12px;border-radius:10px;font-size:11px;cursor:pointer;'>"
        "🔍 미리보기</button>"
        f"<button id='import-confirm-{gid}' onclick='rpImportConfirm({gid})' "
        "style='display:none;background:rgba(0,255,136,0.2);color:#00ff88;"
        "border:1px solid rgba(0,255,136,0.3);"
        "padding:5px 12px;border-radius:10px;font-size:11px;cursor:pointer;"
        "font-weight:600;'>✅ 가져오기 확인</button>"
        "</div>"
        f"<div id='import-preview-{gid}'></div>"
        "</div>"
    )


# ── JS ──────────────────────────────────────────────────────────────────

def _goals_js() -> str:
    """목표 관리 패널 전체 JS (페이지당 1번)."""
    return """<script>
if(!window._rpGoalsMgrInit){window._rpGoalsMgrInit=true;

function rpGoalToggle(gid){
  var el=document.getElementById('goal-detail-'+gid);
  var arr=document.getElementById('goal-arrow-'+gid);
  if(!el)return;
  if(el.style.display!=='none'){
    el.style.display='none';if(arr)arr.textContent='▼';return;
  }
  if(arr)arr.textContent='▲';
  if(el.innerHTML.trim()){el.style.display='block';return;}
  el.innerHTML='<div style="padding:8px;color:var(--muted);font-size:12px;">⏳ 로딩 중...</div>';
  el.style.display='block';
  fetch('/training/goal/'+gid+'/detail',{headers:{'Accept':'text/html'}})
    .then(function(r){return r.text();})
    .then(function(html){el.innerHTML=html;})
    .catch(function(){
      el.innerHTML='<div style="color:#ff6b6b;padding:8px;font-size:12px;">불러오기 실패</div>';
    });
}

function rpGoalDelete(gid){
  if(!confirm('이 목표를 취소하시겠습니까?\\n훈련 계획은 유지됩니다.'))return;
  fetch('/training/goal/'+gid+'/cancel',{
    method:'POST',
    headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
  }).then(function(r){return r.json();})
  .then(function(d){
    var det=document.getElementById('goal-detail-'+gid);
    if(det)det.innerHTML='<div style="padding:8px;color:#ffaa00;font-size:12px;">— 취소됨. 페이지를 새로고침하세요.</div>';
    var row=document.getElementById('goal-row-'+gid);
    if(row)row.style.opacity='0.5';
  })
  .catch(function(){alert('오류가 발생했습니다.');});
}

function rpDeletePlan(gid){
  if(!confirm('AI 자동 생성 훈련 계획을 모두 삭제합니다.\\n수동 입력 계획은 유지됩니다.\\n계속하시겠습니까?'))return;
  fetch('/training/goal/'+gid+'/delete-plan',{
    method:'POST',
    headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
  }).then(function(r){return r.json();})
  .then(function(d){
    if(d.ok){
      alert('훈련 계획이 삭제되었습니다. ('+d.count+'개)');
      location.reload();
    }else{
      alert('오류: '+(d.error||'알 수 없음'));
    }
  })
  .catch(function(){alert('요청 오류가 발생했습니다.');});
}

function rpGoalDeleteEntry(gid){
  if(!confirm('이 목표 기록을 완전히 삭제하시겠습니까?\\n이 작업은 되돌릴 수 없습니다.'))return;
  fetch('/training/goal/'+gid+'/delete',{
    method:'POST',
    headers:{'Accept':'application/json','Content-Type':'application/x-www-form-urlencoded'}
  }).then(function(r){return r.json();})
  .then(function(d){
    if(d.ok){
      var row=document.getElementById('goal-row-'+gid);
      if(row)row.remove();
    }else{
      alert('오류: '+(d.error||'알 수 없음'));
    }
  })
  .catch(function(){alert('요청 오류가 발생했습니다.');});
}

function rpImportRange(gid,type){
  var dw=document.getElementById('import-date-wrap-'+gid);
  var pw=document.getElementById('import-period-wrap-'+gid);
  if(dw)dw.style.display=(type==='date')?'block':'none';
  if(pw)pw.style.display=(type==='period')?'block':'none';
}

function rpImportPreview(gid){
  var src=document.getElementById('import-src-'+gid);
  var start=document.getElementById('import-start-'+gid);
  var range=document.querySelector('input[name="import-range-'+gid+'"]:checked');
  var srcDate=document.getElementById('import-src-date-'+gid);
  var from=document.getElementById('import-from-'+gid);
  var to=document.getElementById('import-to-'+gid);
  if(!start||!start.value){alert('새 시작일을 선택하세요.');return;}
  var params='?start='+start.value;
  if(src&&src.value)params+='&src='+src.value;
  var rv=range?range.value:'all';
  params+='&range='+rv;
  if(rv==='date'&&srcDate&&srcDate.value)params+='&src_date='+srcDate.value;
  if(rv==='period'){
    if(from&&from.value)params+='&src_from='+from.value;
    if(to&&to.value)params+='&src_to='+to.value;
  }
  var pv=document.getElementById('import-preview-'+gid);
  var cb=document.getElementById('import-confirm-'+gid);
  if(pv)pv.innerHTML='<div style="color:var(--muted);font-size:12px;">⏳ 미리보기 로딩...</div>';
  if(cb)cb.style.display='none';
  fetch('/training/goal/'+gid+'/import-preview'+params)
    .then(function(r){return r.text();})
    .then(function(html){
      if(pv)pv.innerHTML=html;
      if(cb)cb.style.display='inline-block';
    })
    .catch(function(){if(pv)pv.innerHTML='<div style="color:#ff6b6b;font-size:12px;">오류 발생</div>';});
}

function rpImportConfirm(gid){
  var src=document.getElementById('import-src-'+gid);
  var start=document.getElementById('import-start-'+gid);
  var range=document.querySelector('input[name="import-range-'+gid+'"]:checked');
  var srcDate=document.getElementById('import-src-date-'+gid);
  var from=document.getElementById('import-from-'+gid);
  var to=document.getElementById('import-to-'+gid);
  if(!start||!start.value){alert('새 시작일을 선택하세요.');return;}
  var body={start:start.value};
  if(src)body.src=src.value;
  var rv=range?range.value:'all';
  body.range=rv;
  if(rv==='date'&&srcDate)body.src_date=srcDate.value;
  if(rv==='period'){
    if(from)body.src_from=from.value;
    if(to)body.src_to=to.value;
  }
  var cb=document.getElementById('import-confirm-'+gid);
  if(cb){cb.disabled=true;cb.textContent='⏳ 처리 중...';}
  fetch('/training/goal/'+gid+'/import',{
    method:'POST',
    headers:{'Content-Type':'application/json','Accept':'application/json'},
    body:JSON.stringify(body)
  }).then(function(r){return r.json();})
  .then(function(d){
    if(d.ok){
      alert('✅ '+d.count+'개 워크아웃을 가져왔습니다. 페이지를 새로고침합니다.');
      location.reload();
    }else{
      alert('오류: '+(d.error||'알 수 없음'));
      if(cb){cb.disabled=false;cb.textContent='✅ 가져오기 확인';}
    }
  })
  .catch(function(){
    alert('요청 오류');
    if(cb){cb.disabled=false;cb.textContent='✅ 가져오기 확인';}
  });
}

}
</script>"""
