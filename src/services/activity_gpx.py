"""단일 활동 GPX 1.1 생성 — activity_streams 의 위치 점이 가장 많은 그룹 구성원을 사용(ADR-022). DB 쓰기 없음."""
from __future__ import annotations

import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from src.utils.canonical import group_activity_ids

MIN_POINTS = 10
_NS = "http://www.topografix.com/GPX/1/1"
_TPX = "http://www.garmin.com/xmlschemas/TrackPointExtension/v1"


class NoGpsError(Exception):
    pass


def _parse_start(s: str | None) -> datetime:
    try:
        d = datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return datetime(1970, 1, 1, tzinfo=timezone.utc)
    return d.replace(tzinfo=timezone.utc) if d.tzinfo is None else d.astimezone(timezone.utc)


def _best_member(conn: sqlite3.Connection, ids: list[int]) -> tuple[int, int]:
    q = ",".join("?" * len(ids))
    row = conn.execute(
        f"SELECT activity_id, COUNT(*) n FROM activity_streams WHERE activity_id IN ({q}) "
        "AND latitude IS NOT NULL AND longitude IS NOT NULL GROUP BY activity_id ORDER BY n DESC LIMIT 1",
        ids).fetchone()
    return (row[0], row[1]) if row else (0, 0)


def build_gpx(conn: sqlite3.Connection, activity_id: int) -> tuple[bytes, str]:
    """(gpx 바이트, 파일명). 위치 점이 MIN_POINTS 미만이면 NoGpsError, 활동이 없으면 LookupError."""
    ids = group_activity_ids(conn, activity_id)
    best, n = _best_member(conn, ids)
    core = conn.execute("SELECT name, start_time FROM activity_summaries WHERE id=?", (activity_id,)).fetchone()
    if core is None:
        raise LookupError(activity_id)
    if n < MIN_POINTS:
        raise NoGpsError()
    start = _parse_start(core[1])
    ET.register_namespace("", _NS)
    ET.register_namespace("gpxtpx", _TPX)
    gpx = ET.Element(f"{{{_NS}}}gpx", {"version": "1.1", "creator": "RunPulse"})
    trk = ET.SubElement(gpx, f"{{{_NS}}}trk")
    ET.SubElement(trk, f"{{{_NS}}}name").text = core[0] or f"활동 {activity_id}"
    seg = ET.SubElement(trk, f"{{{_NS}}}trkseg")
    rows = conn.execute(
        "SELECT elapsed_sec, latitude, longitude, altitude_m, heart_rate, cadence FROM activity_streams "
        "WHERE activity_id=? AND latitude IS NOT NULL AND longitude IS NOT NULL ORDER BY elapsed_sec", (best,))
    for el, lat, lon, alt, hr, cad in rows:
        pt = ET.SubElement(seg, f"{{{_NS}}}trkpt", {"lat": f"{lat:.6f}", "lon": f"{lon:.6f}"})
        if alt is not None:
            ET.SubElement(pt, f"{{{_NS}}}ele").text = f"{alt:.1f}"
        ET.SubElement(pt, f"{{{_NS}}}time").text = (start + timedelta(seconds=el)).strftime("%Y-%m-%dT%H:%M:%SZ")
        if hr is not None or cad is not None:
            ext = ET.SubElement(ET.SubElement(pt, f"{{{_NS}}}extensions"), f"{{{_TPX}}}TrackPointExtension")
            if hr is not None:
                ET.SubElement(ext, f"{{{_TPX}}}hr").text = str(int(hr))
            if cad is not None:
                ET.SubElement(ext, f"{{{_TPX}}}cad").text = str(int(cad))
    body = ET.tostring(gpx, encoding="utf-8", xml_declaration=True)
    return body, f"runpulse-{start.strftime('%Y%m%d')}-{activity_id}.gpx"
