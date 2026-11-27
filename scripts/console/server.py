"""관제 콘솔 HTTP 서버(C2) — stdlib http.server, 127.0.0.1 전용(외부 노출은 cloudflared + Cloudflare Access 가 담당).

GET  /api/overview /api/items /api/item/<id> /api/decisions /api/log /api/timers /api/roles, POST /api/control /api/tunables /api/interval /api/roles /api/decisions/<id> /api/review/<id> /api/failed/<id>.
라우팅은 route() 순수 함수로 분리해 소켓 없이 테스트한다. POST 는 JSON 만, Origin 이 있으면 Host 와 같아야 한다(CSRF 방어).
"""
from __future__ import annotations

import json
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from scripts.audit import consume, decisions, loop, progress, roles, steward, versioning
from scripts.autopilot import queue, settings
from scripts.console import control, items, overview

STATIC_DIR = Path(__file__).parent / "static"
FILES = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
         "/manifest.webmanifest": ("manifest.webmanifest", "application/manifest+json"), "/sw.js": ("sw.js", "application/javascript"),
         "/console.css": ("console.css", "text/css"), "/now.js": ("now.js", "application/javascript"), "/app.js": ("app.js", "application/javascript")}


def log_tail(n: int = 80, path: Path | None = None) -> list[str]:
    try:
        return (path or progress.LOG_PATH).read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except OSError:
        return []


def timers() -> dict:
    """타이머별 다음·마지막 실행 시각(에폭 초)과 활성 상태(systemctl list-timers). 실패하면 빈 값."""
    out = {t: {"next": 0, "last": 0, "active": "?"} for t in control.TIMERS}
    try:
        rows = json.loads(subprocess.run(["systemctl", "--user", "list-timers", "--all", "--output=json"],
                                         capture_output=True, text=True, timeout=10).stdout or "[]")
        for r in rows:
            t = str(r.get("unit", "")).removesuffix(".timer")
            if t in out:
                out[t].update(next=int(r.get("next") or 0) // 1_000_000, last=int(r.get("last") or 0) // 1_000_000, active="active")
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    return out


def tunable_values() -> dict:
    """조정 가능 항목의 현재 유효값(tunables.json 덮어쓰기 → 기본값)."""
    return {k: settings.tunable(k) for k in control.TUNABLES}


def choose(iid: str, choice: str, dpath: Path | None = None, state_path: Path | None = None, plan_path: Path | None = None, text: str = "", queue_path: Path | None = None) -> dict:
    recs = decisions.load(dpath)
    rec = next((r for r in recs if r["id"] == iid), None)
    if rec is None:
        return {"ok": False, "error": "없는 결정"}
    changeable = rec.get("kind") not in ("initiative", "vision")  # 버전·비전은 선택 즉시 반영돼 변경 불가
    if rec.get("kind") == "deploy_failed" and rec["status"] == "applied":
        return {"ok": False, "error": "이미 처리된 반영 실패 결정은 되돌릴 수 없습니다"}
    if rec["status"] not in ("open", "redo") and not (changeable and rec["status"] in ("chosen", "applied")):
        return {"ok": False, "error": f"이미 처리됨({rec['status']})"}
    if choice != "redo" and choice not in {o["key"] for o in rec["options"]}:
        return {"ok": False, "error": "없는 선택지"}
    with control.LOCK:
        if rec["status"] == "applied":
            err = consume.reopen(rec, queue_path or settings.QUEUE_PATH)
            if err:
                return {"ok": False, "error": err}
            decisions.save(recs, dpath)
        decisions.choose(iid, choice, dpath, text=text)
        control.audit("decision", {"id": iid, "choice": choice}, True)
        note = ""
        if rec.get("kind") == "initiative":
            cur = next(r for r in decisions.load(dpath) if r["id"] == iid)
            st = loop.load_state(state_path)
            note = versioning.apply_choice(cur, st, dpath=dpath, plan_path=plan_path)
            loop.save_state(st, state_path)
        elif rec.get("kind") == "vision":
            note = steward.apply_choice(next(r for r in decisions.load(dpath) if r["id"] == iid), dpath=dpath, plan_path=plan_path)
    return {"ok": True, "id": iid, "choice": choice, **({"note": note} if note else {})}


def review_action(iid: str, action: str, queue_path: Path | None = None) -> dict:
    """사후 검토 항목 처리 — done(확인 완료) | rework(queued 복귀, 시도 횟수 초기화). 병합 자체는 사용자가 한다."""
    qp = queue_path or settings.QUEUE_PATH
    if action not in ("done", "rework"):
        return {"ok": False, "error": "없는 동작"}
    with control.LOCK:
        it = next((x for x in queue.parse(qp) if x.item_id == iid), None)
        if it is None or it.stage != "review":
            return {"ok": False, "error": "검토 대기 항목이 아님"}
        if action == "done":
            queue.update_item(qp, iid, stage="done", resolution="reviewed")
        else:
            queue.update_item(qp, iid, stage="queued", attempts=0)
        control.audit("review", {"id": iid, "action": action}, True)
    return {"ok": True, "id": iid, "action": action}


def failed_action(iid: str, action: str, text: str = "", queue_path: Path | None = None) -> dict:
    """failed 항목 처리 — requeue(의견이 있으면 scope 에 지시로 추가, 시도 횟수·사유 초기화) | drop(done + dropped)."""
    qp = queue_path or settings.QUEUE_PATH
    if action not in ("requeue", "drop"):
        return {"ok": False, "error": "없는 동작"}
    with control.LOCK:
        it = next((x for x in queue.parse(qp) if x.item_id == iid), None)
        if it is None or it.stage != "failed":
            return {"ok": False, "error": "failed 항목이 아님"}
        if action == "drop":
            queue.update_item(qp, iid, stage="done", resolution="dropped")
        else:
            scope = list(it.scope) + ([f"사용자 의견: {text.strip()[:500]}"] if text.strip() else [])
            queue.update_item(qp, iid, stage="queued", attempts=0, scope=scope, fail_kind="", fail_reason="")
        control.audit("failed", {"id": iid, "action": action, "text": text[:200]}, True)
    return {"ok": True, "id": iid, "action": action}


def route(method: str, path: str, body: dict | None = None) -> tuple[int, dict | list]:
    body = body or {}
    if method == "GET":
        routes = {"/api/overview": overview.overview, "/api/decisions": overview.decision_list, "/api/items": items.item_list, "/api/log": log_tail, "/api/timers": timers, "/api/tunables": tunable_values, "/api/roles": roles.load}
        if path.startswith("/api/item/"):
            d = items.item_detail(path.rsplit("/", 1)[1])
            return (200, d) if d else (404, {"error": "없는 항목"})
        fn = routes.get(path)
        return (200, fn()) if fn else (404, {"error": "not found"})
    if path == "/api/control":
        r = control.act(str(body.get("action", "")))
    elif path == "/api/roles":
        with control.LOCK:
            r = roles.set_flag(str(body.get("role", "")), str(body.get("flag", "")), bool(body.get("value")))
            control.audit("roles", {k: body.get(k) for k in ("role", "flag", "value")}, bool(r.get("ok")))
    elif path == "/api/tunables":
        r = control.set_tunables(body.get("values") or {})
    elif path == "/api/interval":
        r = control.set_interval(str(body.get("timer", "")), body.get("minutes"))
    elif path.startswith("/api/review/"):
        r = review_action(path.rsplit("/", 1)[1], str(body.get("action", "")))
    elif path.startswith("/api/failed/"):
        r = failed_action(path.rsplit("/", 1)[1], str(body.get("action", "")), str(body.get("text", "")))
    elif path.startswith("/api/decisions/"):
        r = choose(path.rsplit("/", 1)[1], str(body.get("choice", "")), text=str(body.get("text", "")))
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
        if p in FILES:
            name, ctype = FILES[p]
            try:
                return self._send(200, (STATIC_DIR / name).read_bytes(), ctype)
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
