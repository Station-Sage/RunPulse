"""관제 서버 — 라우팅·결정 선택 검증·HTTP 실호출(127.0.0.1 임시 포트)."""
import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

from scripts.audit import decisions
from scripts.console import control, server


def _rec(status="open"):
    return {"id": "d1", "kind": "k", "status": status, "options": [{"key": "A", "name": "a", "pros": "", "cons": ""}], "choice": None}


def test_choose_validation(tmp_path, monkeypatch):
    monkeypatch.setattr(control.settings, "STATE_DIR", tmp_path)
    p = tmp_path / "d.json"
    decisions.save([_rec()], p)
    assert server.choose("zz", "A", p)["ok"] is False
    assert server.choose("d1", "Z", p)["ok"] is False
    assert server.choose("d1", "A", p)["ok"] is True and decisions.load(p)[0]["status"] == "chosen"
    assert server.choose("d1", "redo", p)["ok"] is False  # 이미 처리됨


def test_log_tail_and_route(tmp_path):
    p = tmp_path / "progress.log"
    p.write_text("\n".join(str(i) for i in range(200)))
    assert server.log_tail(5, p) == ["195", "196", "197", "198", "199"]
    assert server.route("GET", "/api/nope")[0] == 404
    assert server.route("POST", "/api/control", {"action": "bogus"})[0] == 400


def test_http_origin_and_content_type():
    srv = ThreadingHTTPServer(("127.0.0.1", 0), server.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{srv.server_port}"
    try:
        def post(headers):
            req = urllib.request.Request(base + "/api/control", data=json.dumps({"action": "bogus"}).encode(), headers=headers, method="POST")
            try:
                return urllib.request.urlopen(req).status
            except urllib.error.HTTPError as e:
                return e.code
        assert post({"Content-Type": "application/json", "Origin": "http://evil.example"}) == 403
        assert post({"Content-Type": "text/plain"}) == 415
        assert post({"Content-Type": "application/json"}) == 400
    finally:
        srv.shutdown()
