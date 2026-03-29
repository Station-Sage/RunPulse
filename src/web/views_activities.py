"""활동 목록 뷰 — Flask Blueprint + 라우트 핸들러.

/activities
  - 날짜 범위·소스·유형 필터
  - 페이지네이션 (20개/페이지)
  - 통합 활동 행 (Garmin 우선 병합)
  - 서브트리 확장/축소 (▶/▼ 토글)
  - 동일 활동 묶기: 자동 묶기 / 직접 편집 모드

세부 구현:
  - views_activities_helpers.py : 포맷 헬퍼 + 아이콘/배지
  - views_activities_filter.py  : 필터 폼 + 날짜 프리셋 JS
  - views_activities_table.py   : 테이블 + 요약 + 편집 바 + 페이지네이션
"""
from __future__ import annotations

import html
import sqlite3
from datetime import date, timedelta

from flask import Blueprint, request

from src.services.unified_activities import fetch_unified_activities
from .helpers import db_path, html_page
from .views_activities_filter import _render_filter_form
from .views_activities_table import (
    _JS,
    _EDIT_BAR,
    _MERGE_BAR,
    _PAGE_SIZE,
    _render_activity_table,
    _render_pagination,
    _render_summary,
)

activities_bp = Blueprint("activities", __name__)


@activities_bp.get("/activities")
def activities_list():
    """활동 목록 페이지."""
    dpath = db_path()
    if not dpath.exists():
        body = "<div class='card'><p>running.db 가 없습니다. DB를 먼저 초기화하세요.</p></div>"
        return html_page("활동 목록", body, active_tab="activities")

    source = request.args.get("source", "").strip()
    act_type = request.args.get("type", "").strip()
    date_from = request.args.get("from", "").strip()
    date_to = request.args.get("to", "").strip()
    q = request.args.get("q", "").strip()
    sort_by = request.args.get("sort", "date").strip()
    sort_dir = request.args.get("dir", "desc").strip()
    if sort_by not in ("date", "distance", "duration", "pace", "hr"):
        sort_by = "date"
    if sort_dir not in ("asc", "desc"):
        sort_dir = "desc"
    try:
        page = max(1, int(request.args.get("page", "1")))
    except ValueError:
        page = 1

    def _parse_float(key: str) -> float | None:
        v = request.args.get(key, "").strip()
        try:
            return float(v) if v else None
        except ValueError:
            return None

    min_dist = _parse_float("min_dist")
    max_dist = _parse_float("max_dist")
    min_pace_raw = request.args.get("min_pace", "").strip()
    max_pace_raw = request.args.get("max_pace", "").strip()
    min_dur_raw = request.args.get("min_dur", "").strip()
    max_dur_raw = request.args.get("max_dur", "").strip()

    def _pace_to_sec(v: str) -> int | None:
        """'M:SS' → 초/km."""
        if not v:
            return None
        parts = v.split(":")
        try:
            return int(parts[0]) * 60 + int(parts[1]) if len(parts) == 2 else None
        except (ValueError, IndexError):
            return None

    min_pace = _pace_to_sec(min_pace_raw)
    max_pace = _pace_to_sec(max_pace_raw)
    min_dur = int(float(min_dur_raw) * 60) if min_dur_raw else None
    max_dur = int(float(max_dur_raw) * 60) if max_dur_raw else None

    _has_date_param = "from" in request.args or "to" in request.args
    if not _has_date_param:
        date_from = (date.today() - timedelta(days=90)).isoformat()

    try:
        with sqlite3.connect(str(dpath)) as conn:
            activities, total, stats = fetch_unified_activities(
                conn,
                source_filter=source,
                act_type_filter=act_type,
                date_from=date_from,
                date_to=date_to,
                page=page,
                page_size=_PAGE_SIZE,
                sort_by=sort_by,
                sort_dir=sort_dir,
                q=q,
                min_dist=min_dist,
                max_dist=max_dist,
                min_pace=min_pace,
                max_pace=max_pace,
                min_dur=min_dur,
                max_dur=max_dur,
            )
    except Exception as exc:
        body = f"<div class='card'><p>조회 오류: {html.escape(str(exc))}</p></div>"
        return html_page("활동 목록", body, active_tab="activities")

    qs_parts = []
    if source:
        qs_parts.append(f"source={html.escape(source)}")
    if act_type:
        qs_parts.append(f"type={html.escape(act_type)}")
    if _has_date_param or date_from:
        qs_parts.append(f"from={html.escape(date_from)}")
    if _has_date_param or date_to:
        qs_parts.append(f"to={html.escape(date_to)}")
    if q:
        qs_parts.append(f"q={html.escape(q)}")
    if min_dist is not None:
        qs_parts.append(f"min_dist={min_dist}")
    if max_dist is not None:
        qs_parts.append(f"max_dist={max_dist}")
    if min_pace_raw:
        qs_parts.append(f"min_pace={html.escape(min_pace_raw)}")
    if max_pace_raw:
        qs_parts.append(f"max_pace={html.escape(max_pace_raw)}")
    if min_dur_raw:
        qs_parts.append(f"min_dur={html.escape(min_dur_raw)}")
    if max_dur_raw:
        qs_parts.append(f"max_dur={html.escape(max_dur_raw)}")
    base_qs = "&".join(qs_parts)
    sort_base = "/activities?" + base_qs

    sync_section = (
        "<div style='margin-top:12px;text-align:center;'>"
        "<a href='/sync' style='color:var(--cyan);font-size:0.82rem;text-decoration:none;'>"
        "🔄 동기화 관리 →</a></div>"
    )

    _guide = (
        "<details style='margin-top:12px;'>"
        "<summary style='cursor:pointer;background:rgba(255,255,255,0.05);border-radius:12px;"
        "padding:10px 16px;font-size:13px;font-weight:600;list-style:none;color:var(--muted);'>"
        "📊 운동 분류 기준</summary>"
        "<div class='card' style='margin-top:8px;font-size:0.82rem;'>"
        "<table style='width:100%;'><thead><tr>"
        "<th>분류</th><th>기준</th><th>훈련 효과</th></tr></thead><tbody>"
        "<tr><td style='color:#27ae60;'>이지런</td><td>Z1-2 &gt; 70%</td><td>유산소 기반 강화</td></tr>"
        "<tr><td style='color:#e67e22;'>템포</td><td>Z3 &gt; 30%, HR 75~88%</td><td>젖산역치 개선</td></tr>"
        "<tr><td style='color:#8e44ad;'>역치</td><td>페이스 ≈ eFTP ±5%, Z3-4</td><td>역치 페이스 향상</td></tr>"
        "<tr><td style='color:#e74c3c;'>인터벌</td><td>Z4-5 &gt; 25%</td><td>VO2Max 자극</td></tr>"
        "<tr><td style='color:#2980b9;'>장거리</td><td>90분+ 또는 15km+, Z1-2 위주</td><td>지구력/지방 연소</td></tr>"
        "<tr><td style='color:#c0392b;'>레이스</td><td>HR &gt; 90% maxHR, 5km+, Z4-5 높음</td><td>최대 퍼포먼스</td></tr>"
        "<tr><td style='color:#7f8c8d;'>회복</td><td>5km 미만, 40분 미만, Z1-2 &gt; 85%</td><td>피로 해소</td></tr>"
        "</tbody></table>"
        "<p class='muted' style='margin:0.5rem 0 0;'>RunPulse가 HR존·페이스·거리·시간을 분석하여 자동 분류합니다. "
        "소스(Garmin/Strava/Intervals) 태그와 독립적입니다.</p></div></details>"
    )

    body = (
        _JS
        + _EDIT_BAR
        + _MERGE_BAR
        + _render_filter_form(source, act_type, date_from, date_to, q,
                             min_dist, max_dist, min_pace_raw, max_pace_raw, min_dur_raw, max_dur_raw)
        + _render_summary(total, stats.get("total_dist_km", 0.0))
        + _render_activity_table(activities, sort_url_base=sort_base, cur_sort=sort_by, cur_dir=sort_dir)
        + _render_pagination(page, total, base_qs)
        + _guide
        + sync_section
    )
    return html_page("활동 목록", body, active_tab="activities")
