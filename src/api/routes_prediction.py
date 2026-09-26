"""GET /api/v1/prediction/compare, GET /api/v1/prediction/profile, GET /api/v1/races/candidates, PUT·DELETE /api/v1/races/<activity_id>/confirm — P7-PRED-53·71."""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta

from flask import request

from src.services import prediction_compare_service, race_result_service
from src.web.helpers import db_path

from . import api_bp, api_error, api_ok

_BUCKETS = ("5k", "10k", "half", "marathon")


def _conn():
    p = db_path()
    return sqlite3.connect(str(p)) if p.exists() else None


@api_bp.get("/prediction/compare")
def get_prediction_compare():
    bucket = request.args.get("bucket", "10k")
    if bucket not in _BUCKETS:
        return api_error("BAD_REQUEST", f"bucket must be one of {_BUCKETS}")
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(prediction_compare_service.compare(conn, bucket, request.args.get("date")))
    finally:
        conn.close()


@api_bp.get("/prediction/profile")
def get_prediction_profile():
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok(prediction_compare_service.profile(conn, request.args.get("date")))
    finally:
        conn.close()


@api_bp.get("/races/candidates")
def get_race_candidates():
    since = request.args.get("since") or (date.today() - timedelta(days=365)).isoformat()
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"items": race_result_service.candidates(conn, since)})
    finally:
        conn.close()


@api_bp.put("/races/<int:activity_id>/confirm")
def put_race_confirm(activity_id: int):
    body = request.get_json(silent=True) or {}
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        res = race_result_service.confirm(conn, activity_id, body.get("effort", ""), body.get("official_time_sec"),
                                          body.get("race_name"), body.get("distance_m"), body.get("note"))
        return api_ok(res)
    except ValueError as e:
        return api_error("BAD_REQUEST", str(e))
    except LookupError:
        return api_error("NOT_FOUND", "activity not found", 404)
    finally:
        conn.close()


@api_bp.delete("/races/<int:activity_id>/confirm")
def delete_race_confirm(activity_id: int):
    conn = _conn()
    if conn is None:
        return api_error("NOT_FOUND", "running.db 없음", 503)
    try:
        return api_ok({"deleted": race_result_service.remove(conn, activity_id)})
    finally:
        conn.close()
