"""관제 콘솔 HTTP 서버(C2) — stdlib http.server, 127.0.0.1 전용(외부 노출은 cloudflared + Cloudflare Access 가 담당).

GET  /api/overview /api/decisions /api/log /api/timers, POST /api/control /api/tunables /api/interval /api/decisions/<id>.
라우팅은 route() 순수 함수로 분리해 소켓 없이 테스트한다. POST 는 JSON 만, Origin 이 있으면 Host 와 같아야 한다(CSRF 방어).
"""
from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from scripts.audit import decisions, progress
from scripts.console import control, overview

STATIC = Path(__file__).parent / "static" / "index.html"


def log_tail(n: int = 80, path: Path | None = None) -> list[str]:
    try:
        return (path or progress.LOG_PATH).read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def timers() -> dict:
    """타이머별 다음 실행·마지막 실행 시각(systemctl show). 실패하면 빈 값."""
    out = {}
    for t in control.TIMERS:
        try:
            r = subprocess.run(["systemctl", "--user", "show", f"{t}.timer", "-p", "NextElapseUSecRealtime", "-p", "LastTriggerUSec", "-p", "ActiveState"],
                               capture_output=True, text=True, timeout=10).stdout
            out[t] = dict(line.split("=", 1) for line in r.splitlines() if "=" in line)
        except (OSError, subprocess.SubprocessError):
            out[t] = {}
    return out


def choose(iid: str, choice: str, dpath: Path | None = None) -> dict:
    recs = decisions.load(dpath)
    rec = next((r for r in recs if r["id"] == iid), None)
    if rec is None:
        return {"ok": False, "error": "없는 결정"}
    if rec["status"] not in ("open", "redo"):
        return {"ok": False, "error": f"이미 처리됨({rec['status']})"}
    if choice != "redo" and choice not in {o["key"] for o in rec["options"]}:
        return {"ok": False, "error": "없는 선택지"}
    with control.LOCK:
        decisions.choose(iid, choice, dpath)
        control.audit("decision", {"id": iid, "choice": choice}, True)
    return {"ok": True, "id": iid, "choice": choice}


def route(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    body = body or {}
    if method == "GET":
        routes = {"/api/overview": overview.overview, "/api/decisions": overview.decision_list, "/api/log": log_tail, "/api/timers": timers}
        fn = routes.get(path)
        return (200, fn()) if fn else (404, {"error": "not found"})
    if path == "/api/control":
        r = control.act(str(body.get("action", "")))
    elif path == "/api/tunables":
        r = control.set_tunables(body.get("values") or {})
    elif path == "/api/interval":
        r = control.set_interval(str(body.get("timer", "")), body.get("minutes"))
    elif path.startswith("/api/decisions/"):
        r = choose(path.rsplit("/", 1)[1], str(body.get("choice", "")))
    else:
        return 404, {"error": "not found"}
    return (200 if r.get("ok") else 400), r


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, payload, ctype: str = "application/json") -> None:
        data = payload if isinstance(payload, bytes) else json.dumps(payload, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        p = urlparse(self.path).path
        if p in ("/", "/index.html"):
            try:
                return self._send(200, STATIC.read_bytes(), "text/html")
            except OSError:
                return self._send(404, {"error": "UI 없음"})
        self._send(*route("GET", p))

    def do_POST(self) -> None:  # noqa: N802
        origin, host = self.headers.get("Origin"), self.headers.get("Host", "")
        if origin and urlparse(origin).netloc != host:
            return self._send(403, {"error": "origin"})
        if "application/json" not in self.headers.get("Content-Type", ""):
            return self._send(415, {"error": "json only"})
        try:
            body = json.loads(self.rfile.read(min(int(self.headers.get("Content-Length", 0)), 65536)) or b"{}")
        except ValueError:
            return self._send(400, {"error": "bad json"})
        self._send(*route("POST", urlparse(self.path).path, body if isinstance(body, dict) else {}))

    def log_message(self, *a) -> None:
        pass


def main(port: int = 8765) -> None:
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main(int(sys.argv[1]) if len(sys.argv) > 1 else 8765)
