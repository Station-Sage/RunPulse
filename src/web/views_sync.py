"""동기화 탭 뷰 — 데이터 동기화 + 서비스 연결 + 임포트/익스포트.

/sync : 동기화 메인 (기본/기간 동기화 + 서비스 상태 + 임포트)
"""
from __future__ import annotations

import html as _html
import logging

from flask import Blueprint, request

from src.utils.config import load_config
from src.sync.garmin import check_garmin_connection, _tokenstore_path
from src.sync.strava import check_strava_connection
from src.sync.intervals import check_intervals_connection
from src.sync.runalyze import check_runalyze_connection
from .helpers import db_path, html_page, last_sync_info
from .sync_ui import sync_card_html
from .views_settings_hub import render_sync_overview
from .views_settings import _service_card, _garmin_token_status_html

log = logging.getLogger(__name__)
sync_bp = Blueprint("sync_tab", __name__)


@sync_bp.route("/sync")
def sync_page():
    """동기화 탭 메인 페이지."""
    config = load_config()

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
    connected = {k for k, v in statuses.items() if v}
    sync_card = sync_card_html(last_sync=sync, connected=connected)

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
        "<label>최근 <input type='number' id='recompute-days' value='90' min='1' max='365'"
        " style='width:4rem;text-align:center;'> 일</label>"
        "<button type='button' onclick='recomputeMetrics()' "
        "style='background:var(--cyan);color:#000;border:none;padding:0.4rem 1.2rem;"
        "border-radius:4px;cursor:pointer;font-weight:bold;'>재계산 시작</button>"
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

    body = (
        msg_html
        + sync_overview
        + sync_card
        + service_cards
        + import_section
        + recompute_section
    )
    return html_page("동기화", body, active_tab="sync")
