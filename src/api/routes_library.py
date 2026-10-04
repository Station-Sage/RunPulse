"""GET /api/v1/library/activities(+:id, +:id/streams, +:id/providers) + /archive + /metrics/:slug + /wellness — Phase 7a/7b."""
from __future__ import annotations

import sqlite3
from datetime import date

from flask import request

from src.services import activity_list_filters, activity_service, archive_service, metrics_browser_service, metrics_explain, metrics_service, provider_comparison_service, provider_matrix_service, provider_pairs_service, provider_status_service, wellness_service
from src.utils.provider_matrix_rows import compare_group_for_slug
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok, api_ok_cacheable


@api_bp.get("/library/activities")
def get_library_activities():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        filters = activity_list_filters.parse_args(request.args)
    except ValueError as e:
        return api_error("INVALID_PARAM", f"잘못된 파라미터: {e}", 400)
    if request.args.get("sort"):
        filters["sort"] = request.args["sort"]

    try:
        page = int(request.args.get("page", 1))
        per_page = int(request.args.get("per_page", 20))
    except ValueError:
        return api_error("INVALID_PARAM", "page/per_page는 정수여야 합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        result = activity_service.get_activity_list(
            conn, filters=filters, page=page, per_page=per_page,
        )
    finally:
        conn.close()

    return api_ok(
        {
            "activities": result["activities"],
            "total": result["total"],
            "has_more": result["page"] < result["total_pages"],
        },
        meta={"page": result["page"], "per_page": result["per_page"]},
    )


@api_bp.get("/library/activities/<int:activity_id>")
def get_library_activity_detail(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        include = {x.strip() for x in request.args.get("include", "").split(",")}
        detail = activity_service.get_activity_detail(conn, activity_id, include_streams="streams" in include)
    finally:
        conn.close()

    if not detail["core"]:
        return api_error("NOT_FOUND", f"활동을 찾을 수 없습니다: {activity_id}", 404)

    # 동기화 후엔 거의 안 바뀌는 무거운 페이로드(요약 탭 다운샘플 스트림 포함) — ETag로 조건부 GET.
    return api_ok_cacheable({"activity": detail})


@api_bp.get("/library/metrics/<slug>")
def get_library_metric_breakdown(slug: str):
    scope_id = request.args.get("scope_id")
    if not scope_id:
        return api_error("INVALID_PARAM", "scope_id 파라미터가 필요합니다.", 400)

    scope_type = request.args.get("scope_type", "daily")

    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        result = None
        # explain=1: 분해 v2(§C3.2) — TSB/CTL/ATL/UTRS/CIRS만 지원(2-5, 2026-09-28).
        # 그 외 슬러그·explainer 실패 시 기존 v1(children/inputs)로 폴백.
        if request.args.get("explain") == "1":
            result = metrics_explain.get_metric_explain(conn, scope_type, scope_id, slug)
        if result is None:
            result = metrics_service.get_metric_breakdown(conn, scope_type, scope_id, slug)
    finally:
        conn.close()

    if result is None:
        return api_error("NOT_FOUND", f"메트릭을 찾을 수 없습니다: {slug}", 404)

    return api_ok({"metric": result, "compare_group": compare_group_for_slug(slug)})


@api_bp.get("/library/activities/<int:activity_id>/providers")
def get_library_activity_providers(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        threshold = float(request.args.get("discrepancy_threshold", 5.0))
    except ValueError:
        return api_error("INVALID_PARAM", "discrepancy_threshold는 숫자여야 합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        result = provider_comparison_service.get_provider_comparison(
            conn, activity_id, discrepancy_threshold=threshold,
        )
    finally:
        conn.close()

    if result is None:
        return api_error("NOT_FOUND", f"활동을 찾을 수 없습니다: {activity_id}", 404)

    return api_ok({"comparison": result})


@api_bp.get("/library/metrics")
def get_library_metrics_browser():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    date_param = request.args.get("date") or None
    conn = sqlite3.connect(str(dpath))
    try:
        result = metrics_browser_service.get_metrics_browser(conn, date=date_param)
    finally:
        conn.close()

    return api_ok(result)


@api_bp.get("/library/metrics/<slug>/trend")
def get_library_metric_trend(slug: str):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    period = request.args.get("period", "3m")
    conn = sqlite3.connect(str(dpath))
    try:
        result = metrics_browser_service.get_metric_trend(conn, slug, period=period)
    finally:
        conn.close()

    if result is None:
        return api_error("NOT_FOUND", f"메트릭 데이터를 찾을 수 없습니다: {slug}", 404)

    return api_ok({**result, "compare_group": compare_group_for_slug(slug)})


@api_bp.get("/library/activities/<int:activity_id>/streams")
def get_library_activity_streams(activity_id: int):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        streams = activity_service.get_activity_streams(
            conn, activity_id, source=request.args.get("source"),
        )
    finally:
        conn.close()

    # 전체 해상도 스트림(가장 무거운 페이로드) — ETag로 조건부 GET.
    return api_ok_cacheable({"streams": streams})


@api_bp.get("/library/wellness")
def get_library_wellness():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    date_param = request.args.get("date") or None
    if date_param is not None:
        try:
            date.fromisoformat(date_param)
        except ValueError:
            return api_error("INVALID_PARAM", "date는 YYYY-MM-DD 형식이어야 합니다.", 400)
        if date_param > date.today().isoformat():
            date_param = None  # 미래 날짜는 오늘로
    conn = sqlite3.connect(str(dpath))
    try:
        result = wellness_service.get_wellness_detail(conn, date=date_param)
    finally:
        conn.close()

    return api_ok(result)


@api_bp.get("/library/providers/status")
def get_library_providers_status():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        result = provider_status_service.get_provider_status(conn)
    finally:
        conn.close()

    return api_ok({"providers": result})


@api_bp.get("/library/providers/coverage")
def get_library_providers_coverage():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        from src.utils.config import load_config
        result = provider_status_service.get_provider_coverage(conn, config=load_config())
    finally:
        conn.close()

    return api_ok(result)


def _matrix_params():
    try:
        days = int(request.args.get("days", 28))
    except ValueError:
        days = -1
    return days if days in provider_matrix_service.VALID_DAYS else None


@api_bp.get("/library/providers/matrix")
def get_library_providers_matrix():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    days = _matrix_params()
    if days is None:
        return api_error("INVALID_PARAM", "days는 28/56/84 중 하나여야 합니다.", 400)
    conn = sqlite3.connect(str(dpath))
    try:
        result = provider_matrix_service.get_matrix(conn, days, date.today().isoformat())
    finally:
        conn.close()
    return api_ok(result)


@api_bp.get("/library/providers/pairs/<group>")
def get_library_providers_pairs(group: str):
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)
    days = _matrix_params()
    if days is None:
        return api_error("INVALID_PARAM", "days는 28/56/84 중 하나여야 합니다.", 400)
    conn = sqlite3.connect(str(dpath))
    try:
        result = provider_pairs_service.get_pairs(conn, group, days, date.today().isoformat())
    finally:
        conn.close()
    if result is None:
        return api_error("NOT_FOUND", f"알 수 없는 비교 그룹: {group}", 404)
    return api_ok(result)


@api_bp.get("/library/wellness/trend")
def get_library_wellness_trend():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        return api_error("INVALID_PARAM", "days는 정수여야 합니다.", 400)

    end = request.args.get("end") or None
    if end is not None:
        try:
            date.fromisoformat(end)
        except ValueError:
            return api_error("INVALID_PARAM", "end는 YYYY-MM-DD 형식이어야 합니다.", 400)
    conn = sqlite3.connect(str(dpath))
    try:
        result = wellness_service.get_wellness_trend(conn, days=days, end=end)
    finally:
        conn.close()

    return api_ok(result)


@api_bp.get("/library/archive")
def get_library_archive():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    conn = sqlite3.connect(str(dpath))
    try:
        result = archive_service.get_archive(conn)
    finally:
        conn.close()

    return api_ok(result)
