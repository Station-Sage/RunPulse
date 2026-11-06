"""GET /api/v1/library/metrics/training-balance — 스키마 키·파라미터 검증·503·<slug> 라우트 비충돌 (§8 T3)."""
import sqlite3

import pytest
from flask import Flask

from src.db_setup import create_tables, migrate_db

URL = "/api/v1/library/metrics/training-balance"


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "running.db"
    c = sqlite3.connect(str(db_file))
    create_tables(c)
    migrate_db(c)
    c.close()
    import src.api.routes_library_balance as mod
    orig = mod.db_path
    mod.db_path = lambda: db_file
    app = Flask(__name__)
    app.config["TESTING"] = True
    from src.api import api_bp
    app.register_blueprint(api_bp)
    with app.test_client() as cl:
        yield cl, mod, tmp_path
    mod.db_path = orig


def test_schema_keys_fixed(client):
    cl, _, _ = client
    res = cl.get(f"{URL}?date=2026-11-06")
    assert res.status_code == 200
    d = res.get_json()["data"]
    assert set(d) == {"as_of", "window_weeks", "state", "axes", "compare", "aux", "notes", "stale_text"}
    assert d["as_of"] == "2026-11-06" and d["state"] == "collecting" and d["compare"]["as_of"] == "2026-10-09"
    assert [a["key"] for a in d["axes"]] == ["volume", "long_run", "easy_base", "quality", "load", "recovery"]
    assert set(d["axes"][0]) == {"key", "label", "unit", "actual", "target", "basis", "score", "band", "status",
                                 "reason", "reason_text", "source", "computed_on", "stale"}


def test_default_date_uses_reference_today(client):
    cl, _, _ = client
    assert cl.get(URL).get_json()["data"]["as_of"]


@pytest.mark.parametrize("q", ["date=2026-13-01", "date=20261106", "date=2026-1-6", "compare_days=x",
                               "compare_days=-1", "compare_days=85"])
def test_invalid_params_400(client, q):
    cl, _, _ = client
    res = cl.get(f"{URL}?{q}")
    assert res.status_code == 400 and res.get_json()["error"]["code"] == "INVALID_PARAM"


def test_compare_zero_skips(client):
    cl, _, _ = client
    assert cl.get(f"{URL}?date=2026-11-06&compare_days=0").get_json()["data"]["compare"] is None


def test_no_db_503(client):
    cl, mod, tmp_path = client
    mod.db_path = lambda: tmp_path / "missing.db"
    res = cl.get(URL)
    assert res.status_code == 503 and res.get_json()["error"]["code"] == "NOT_FOUND"


def test_static_route_wins_over_slug(client):
    cl, _, _ = client
    adapter = cl.application.url_map.bind("localhost")
    endpoint, _ = adapter.match("/api/v1/library/metrics/training-balance")
    assert endpoint.endswith("get_library_training_balance")
