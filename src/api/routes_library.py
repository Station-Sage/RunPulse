"""GET /api/v1/library/activities(+:id, +:id/streams, +:id/providers) + /archive + /metrics/:slug + /wellness — Phase 7a/7b."""
from __future__ import annotations

import sqlite3

from flask import request

from src.services import activity_service, archive_service, metrics_browser_service, metrics_service, provider_comparison_service, provider_matrix_service, provider_status_service, wellness_service
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok


@api_bp.get("/library/activities")
def get_library_activities():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    filters: dict = {}
    if request.args.get("sport"):
        filters["activity_type"] = request.args["sport"]
    if request.args.get("from"):
        filters["date_from"] = request.args["from"]
    if request.args.get("to"):
        filters["date_to"] = request.args["to"]
    if request.args.get("search"):
        filters["search"] = request.args["search"]
    if request.args.get("dist_min"):
        try:
            filters["min_distance_m"] = float(request.args["dist_min"]) * 1000
        except ValueError:
            return api_error("INVALID_PARAM", "dist_min은 숫자여야 합니다.", 400)

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
        detail = activity_service.get_activity_detail(conn, activity_id)
    finally:
        conn.close()

    if not detail["core"]:
        return api_error("NOT_FOUND", f"활동을 찾을 수 없습니다: {activity_id}", 404)

    return api_ok({"activity": detail})


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
        result = metrics_service.get_metric_breakdown(conn, scope_type, scope_id, slug)
    finally:
        conn.close()

    if result is None:
        return api_error("NOT_FOUND", f"메트릭을 찾을 수 없습니다: {slug}", 404)

    return api_ok({"metric": result})


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

    return api_ok(result)


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

    return api_ok({"streams": streams})


@api_bp.get("/library/wellness")
def get_library_wellness():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    date_param = request.args.get("date") or None
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
        result = provider_status_service.get_provider_coverage(conn)
    finally:
        conn.close()

    return api_ok(result)


@api_bp.get("/library/providers/matrix")
def get_library_providers_matrix():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        days = int(request.args.get("days", 28))
    except ValueError:
        return api_error("INVALID_PARAM", "days는 정수여야 합니다.", 400)

    try:
        threshold = float(request.args.get("discrepancy_threshold", 5.0))
    except ValueError:
        return api_error("INVALID_PARAM", "discrepancy_threshold는 숫자여야 합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        result = provider_matrix_service.get_provider_comparison_period(
            conn, days=days, discrepancy_threshold=threshold,
        )
    finally:
        conn.close()

    return api_ok({"comparison": result})


@api_bp.get("/library/wellness/trend")
def get_library_wellness_trend():
    dpath = db_path()
    if not dpath.exists():
        return api_error("NOT_FOUND", "running.db 없음", 503)

    try:
        days = int(request.args.get("days", 30))
    except ValueError:
        return api_error("INVALID_PARAM", "days는 정수여야 합니다.", 400)

    conn = sqlite3.connect(str(dpath))
    try:
        result = wellness_service.get_wellness_trend(conn, days=days)
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
