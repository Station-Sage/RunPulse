"""import_service — 종류 감지, 사본 미리보기(원본 불변), 실행 결과, API 라우트."""
from __future__ import annotations

import io
import sqlite3
import zipfile

import pytest

from src.services import import_service as ims
from src.utils import sync_jobs

CSV = ("Activity ID,Activity Date,Activity Name,Activity Type,Distance,Moving Time,Elapsed Time\n"
       "111,\"Oct 1, 2026, 7:00:00 AM\",Morning,Run,10000,3000,3100\n"
       "222,\"Oct 3, 2026, 7:00:00 AM\",Easy,Run,5000,1500,1520\n"
       ",,bad,Run,1,1,1\n")


@pytest.fixture
def udb(monkeypatch, tmp_path):
    from src import db_setup

    p = tmp_path / "running.db"
    monkeypatch.setattr(db_setup, "get_db_path", lambda uid=None: p)
    monkeypatch.setattr(ims, "get_db_path", lambda uid=None: p)
    db_setup.init_db()
    monkeypatch.setattr(sync_jobs, "_jobs_db_path", lambda uid=None: str(tmp_path / "jobs.db"))
    return p


def _count(p):
    c = sqlite3.connect(p)
    try:
        return c.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
    finally:
        c.close()


def test_detect_kind(tmp_path):
    csv_p = tmp_path / "a.csv"
    csv_p.write_text(CSV, encoding="utf-8")
    other = tmp_path / "g.csv"
    other.write_text("활동 유형,날짜\n", encoding="utf-8")
    zbad = tmp_path / "b.zip"
    zbad.write_bytes(b"nope")
    zok = tmp_path / "ok.zip"
    with zipfile.ZipFile(zok, "w") as z:
        z.writestr("export/activities.csv", CSV)
    assert ims.detect_kind([csv_p])[0] == "strava_csv"
    assert ims.detect_kind([other])[0] == "garmin_csv"
    assert ims.detect_kind([zbad])[0] is None
    assert ims.detect_kind([zok])[0] == "strava_archive"
    assert ims.detect_kind([tmp_path / "x.fit", tmp_path / "y.gpx.gz"])[0] == "files"
    assert ims.detect_kind([tmp_path / "x.txt"])[1]
    assert ims.detect_kind([])[1]


def test_preview_does_not_touch_original(udb, tmp_path):
    p = tmp_path / "a.csv"
    p.write_text(CSV, encoding="utf-8")
    before = _count(udb)
    res = ims.preview("u", "strava_csv", [p], "strava")
    assert res["new"] == 2 and res["errors"] == 1 and res["recognized"] == 3
    assert res["period"]["from"].startswith("2026-10") and res["period"]["to"] >= res["period"]["from"]
    assert _count(udb) == before


def test_apply_then_duplicates(udb, tmp_path):
    p = tmp_path / "a.csv"
    p.write_text(CSV, encoding="utf-8")
    conn = sqlite3.connect(udb)
    first = ims.run_on(conn, "strava_csv", [p], "strava")
    second = ims.run_on(conn, "strava_csv", [p], "strava")
    conn.close()
    assert first["inserted"] == 2 and second["inserted"] == 0 and second["skipped"] == 2
    assert second["from"] is None


def test_safe_extract_rejects_traversal(tmp_path):
    z = tmp_path / "evil.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("../evil.csv", "x")
    with pytest.raises(ValueError):
        ims._safe_extract(z, tmp_path / "out")


def test_routes(udb, monkeypatch, tmp_path):
    from flask import Flask

    import src.api.routes_data_import as ri
    from src.api import api_bp

    monkeypatch.setattr(ri, "db_path", lambda: udb)
    monkeypatch.setattr(ri, "get_current_user_id", lambda: "u")
    monkeypatch.setattr(ims, "imports_dir", lambda uid: tmp_path / "imports")
    started = []
    monkeypatch.setattr(ims.threading, "Thread", lambda **kw: type("T", (), {"start": lambda s: started.append(kw)})())
    app = Flask(__name__)
    app.register_blueprint(api_bp)
    with app.test_client() as c:
        assert c.post("/api/v1/data/import/preview", data={}).status_code == 400
        bad = c.post("/api/v1/data/import/preview", data={"files": (io.BytesIO(b"x"), "a.txt")},
                     content_type="multipart/form-data")
        assert bad.status_code == 400 and bad.get_json()["error"]["code"] == "INVALID_UPLOAD"
        r = c.post("/api/v1/data/import/preview", data={"files": (io.BytesIO(CSV.encode()), "a.csv"), "source": "strava"},
                   content_type="multipart/form-data")
        d = r.get_json()["data"]
        assert r.status_code == 200 and d["new"] == 2 and d["kind"] == "strava_csv"
        assert c.post("/api/v1/data/import", json={}).status_code == 400
        assert c.post("/api/v1/data/import", json={"upload_id": "zzz", "source": "strava"}).status_code == 404
        r = c.post("/api/v1/data/import", json={"upload_id": d["upload_id"], "source": "strava"})
        assert r.status_code == 202 and started
        jid = r.get_json()["data"]["job_id"]
        assert c.post("/api/v1/data/import", json={"upload_id": d["upload_id"]}).status_code == 409
        assert c.get(f"/api/v1/data/imports/{jid}").get_json()["data"]["state"] == "queued"
        assert c.get("/api/v1/data/imports/nope").status_code == 404
        assert len(c.get("/api/v1/data/imports").get_json()["data"]["imports"]) == 1


def test_run_job_records_result(udb, monkeypatch, tmp_path):
    monkeypatch.setattr(ims, "imports_dir", lambda uid: tmp_path / "imports")
    up = tmp_path / "imports" / "abc"
    up.mkdir(parents=True)
    (up / "a.csv").write_text(CSV, encoding="utf-8")
    job = sync_jobs.create_job(ims.SERVICE, "2026-10-08", "2026-10-08")
    ims._run(job.id, "u", "abc", "strava_csv", "strava")
    v = ims.job_view(sync_jobs.get_job(job.id))
    assert v["state"] == "done" and v["result"]["new"] == 2 and v["result"]["suggest_recompute"] is True
    assert not up.exists()


def test_reimport_updates_changed_distance(udb, tmp_path):
    p = tmp_path / "a.csv"
    p.write_text(CSV, encoding="utf-8")
    conn = sqlite3.connect(udb)
    ims.run_on(conn, "strava_csv", [p], "strava")
    p.write_text(CSV.replace("10000", "10500"), encoding="utf-8")
    ims.run_on(conn, "strava_csv", [p], "strava")
    conn.commit()
    dist = conn.execute(
        "SELECT distance_m FROM activity_summaries WHERE source_id='111'").fetchone()[0]
    conn.close()
    assert dist == 10500
