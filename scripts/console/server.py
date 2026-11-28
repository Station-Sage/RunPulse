"""관제 콘솔 HTTP 서버(C2) — stdlib http.server, 127.0.0.1 전용(외부 노출은 cloudflared + Cloudflare Access 가 담당).

GET  /api/overview /api/items /api/item/<id> /api/decisions /api/log /api/timers /api/roles, POST /api/control /api/timer /api/tunables /api/roles /api/decisions/<id> /api/decisions/<id>/note /api/decisions/<id>/review /api/review/<id> /api/failed/<id> /api/queued/<id>.
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
from scripts.autopilot import queue, settings, verify_doctor
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


def _show(unit: str, *props: str) -> dict:
    try:
        out = subprocess.run(["systemctl", "--user", "show", unit, *[f"-p{p}" for p in props]], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.SubprocessError):
        return {}
    return dict(ln.split("=", 1) for ln in out.splitlines() if "=" in ln)


def timers() -> dict:
    """타이머별 다음·마지막 실행(에폭 초), 활성·enable 상태, 마지막 서비스 결과. 실패하면 빈 값."""
    out = {t: {"next": 0, "last": 0, "active": "?", "enabled": "?", "result": "", "exit": ""} for t in control.TIMERS}
    try:
        rows = json.loads(subprocess.run(["systemctl", "--user", "list-timers", "--all", "--output=json"],
                                         capture_output=True, text=True, timeout=10).stdout or "[]")
        for r in rows:
            t = str(r.get("unit", "")).removesuffix(".timer")
            if t in out:
                out[t].update(next=int(r.get("next") or 0) // 1_000_000, last=int(r.get("last") or 0) // 1_000_000)
    except (OSError, subprocess.SubprocessError, ValueError):
        pass
    for t, o in out.items():
        tm = _show(f"{t}.timer", "ActiveState", "UnitFileState")
        sv = _show(f"{t}.service", "Result", "ExecMainStatus")
        o.update(active=tm.get("ActiveState", "?"), enabled=tm.get("UnitFileState", "?"), result=sv.get("Result", ""), exit=sv.get("ExecMainStatus", ""))
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
        elif choice != "redo" and rec.get("kind") != "deploy_failed":
            qp = queue_path or settings.QUEUE_PATH
            it = next((x for x in queue.parse(qp) if x.item_id == iid), None)
            if it is not None and it.stage in ("needs_decision", "failed"):  # 루프를 기다리지 않고 선택 즉시 큐에 반영
                consume.apply(qp, lambda f: {}, dpath)
    return {"ok": True, "id": iid, "choice": choice, **({"note": note} if note else {})}


def save_note(iid: str, text: str, dpath: Path | None = None) -> dict:
    """결정 카드의 의견만 저장(선택 안 함). 이미 큐에 반영된 결정은 '이 안으로 변경'을 눌러야 지시에 반영된다."""
    with control.LOCK:
        rec = decisions.save_note(iid, text, dpath)
        control.audit("decision_note", {"id": iid, "text": text[:200]}, rec is not None)
    return {"ok": True, "id": iid, "text": rec["text"]} if rec else {"ok": False, "error": "없는 결정"}


def review_card(iid: str, dpath: Path | None = None, ask=None) -> dict:
    """열린 split/verify 결정 카드를 처음 볼 때 에이전트가 검토한다(호출은 락 밖 — 수 분 걸릴 수 있음). 결과는 카드에 캐시."""
    from scripts.autopilot import card_review
    cur = next((r for r in decisions.load(dpath) if r["id"] == iid), None)
    if cur is None:
        return {"ok": False, "error": "없는 결정"}
    if cur["status"] != "open" or cur.get("kind") not in card_review.KINDS or cur.get("review_source"):
        return {"ok": True, "id": iid, "source": cur.get("review_source", "none")}
    work = json.loads(json.dumps(cur))
    res = card_review.review(work, ask=ask)
    if res["source"] in ("agent", "rule", "pending"):
        with control.LOCK:
            recs = decisions.load(dpath)
            tgt = next((r for r in recs if r["id"] == iid), None)
            if tgt is not None and tgt["status"] == "open" and not tgt.get("review_source"):
                tgt.update({k: work[k] for k in ("review", "options", "recommendation", "recommend_why", "review_source", "split_plan", "review_tries") if k in work})
                decisions.save(recs, dpath)
                control.audit("decision_review", {"id": iid, "source": res["source"]}, True)
    return {"ok": True, "id": iid, "source": res["source"]}


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


def queued_action(iid: str, action: str, queue_path: Path | None = None) -> dict:
    """대기 항목 우선순위 — up(한 칸 위) | top(맨 앞). 파일 순서가 실행 순서라 BACKLOG 에서 블록을 옮긴다."""
    with control.LOCK:
        err = queue.move_item(queue_path or settings.QUEUE_PATH, iid, action)
        control.audit("queued", {"id": iid, "action": action}, not err)
    return {"ok": False, "error": err} if err else {"ok": True, "id": iid, "action": action}


def failed_action(iid: str, action: str, text: str = "", queue_path: Path | None = None) -> dict:
    """failed 항목 처리 — requeue(verify 실패는 원인 파일·이전 실패 출력, 의견이 있으면 scope 에 지시로 추가, 시도 횟수·사유 초기화) | drop(done + dropped)."""
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
            scope = list(it.scope)
            if it.fail_kind == "verify":  # 진단(원인 파일·실패 출력)을 자동으로 이어 붙여 같은 실패 반복을 막는다
                kind, body, target = verify_doctor.failed_diagnosis(it.fail_reason, it.scope)
                scope += ([target] if target else []) + ([f"이전 실패({kind}): {body[:400]}"] if kind else [])
            scope += [f"사용자 의견: {text.strip()[:500]}"] if text.strip() else []
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
    elif path == "/api/timer":
        r = control.set_timer(str(body.get("name", "")), bool(body.get("on")))
    elif path == "/api/tunables":
        r = control.set_tunables(body.get("values") or {})
    elif path.startswith("/api/review/"):
        r = review_action(path.rsplit("/", 1)[1], str(body.get("action", "")))
    elif path.startswith("/api/queued/"):
        r = queued_action(path.rsplit("/", 1)[1], str(body.get("action", "")))
    elif path.startswith("/api/failed/"):
        r = failed_action(path.rsplit("/", 1)[1], str(body.get("action", "")), str(body.get("text", "")))
    elif path.startswith("/api/decisions/") and path.endswith("/review"):
        r = review_card(path.split("/")[3])
    elif path.startswith("/api/decisions/") and path.endswith("/note"):
        r = save_note(path.split("/")[3], str(body.get("text", "")))
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
