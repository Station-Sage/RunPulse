"""원본 링크·GPX 내보내기 테스트."""
import sqlite3
import xml.etree.ElementTree as ET

import pytest
from flask import Flask

from src.db_setup import create_tables
from src.services import activity_gpx, activity_source_links


@pytest.fixture
def conn_ids(tmp_path):
    f = tmp_path / "running.db"
    c = sqlite3.connect(str(f))
    create_tables(c)
    for src, sid in (("garmin", "123"), ("strava", "9/../x")):
        c.execute("INSERT INTO activity_summaries(source, source_id, activity_type, start_time, distance_m, duration_sec)"
                  " VALUES (?,?, 'running','2026-04-01T08:00:00Z',5000,1800)", (src, sid))
    c.commit()
    ids = [r[0] for r in c.execute("SELECT id FROM activity_summaries ORDER BY id")]
    yield f, c, ids
    c.close()


def _add_points(c, aid, n):
    for i in range(n):
        c.execute("INSERT INTO activity_streams(activity_id, source, elapsed_sec, latitude, longitude, heart_rate)"
                  " VALUES (?, 'garmin', ?, 37.5+?*0.0001, 127.0, 140)", (aid, i, i))
    c.commit()


def test_source_links_skip_unsafe_id(conn_ids):
    _, c, ids = conn_ids
    links = activity_source_links.source_links(c, ids[0])
    assert any(l["provider"] == "garmin" and l["url"].endswith("/activity/123") for l in links)
    assert all(l["provider"] != "strava" or "../" not in l["url"] for l in links)


def test_gpx_no_gps(conn_ids):
    _, c, ids = conn_ids
    _add_points(c, ids[0], 5)
    with pytest.raises(activity_gpx.NoGpsError):
        activity_gpx.build_gpx(c, ids[0])


def test_gpx_ok_and_missing(conn_ids):
    _, c, ids = conn_ids
    _add_points(c, ids[0], 12)
    body, name = activity_gpx.build_gpx(c, ids[0])
    assert name == f"runpulse-20260401-{ids[0]}.gpx"
    root = ET.fromstring(body)
    assert len(root.findall(".//{http://www.topografix.com/GPX/1/1}trkpt")) == 12
    with pytest.raises(LookupError):
        activity_gpx.build_gpx(c, 9999)


def test_export_routes(conn_ids, monkeypatch):
    f, c, ids = conn_ids
    _add_points(c, ids[0], 12)
    import src.api.routes_library_export as r
    monkeypatch.setattr(r, "db_path", lambda: f)
    app = Flask(__name__)
    from src.api import api_bp
    app.register_blueprint(api_bp)
    cl = app.test_client()
    g = cl.get(f"/api/v1/library/activities/{ids[0]}/export.gpx")
    assert g.status_code == 200 and "attachment" in g.headers["Content-Disposition"]
    assert cl.get("/api/v1/library/activities/9999/export.gpx").status_code == 404
    assert cl.get(f"/api/v1/library/activities/{ids[0]}/source-links").get_json()["data"]["links"]
