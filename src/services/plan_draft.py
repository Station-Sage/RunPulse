"""AI 플랜 초안 (V2-AI-CLAUDE-QUEUE E5-c, plan_draft_v1) — 규칙 계획을 baseline 으로 opus 가 이지/롱런 거리·설명을 다듬는다.

흐름: 규칙 미리보기(want_rows)로 baseline → 앞 HORIZON 주만 LLM 에 전달 → 게이트 검증(날짜·종류 불변, 거리 ±15%,
제약 한계, week_violations) 통과분만 ai_outputs(kind='plan_draft')에 저장 → 사용자가 확인하면 plan_replan_service.apply 에
plan_override 로 넘겨 일반 재계획과 같은 경로(되돌리기 포함)로 반영한다. 실패하면 저장하지 않고 사유만 남기며 규칙 계획이 그대로 쓰인다.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import sqlite3
import threading
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

log = logging.getLogger(__name__)

KIND = "plan_draft"
HORIZON = 4
SHIFT_MAX = 0.15
_FLEX = ("easy", "recovery", "long")
_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "plan_draft.txt"
_KM_RE = re.compile(r"(\d+(?:\.\d+)?)km")
_running: set[str] = set()
_lock = threading.Lock()


_KEEP_PARAMS = ("recent_weekly_km", "recent_long_km", "target_time_sec", "plan_method")


def _weeks(rows: list[dict]) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for r in rows:
        d = date.fromisoformat(r["date"])
        out.setdefault((d - timedelta(days=d.weekday())).isoformat(), []).append(r)
    return out


def method_info(method_id: str | None) -> dict:
    from src.training.methods.registry import get_method
    m = get_method(method_id)
    return {"id": m.id, "label": m.label, "summary": m.summary, "pros": list(m.pros), "cons": list(m.cons),
            "ai_note": m.ai_note, "long_cap_km": m.long_cap_km}


def build_input(conn: sqlite3.Connection, baseline: dict[str, list[dict]], method_id: str | None = None) -> dict:
    from src.ai.tool_exec_plan_constraints import _exec_get_plan_constraints
    weeks = []
    for ws in sorted(baseline)[:HORIZON]:
        weeks.append({"week_start": ws, "sessions": [
            {"date": r["date"], "type": r["workout_type"], "distance_km": float(r.get("distance_km") or 0),
             "description": r.get("description") or ""} for r in baseline[ws]]})
    return {"constraints": _exec_get_plan_constraints(conn, {}), "method": method_info(method_id), "baseline": weeks}


def src_hash(inp: dict) -> str:
    return hashlib.sha256(json.dumps(inp, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def _check_week(ws: str, base: list[dict], new: list[dict], inp: dict) -> str | None:
    """주 하나를 게이트로 검증. 위반 사유 문자열 또는 None."""
    from src.training.plan_finalize import week_violations
    lim, prefs = inp["constraints"]["limits"], inp["constraints"]["prefs"]
    days = {"월": 0, "화": 1, "수": 2, "목": 3, "금": 4, "토": 5, "일": 6}
    run_days = [days[d] for d in prefs["workout_weekdays"]] or range(7)
    for b, n in zip(base, new):
        t, bk, nk = b["workout_type"], float(b.get("distance_km") or 0), float(n.get("distance_km") or 0)
        if abs(nk - bk) < 1e-9:
            continue
        if t not in _FLEX:
            return f"{b['date']}: {t} 세션 거리는 바꿀 수 없음"
        if abs(nk - bk) > bk * SHIFT_MAX + 1e-9:
            return f"{b['date']}: 거리 변경이 ±{SHIFT_MAX:.0%} 초과"
        if nk < lim["min_session_km"]:
            return f"{b['date']}: 최소 세션 거리 {lim['min_session_km']}km 미만"
        if t == "easy" and nk > lim["easy_max_km"]:
            return f"{b['date']}: 이지 상한 {lim['easy_max_km']}km 초과"
        cap = lim.get("long_abs_cap_km")
        if t == "long" and cap and nk > cap:
            return f"{b['date']}: 롱런 상한 {cap}km 초과"
        mcap = (inp.get("method") or {}).get("long_cap_km")
        if t == "long" and mcap and nk > mcap:
            return f"{b['date']}: 이 훈련 방식의 롱런 상한 {mcap}km 초과"
    tb, tn = sum(float(r.get("distance_km") or 0) for r in base), sum(float(r.get("distance_km") or 0) for r in new)
    if tb > 0 and tn > tb * (1 + SHIFT_MAX):
        return f"{ws} 주 총거리가 baseline 대비 {SHIFT_MAX:.0%} 초과"
    pre = set(week_violations(base, run_days))
    v = [x for x in week_violations(new, run_days) if x not in pre]
    return v[0] if v else None


def validate(inp: dict, baseline: dict[str, list[dict]], out: str | None) -> tuple[dict | None, str | None]:
    """응답 → ({summary, weeks:{week_start: 병합된 행 목록}}, None) 또는 (None, 실패 사유)."""
    m = re.search(r"\{.*\}", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else None
    except ValueError:
        d = None
    if not isinstance(d, dict) or not isinstance(d.get("summary"), str) or not isinstance(d.get("weeks"), list):
        return None, "응답 형식 오류"
    summary = d["summary"].strip()
    if not summary or len(summary) > 160 or "#" in summary or "*" in summary:
        return None, "요약 형식 오류"
    allowed = {w["week_start"] for w in inp["baseline"]}
    merged: dict[str, list[dict]] = {}
    for w in d["weeks"]:
        ws = w.get("week_start") if isinstance(w, dict) else None
        if ws not in allowed or not isinstance(w.get("sessions"), list):
            return None, "알 수 없는 주"
        rows = [dict(r) for r in baseline[ws]]
        by_date = {r["date"]: r for r in rows}
        for s in w["sessions"]:
            r = by_date.get(s.get("date")) if isinstance(s, dict) else None
            if r is None:
                return None, "알 수 없는 날짜"
            km, desc, why = s.get("distance_km"), s.get("description"), s.get("rationale") or ""
            if not isinstance(km, (int, float)) or isinstance(km, bool) or not isinstance(desc, str) or not isinstance(why, str):
                return None, f"{r['date']}: 필드 형식 오류"
            if len(why) > 80 or len(desc) > 200:
                return None, f"{r['date']}: 길이 초과"
            for t in (desc, why):
                if "#" in t or "*" in t:
                    return None, f"{r['date']}: 마크다운 금지"
            r.update(distance_km=round(float(km), 1), description=desc.strip(), rationale=why.strip())
            if r["workout_type"] in _FLEX:
                r["structure"] = None
        bad = _check_week(ws, baseline[ws], rows, inp)
        if bad:
            return None, bad
        merged[ws] = rows
    return {"summary": summary, "weeks": merged}, None


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _put(conn: sqlite3.Connection, h: str, body: dict) -> None:
    conn.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at) VALUES (?,?,?,?,?)",
                 (KIND, "latest", h, json.dumps(body, ensure_ascii=False), _now()))
    conn.commit()


def latest(conn: sqlite3.Connection) -> dict | None:
    r = conn.execute("SELECT body_json FROM ai_outputs WHERE kind=? AND scope_key='latest'", (KIND,)).fetchone()
    return json.loads(r[0]) if r else None


def generate(conn: sqlite3.Connection, config: dict | None, params: dict, today: date | None = None) -> dict:
    """초안 생성(블로킹 — 백그라운드에서 호출). 결과 body 를 저장·반환. state: ready | failed."""
    from src.ai import provider_claude_queue as pcq
    from src.services import plan_replan_service as svc
    base = svc.preview(conn, {**params, "want_rows": True}, today)
    baseline = _weeks(base["plan_rows"] or [])
    if not baseline:
        body = {"state": "failed", "reason": "baseline 없음"}
        _put(conn, "", body)
        return body
    inp = build_input(conn, baseline, base.get("plan_method"))
    h = src_hash(inp)
    cur = latest(conn)
    if cur and cur.get("hash") == h and cur.get("state") == "ready":
        return cur
    body: dict = {"state": "failed", "hash": h, "anchor_monday": base["anchor_monday"]}
    if not pcq.available(conn, config):
        body["reason"] = "AI 큐를 사용할 수 없음"
    else:
        prompt = _TEMPLATE.read_text(encoding="utf-8").replace("{{INPUT}}", json.dumps(inp, ensure_ascii=False))
        from src.mcp_remote.policy import LOCAL_ONLY_TOOLS, REMOTE_TOOLS
        res, why = None, "AI 응답 없음"
        for attempt in range(2):
            p = prompt if attempt == 0 else prompt + f"\n\n직전 응답은 검증에서 거절됐습니다: {why}. 이 문제를 고쳐 JSON 만 다시 출력하세요."
            out = pcq.try_complete(conn, config, kind="plan_draft", prompt=p, tools="read",
                                   allowed_tools=sorted(REMOTE_TOOLS | LOCAL_ONLY_TOOLS))
            res, why = validate(inp, baseline, out) if out else (None, "AI 응답 없음")
            if res or not out:
                break
        if res:
            changed = sum(1 for ws, rows in res["weeks"].items() for a, b in zip(baseline[ws], rows)
                          if a.get("distance_km") != b.get("distance_km") or a.get("description") != b.get("description"))
            body.update(state="ready", summary=res["summary"], override=res["weeks"], changed=changed,
                        params={k: v for k, v in params.items() if k in _KEEP_PARAMS})
        else:
            body["reason"] = why
    _put(conn, h, body)
    return body


def start_background(db_path: str, config: dict | None, params: dict) -> bool:
    """이미 생성 중이면 False. 별도 스레드에서 generate 를 돌리고 진행 중 상태를 latest 에 남긴다."""
    with _lock:
        if db_path in _running:
            return False
        _running.add(db_path)

    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                generate(c, config, params)
        except Exception as e:  # noqa: BLE001
            log.warning("plan draft failed", exc_info=True)
            try:
                with sqlite3.connect(db_path, timeout=30) as c:
                    _put(c, "", {"state": "failed", "reason": f"오류: {str(e)[:80]}"})
            except sqlite3.Error:
                pass
        finally:
            with _lock:
                _running.discard(db_path)
    threading.Thread(target=_run, daemon=True, name="plan-draft").start()
    return True


def is_running(db_path: str) -> bool:
    with _lock:
        return db_path in _running


def apply_draft(conn: sqlite3.Connection, expect_anchor: str, today: date | None = None) -> dict:
    """저장된 ready 초안을 재계획 적용 경로로 반영(되돌리기 가능). 초안 없음·앵커 불일치는 ReplanError."""
    from src.services import plan_replan_service as svc
    cur = latest(conn)
    if not cur or cur.get("state") != "ready":
        raise svc.ReplanError("NO_DRAFT", "적용할 초안이 없습니다")
    if cur.get("anchor_monday") != expect_anchor:
        raise svc.ReplanError("CONFLICT", "초안 기준일이 바뀌었습니다. 초안을 다시 만드세요")
    p = {**cur.get("params", {}), "expect_anchor": expect_anchor, "plan_override": cur["override"]}
    return svc.apply(conn, p, today)
