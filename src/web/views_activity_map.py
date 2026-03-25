"""활동 상세 — Mapbox 경로 지도 렌더링."""
from __future__ import annotations

import json
import sqlite3

from .helpers import db_path


def render_map_placeholder(activity_id: int | None = None) -> str:
    """활동 경로 지도 (Mapbox 토큰 있으면 렌더링, 없으면 안내)."""
    from src.utils.config import load_config
    token = load_config().get("mapbox", {}).get("token", "")
    _no_map = (
        "<div class='card' style='text-align:center;min-height:120px;"
        "display:flex;flex-direction:column;align-items:center;justify-content:center;'>"
        "<div style='font-size:2.5rem;margin-bottom:0.4rem;'>&#128506;</div>"
        "<h2 style='font-size:0.95rem;margin-bottom:0.3rem;'>활동 경로 지도</h2>"
    )
    if not token or not activity_id:
        return _no_map + "<p class='muted' style='font-size:0.8rem;margin:0;'>Mapbox 토큰 설정 후 표시됩니다.</p></div>"
    coords: list = []
    try:
        with sqlite3.connect(str(db_path())) as conn:
            row = conn.execute(
                "SELECT stream_data FROM activity_streams "
                "WHERE activity_id=? AND stream_type='latlng' LIMIT 1",
                (activity_id,),
            ).fetchone()
            if row and row[0]:
                coords = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    except Exception:
        pass
    if not coords or len(coords) < 2:
        return _no_map + "<p class='muted' style='font-size:0.8rem;margin:0;'>GPS 데이터가 없습니다.</p></div>"
    geojson_str = json.dumps({"type": "LineString", "coordinates": [[c[1], c[0]] for c in coords]})
    mid = coords[len(coords) // 2]
    center = json.dumps([mid[1], mid[0]])
    return (
        f"<div class='card' style='padding:0;overflow:hidden;border-radius:20px;'>"
        f"<div id='activity-map' style='height:300px;width:100%;'></div></div>"
        f"<script src='https://api.mapbox.com/mapbox-gl-js/v3.4.0/mapbox-gl.js'></script>"
        f"<link href='https://api.mapbox.com/mapbox-gl-js/v3.4.0/mapbox-gl.css' rel='stylesheet'/>"
        f"<script>(function(){{"
        f"if(!window.mapboxgl)return;mapboxgl.accessToken='{token}';"
        f"var map=new mapboxgl.Map({{container:'activity-map',style:'mapbox://styles/mapbox/dark-v11',center:{center},zoom:13}});"
        f"var g={geojson_str};map.on('load',function(){{"
        f"map.addSource('route',{{type:'geojson',data:{{type:'Feature',geometry:g}}}});"
        f"map.addLayer({{id:'route',type:'line',source:'route',paint:{{'line-color':'#00d4ff','line-width':3}}}});"
        f"var b=new mapboxgl.LngLatBounds();g.coordinates.forEach(function(c){{b.extend(c);}});"
        f"map.fitBounds(b,{{padding:40}});}});}})();</script>"
    )
