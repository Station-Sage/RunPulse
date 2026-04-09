"""활동 데이터 CSV 내보내기 라우트."""

from __future__ import annotations

import csv
import io
import sqlite3

from flask import Blueprint, Response, request

from src.services.activity_service import get_activity_list
from src.web.helpers import db_path

export_bp = Blueprint("export", __name__)

_CSV_COLUMNS = [
    ("id", "ID"),
    ("source", "소스"),
    ("activity_type", "활동 유형"),
    ("start_time", "시작 시간"),
    ("distance_km", "거리(km)"),
    ("duration_sec", "시간(초)"),
    ("avg_pace_sec_km", "평균 페이스(초/km)"),
    ("avg_hr", "평균 심박수"),
    ("max_hr", "최대 심박수"),
    ("avg_cadence", "평균 케이던스"),
    ("elevation_gain", "고도 상승(m)"),
    ("avg_speed_ms", "평균 속도(m/s)"),
    ("name", "이름"),
    ("description", "설명"),
]


@export_bp.route("/activities/export.csv")
def activities_export_csv():
    """활동 목록을 CSV로 내보내기.

    Query params:
        date_from: YYYY-MM-DD (optional)
        date_to:   YYYY-MM-DD (optional)
        activity_type: 필터 (optional)
        max_rows:  최대 행 수, 기본 10000
    """
    dbp = db_path()
    if not dbp or not dbp.exists():
        return Response("데이터베이스를 찾을 수 없습니다.", status=404)

    filters: dict = {}
    if request.args.get("date_from"):
        filters["date_from"] = request.args["date_from"]
    if request.args.get("date_to"):
        filters["date_to"] = request.args["date_to"]
    if request.args.get("activity_type"):
        filters["activity_type"] = request.args["activity_type"]

    max_rows = min(request.args.get("max_rows", 10_000, type=int), 50_000)

    try:
        conn = sqlite3.connect(str(dbp))
        try:
            result = get_activity_list(
                conn,
                filters=filters,
                sort_by="start_time",
                sort_dir="DESC",
                page=1,
                per_page=max_rows,
            )
        finally:
            conn.close()
    except Exception as e:
        return Response(f"데이터 조회 실패: {e}", status=500)

    activities = result["activities"]

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([label for _, label in _CSV_COLUMNS])

    for act in activities:
        distance_m = act.get("distance_m") or 0
        distance_km = round(distance_m / 1000, 3)

        row = []
        for key, _ in _CSV_COLUMNS:
            if key == "distance_km":
                row.append(distance_km)
            else:
                row.append(act.get(key, ""))
        writer.writerow(row)

    csv_content = buf.getvalue()
    return Response(
        csv_content,
        mimetype="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=activities.csv",
        },
    )
