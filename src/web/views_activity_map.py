"""활동 상세 — Leaflet + OpenStreetMap 경로 지도 렌더링.

Mapbox 대신 Leaflet(무료, API 키 불필요) + OSM 타일 사용.
"""
from __future__ import annotations

import json
import sqlite3

from .helpers import db_path


def render_map_placeholder(activity_id: int | None = None) -> str:
    """활동 경로 지도 (GPS 데이터 있으면 Leaflet 렌더링)."""
    _no_map = (
        "<div class='card' style='text-align:center;min-height:120px;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;'>"
        "<div style='font-size:2.5rem;margin-bottom:0.4rem;'>&#128506;</div>"
        "<h2 style='font-size:0.95rem;margin-bottom:0.3rem;'>활동 경로 지도</h2>"
    )
    if not activity_id:
        return _no_map + "<p class='muted' style='font-size:0.8rem;margin:0;'>활동을 선택하세요.</p></div>"

    coords = _load_coords(activity_id)
    if not coords:
        return _no_map + "<p class='muted' style='font-size:0.8rem;margin:0;'>GPS 데이터가 없습니다.</p></div>"

    return _render_leaflet_map(coords)


def _load_coords(activity_id: int) -> list[list[float]]:
    """activity_streams에서 latlng 좌표 로드."""
    try:
        with sqlite3.connect(str(db_path())) as conn:
            row = conn.execute(
                "SELECT data_json FROM activity_streams "
                "WHERE activity_id=? AND stream_type='latlng' LIMIT 1",
                (activity_id,),
            ).fetchone()
            # 그룹 내 다른 소스에서 GPS 탐색
            if not row or not row[0]:
                grp = conn.execute(
                    "SELECT matched_group_id FROM activity_summaries WHERE id=?",
                    (activity_id,),
                ).fetchone()
                if grp and grp[0]:
                    row = conn.execute(
                        "SELECT s.data_json FROM activity_streams s "
                        "JOIN activity_summaries a ON a.id=s.activity_id "
                        "WHERE a.matched_group_id=? AND s.stream_type='latlng' LIMIT 1",
                        (grp[0],),
                    ).fetchone()
            if row and row[0]:
                data = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if isinstance(data, list) and len(data) >= 2:
                    if isinstance(data[0], (list, tuple)):
                        return [[float(p[0]), float(p[1])] for p in data if len(p) >= 2]
                if isinstance(data, dict):
                    lats = data.get("lat", data.get("latitude", []))
                    lngs = data.get("lng", data.get("longitude", []))
                    if lats and lngs:
                        return [[float(la), float(lo)] for la, lo in zip(lats, lngs)]
    except Exception:
        pass
    return []


def _render_leaflet_map(coords: list[list[float]]) -> str:
    """Leaflet + OSM 타일로 GPS 경로 지도 렌더링."""
    # 다운샘플링 (최대 500포인트)
    if len(coords) > 500:
        step = len(coords) // 500
        coords = coords[::step]

    coords_json = json.dumps(coords)
    mid = coords[len(coords) // 2]

    return (
        "<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'/>"
        "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>"
        "<div class='card' style='padding:0;overflow:hidden;border-radius:20px;'>"
        "<div id='activity-map' style='height:300px;width:100%;'></div></div>"
        "<script>"
        "(function(){"
        "var el=document.getElementById('activity-map');"
        "if(!el||typeof L==='undefined')return;"
        f"var coords={coords_json};"
        f"var map=L.map('activity-map',{{zoomControl:false}}).setView([{mid[0]},{mid[1]}],13);"
        "L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{"
        "attribution:'&copy; OSM',maxZoom:18"
        "}).addTo(map);"
        "var latlngs=coords.map(function(c){return [c[0],c[1]];});"
        "var polyline=L.polyline(latlngs,{color:'#00d4ff',weight:3,opacity:0.9}).addTo(map);"
        "map.fitBounds(polyline.getBounds(),{padding:[20,20]});"
        "L.marker(latlngs[0],{title:'시작'}).addTo(map);"
        "L.marker(latlngs[latlngs.length-1],{title:'종료'}).addTo(map);"
        "})();</script>"
    )
