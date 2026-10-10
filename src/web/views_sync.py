"""동기화 탭 뷰 — 데이터 동기화 + 서비스 연결 + 임포트/익스포트.

/sync : 동기화 메인 (기본/기간 동기화 + 서비스 상태 + 임포트)
"""
from __future__ import annotations

import html as _html
import logging

from flask import Blueprint, redirect, request

from src.utils.config import load_config, save_config
from src.sync.garmin import check_garmin_connection, _tokenstore_path
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from .helpers import db_path, html_page, last_sync_info
from .sync_ui import sync_card_html
from .views_settings_hub import render_sync_overview
from .views_settings_render import _service_card
from .views_settings_garmin import _garmin_token_status_html

log = logging.getLogger(__name__)
sync_bp = Blueprint("sync_tab", __name__)


@sync_bp.route("/sync")
def sync_page():
    """동기화 탭 메인 페이지."""
    from .helpers import get_current_user_id
    config = load_config(user_id=get_current_user_id())

    garmin_status = check_garmin_connection(config)
    strava_status = check_strava_connection(config)
    intervals_status = check_intervals_connection(config)
    runalyze_status = check_runalyze_connection(config)

    tokenstore = _tokenstore_path(config)
    garmin_extra = (
        f"<p class='muted' style='font-size:0.82rem;margin-top:0.3rem;'>"
        f"토큰: <code>{_html.escape(str(tokenstore))}</code></p>"
    )

    sync = last_sync_info(["garmin", "strava", "intervals", "runalyze"])
    statuses = {
        "garmin": garmin_status, "strava": strava_status,
        "intervals": intervals_status, "runalyze": runalyze_status,
    }

    msg = _html.escape(request.args.get("msg", ""))
    msg_html = (
        f"<div class='card' style='border-color:#4caf50;'><p>{msg}</p></div>"
        if msg else ""
    )

    # 동기화 상태 요약
    sync_overview = render_sync_overview(statuses, sync)

    # 동기화 실행 카드 (기본/기간 2탭)
    connected = {k for k, v in statuses.items() if v.get("ok")}
    from src.utils.config import ALL_SOURCES, enabled_sources
    on = set(enabled_sources(config))
    sync_card = sync_card_html(last_sync=sync, connected=connected, sync_off=set(ALL_SOURCES) - on)
    sources_section = _sync_sources_html(on, connected)

    # 서비스 연결 카드
    service_cards = (
        "<h2 style='margin:1rem 0 0.8rem;font-size:1rem;color:var(--muted);'>"
        "데이터 소스 연동</h2>"
        "<div class='cards-row'>"
        + _service_card("Garmin Connect", "⌚", garmin_status,
                        "/connect/garmin", "/connect/garmin/disconnect", garmin_extra,
                        last_sync=sync.get("garmin"))
        + _service_card("Strava", "🏃", strava_status,
                        "/connect/strava", "/connect/strava/disconnect",
                        last_sync=sync.get("strava"))
        + "</div><div class='cards-row'>"
        + _service_card("Intervals.icu", "📊", intervals_status,
                        "/connect/intervals", "/connect/intervals/disconnect",
                        last_sync=sync.get("intervals"))
        + _service_card("Runalyze", "📈", runalyze_status,
                        "/connect/runalyze", "/connect/runalyze/disconnect",
                        last_sync=sync.get("runalyze"))
        + "</div>"
    )

    # 임포트 섹션
    import_section = (
        "<div class='card'>"
        "<h2>Strava 아카이브 임포트</h2>"
        "<p>Strava에서 내보낸 zip 파일을 임포트하거나, 기존 활동에 FIT/GPX 파일을 재연결합니다.<br>"
        "<small class='muted'>Settings → 데이터 내보내기에서 다운로드한 zip 파일을 사용합니다.</small></p>"
        "<a href='/import/strava-archive'>"
        "<button style='padding:0.4rem 1.2rem;background:var(--cyan);color:#000;"
        "border:none;border-radius:4px;cursor:pointer;font-weight:bold;'>"
        "아카이브 임포트</button></a></div>"
    )

    # 메트릭 재계산 섹션
    recompute_section = (
        "<div class='card' id='metrics-section'>"
        "<h2>메트릭 재계산</h2>"
        "<p>기존 DB 데이터를 기반으로 2차 메트릭을 재계산합니다.<br>"
        "<small class='muted'>동기화 후 자동 실행되지만, 수동으로 강제 재계산할 때 사용합니다.</small></p>"
        "<form id='recompute-form' style='display:flex;align-items:center;gap:1rem;flex-wrap:wrap;'>"
        "<label>최근 <input type='number' id='recompute-days' value='90' min='1'"
        " style='width:4rem;text-align:center;'> 일</label>"
        "<button type='button' onclick='recomputeMetrics()' "
        "style='background:var(--cyan);color:#000;border:none;padding:0.4rem 1.2rem;"
        "border-radius:4px;cursor:pointer;font-weight:bold;'>재계산 시작</button>"
        "<button type='button' onclick='document.getElementById(\"recompute-days\").value=0;recomputeMetrics()' "
        "style='background:rgba(255,255,255,0.08);color:var(--muted);border:1px solid var(--card-border);"
        "padding:0.4rem 1rem;border-radius:4px;cursor:pointer;'>전체 기간</button>"
        "<span id='recompute-status' class='muted'></span></form>"
        "<script>"
        "function recomputeMetrics(){"
        "  var days=document.getElementById('recompute-days').value;"
        "  var st=document.getElementById('recompute-status');"
        "  st.textContent='재계산 중...';"
        "  fetch('/recompute-metrics?days='+days)"
        "  .then(r=>r.json()).then(d=>{st.textContent=d.message||'완료';})"
        "  .catch(()=>{st.textContent='실패';});"
        "}"
        "</script></div>"
    )

    auto_sync_section = _auto_sync_settings_html(config)

    body = (
        msg_html
        + sync_overview
        + sync_card
        + sources_section
        + auto_sync_section
        + service_cards
        + import_section
        + recompute_section
    )
    return html_page("동기화", body, active_tab="sync")


def _sync_sources_html(on: set[str], connected: set[str]) -> str:
    """동기화 대상 카드 — 체크 해제하면 자동·기본 동기화에서 빠지고, 다시 체크하면 포함(즉시 저장)."""
    from src.utils.config import ALL_SOURCES
    names = {"garmin": "Garmin", "strava": "Strava", "intervals": "Intervals", "runalyze": "Runalyze"}
    unlinked = " <small class='muted'>(미연결)</small>"
    boxes = "".join(
        f"<label style='display:inline-flex;align-items:center;gap:6px;margin-right:1.2rem;font-size:0.9rem;'>"
        f"<input type='checkbox' name='src_{k}' value='1' {'checked' if k in on else ''}"
        f" onchange='this.form.submit()'> {names[k]}{'' if k in connected else unlinked}</label>"
        for k in ALL_SOURCES
    )
    return (
        "<div class='card'><h2 style='margin-bottom:0.4rem;'>동기화 대상</h2>"
        "<p class='muted' style='font-size:0.82rem;margin:0 0 0.6rem;'>"
        "체크 해제한 소스는 자동·기본 동기화에서 제외됩니다(기존 데이터는 유지). 다시 체크하면 곧바로 포함됩니다. "
        "기간 동기화는 직접 고른 소스로 실행할 수 있습니다.</p>"
        f"<form method='post' action='/sync/sources'>{boxes}</form></div>"
    )


@sync_bp.post("/sync/sources")
def sync_sources_post():
    """동기화 대상 소스 저장(config.sync_sources). 체크된 것만 포함."""
    from .helpers import get_current_user_id
    from src.utils.config import ALL_SOURCES

    config = load_config(user_id=get_current_user_id())
    config["sync_sources"] = [k for k in ALL_SOURCES if request.form.get(f"src_{k}") == "1"]
    save_config(config)
    return redirect("/sync?msg=동기화 대상이 저장되었습니다")


def _auto_sync_settings_html(config: dict) -> str:
    """자동 주기 동기화 설정 카드."""
    from .auto_sync import status as auto_sync_status
    from src.utils.sync_ledger_query import last_auto_run

    cfg = config.get("auto_sync", {})
    enabled = cfg.get("enabled", True)
    interval_hours = int(cfg.get("interval_hours", 4))
    days = int(cfg.get("days", 2))

    st = auto_sync_status()
    thread_badge = (
        "<span style='background:#00ff88;color:#000;padding:2px 8px;border-radius:10px;"
        "font-size:0.75rem;font-weight:600;'>실행 중</span>"
        if st["running"] else
        "<span style='background:rgba(255,255,255,0.12);color:var(--muted);padding:2px 8px;"
        "border-radius:10px;font-size:0.75rem;'>대기</span>"
    )
    last_run_text = f"마지막 실행: {_html.escape(st['last_run'])}" if st["last_run"] else "아직 실행되지 않음"

    checked = "checked" if enabled else ""
    interval_opts = "".join(
        f"<option value='{h}' {'selected' if h == interval_hours else ''}>{h}시간마다</option>"
        for h in [1, 2, 4, 6, 12, 24]
    )

    return (
        "<div class='card'>"
        "<div style='display:flex;align-items:center;justify-content:space-between;margin-bottom:0.8rem;'>"
        "<div>"
        "<h2 style='margin:0;font-size:0.95rem;'>자동 동기화</h2>"
        f"<p class='muted' style='margin:0.2rem 0 0;font-size:0.8rem;'>{thread_badge} {last_run_text}</p>"
        "</div></div>"
        "<form method='POST' action='/sync/auto-sync-settings' "
        "style='display:flex;align-items:center;gap:1.2rem;flex-wrap:wrap;'>"
        "<label style='display:flex;align-items:center;gap:0.5rem;cursor:pointer;'>"
        f"<input type='checkbox' name='enabled' value='1' {checked} "
        "style='width:16px;height:16px;accent-color:var(--cyan);'>"
        "<span style='font-size:0.9rem;'>활성화</span>"
        "</label>"
        "<label style='display:flex;align-items:center;gap:0.5rem;font-size:0.9rem;'>"
        "주기:"
        f"<select name='interval_hours' style='background:var(--card-bg);color:var(--text);"
        "border:1px solid var(--card-border);border-radius:6px;padding:4px 8px;font-size:0.88rem;'>"
        f"{interval_opts}"
        "</select>"
        "</label>"
        "<label style='display:flex;align-items:center;gap:0.5rem;font-size:0.9rem;'>"
        "범위:"
        f"<input type='number' name='days' value='{days}' min='1' max='30' "
        "style='width:4rem;background:var(--card-bg);color:var(--text);"
        "border:1px solid var(--card-border);border-radius:6px;padding:4px 8px;"
        "text-align:center;font-size:0.88rem;'>"
        "<span class='muted' style='font-size:0.82rem;'>일 전까지</span>"
        "</label>"
        "<button type='submit' style='background:var(--cyan);color:#000;border:none;"
        "padding:0.4rem 1.2rem;border-radius:6px;cursor:pointer;font-weight:600;"
        "font-size:0.88rem;'>저장</button>"
        "</form>"
        "</div>"
    )


@sync_bp.post("/sync/auto-sync-settings")
def auto_sync_settings_post():
    """자동 동기화 설정 저장 + thread 재시작."""
    from .helpers import get_current_user_id
    from .auto_sync import restart as auto_sync_restart

    user_id = get_current_user_id()
    config = load_config(user_id=user_id)

    enabled = request.form.get("enabled") == "1"
    try:
        interval_hours = max(1, int(request.form.get("interval_hours", 4)))
        days = max(1, min(30, int(request.form.get("days", 2))))
    except (ValueError, TypeError):
        return redirect("/sync?msg=입력값이 올바르지 않습니다")

    config["auto_sync"] = {
        "enabled": enabled,
        "interval_hours": interval_hours,
        "days": days,
    }
    save_config(config)

    auto_sync_restart(config, user_id)
    log.info("[auto_sync_settings] 저장 완료: enabled=%s, interval=%dh, days=%d",
             enabled, interval_hours, days)

    status_str = "활성화" if enabled else "비활성화"
    return redirect(f"/sync?msg=자동 동기화 설정이 저장되었습니다 ({status_str}, {interval_hours}시간 주기)")
