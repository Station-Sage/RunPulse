"""감사 스윕 러너(P2) — 합성 DB 로 앱을 띄워 인벤토리의 셀을 기계 감지하고 원장에 기록한다.

사용: .venv/bin/python scripts/audit/sweep.py [--states empty,small,error] [--viewports 390,desktop] [--limit N]
상태: empty(빈 DB)·small(합성 30일)·error(모든 /api 500). large 는 대용량 시드가 없어 미구현(원장에 미확인으로 남는다).
결함 후보가 없으면 '확인', 있으면 '이슈' + 후보 목록. 운영 DB 는 건드리지 않는다.
"""
from __future__ import annotations

import argparse
import json
import re
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.audit import inventory, procs  # noqa: E402

VIEWPORT_SIZE = {"390": {"width": 390, "height": 844}, "desktop": {"width": 1280, "height": 800}}
_PARAM = re.compile(r"\[(\w+)\]")
_SQL = {   # (라우트 접두어, 파라미터) → 샘플 조회 SQL. 없으면 DEFAULTS 사용
    ("/library/shoes", "id"): "SELECT id FROM user_shoes LIMIT 1",
    ("/coach/plan", "id"): "SELECT DISTINCT COALESCE(goal_id, 1) FROM planned_workouts LIMIT 1",
    ("/library", "id"): "SELECT id FROM activity_summaries ORDER BY start_time DESC LIMIT 1",
    ("/coach", "threadId"): "SELECT id FROM chat_threads LIMIT 1",
    ("", "date"): "SELECT date FROM daily_wellness ORDER BY date DESC LIMIT 1",
}
DEFAULTS = {"id": "1", "threadId": "1", "date": time.strftime("%Y-%m-%d"), "provider": "garmin", "group": "garmin-strava",
            "slug": "cirs", "period": "week", "ym": time.strftime("%Y-%m")}


def resolve_path(route: str, conn: sqlite3.Connection | None) -> str:
    """동적 라우트의 `[param]` 을 DB 샘플(없으면 기본값)로 치환한다."""
    def sub(m: re.Match) -> str:
        name = m.group(1)
        hits = [(pre, sql) for (pre, pname), sql in _SQL.items() if pname == name and route.startswith(pre)]
        if hits:
            sql = max(hits, key=lambda h: len(h[0]))[1]   # 가장 구체적인 접두어만 사용
            try:
                row = conn.execute(sql).fetchone() if conn else None
            except sqlite3.Error:
                row = None
            if row and row[0] is not None:
                return str(row[0])
        return DEFAULTS.get(name, "1")
    return _PARAM.sub(sub, route)


def apply_results(results: list[dict], ledger_path: Path = inventory.LEDGER_PATH) -> dict:
    """스윕 결과를 원장에 기록하고 {confirmed, issues} 개수를 돌려준다."""
    n = {"confirmed": 0, "issues": 0}
    for r in results:
        if r["issues"]:
            inventory.record(r["cell"], "이슈", "; ".join(r["issues"])[:300], ledger_path)
            n["issues"] += 1
        else:
            inventory.record(r["cell"], "확인", "기계 감지 통과", ledger_path)
            n["confirmed"] += 1
    return n


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def stop(proc: subprocess.Popen) -> None:
    """서버 종료 — terminate 후 5초 안에 안 죽으면 kill, 반드시 wait 로 회수."""
    procs.unregister(proc.pid)
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def _serve(db: Path) -> tuple[subprocess.Popen, str]:
    port = _free_port()
    proc = subprocess.Popen([sys.executable, str(ROOT / "scripts/synth_smoke/serve_synth.py"), str(db), str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    procs.register(proc.pid, "serve_synth.py")
    base = f"http://127.0.0.1:{port}"
    for _ in range(60):
        try:
            urllib.request.urlopen(base + "/v2/today", timeout=1)
            return proc, base
        except Exception:
            time.sleep(0.5)
    stop(proc)
    raise RuntimeError("synth server did not start")


def sweep_state(state: str, viewport: str, tmp: Path, limit: int | None, only: list[str] | None = None) -> list[dict]:
    from scripts.synth_smoke.seed_synth import seed

    db = tmp / f"{state}.db"
    seed(db, empty=(state == "empty"))
    conn = sqlite3.connect(db)
    inv = inventory.build(screens=inventory.frontend_screens(), apis=[])
    screens = [x for x in inv["screens"] if x in only] if only else inv["screens"]
    screens = screens[:limit] if limit else screens
    jobs = [{"cell": f"{s}|{state}|{viewport}", "path": resolve_path(s, conn)} for s in screens]
    conn.close()
    cfg = tmp / f"jobs_{state}_{viewport}.json"
    cfg.write_text(json.dumps({"viewport": VIEWPORT_SIZE[viewport], "state": state, "jobs": jobs}), encoding="utf-8")
    proc, base = _serve(db)
    try:
        cfg_data = json.loads(cfg.read_text(encoding="utf-8"))
        cfg_data["base"] = base
        cfg.write_text(json.dumps(cfg_data), encoding="utf-8")
        out = subprocess.run(["node", str(ROOT / "scripts/audit/sweep_pw.mjs"), str(cfg)], capture_output=True, text=True, timeout=1800)
        if out.returncode != 0:
            raise RuntimeError(out.stderr[-500:])
        return json.loads(out.stdout.strip().splitlines()[-1])
    finally:
        stop(proc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--states", default="empty,small,error")
    ap.add_argument("--viewports", default="390,desktop")
    ap.add_argument("--screens", default="", help="이 화면들만(쉼표 구분, 비우면 전부)")
    ap.add_argument("--limit", type=int, default=None, help="화면 수 제한(시험용)")
    args = ap.parse_args(argv)
    total, failed = 0, []
    combos = [(s, v) for s in args.states.split(",") for v in args.viewports.split(",")]
    with tempfile.TemporaryDirectory() as d:
        for i, (state, vp) in enumerate(combos, 1):
            print(f"[sweep] {i}/{len(combos)} {state} {vp} 시작", flush=True)
            t0 = time.time()
            try:
                res = sweep_state(state, vp, Path(d), args.limit, [x for x in args.screens.split(",") if x] or None)
            except Exception as e:   # 한 조합 실패가 나머지 스윕을 막지 않는다
                failed.append({"state": state, "viewport": vp, "error": str(e)[:200]})
                print(f"[sweep] {i}/{len(combos)} {state} {vp} 실패 ({time.time() - t0:.0f}s): {str(e)[:120]}", flush=True)
                continue
            total += len(res)
            print(f"[sweep] {i}/{len(combos)} {state} {vp} 완료 — {len(res)}셀 ({time.time() - t0:.0f}s)", flush=True)
            print(state, vp, apply_results(res), flush=True)
    print(json.dumps({"swept": total, "failed": failed}, ensure_ascii=False))
    return 1 if failed or total == 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
