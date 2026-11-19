"""지난주 훈련 이행 리뷰 (V2-AI-CLAUDE-QUEUE E3, adherence_v1) — 규칙 수치를 근거로 LLM 이 해설한다.

입력은 week_compliance 수치만 담은 평면 dict(민감 노트·질병 신호 미포함). 출력은 스키마·숫자 부분집합·
evidence_key 검증을 통과해야 ai_outputs(kind='adherence', scope_key=ISO주)에 저장된다. 실패하면 저장하지 않고
화면은 기존 수치 표시만 유지한다. 같은 입력 해시면 재호출하지 않는다.
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

KIND = "adherence"
_TEMPLATE = Path(__file__).resolve().parents[1] / "ai" / "prompt_templates" / "adherence.txt"
_SKIP_STATES = ("pre_plan", "rest")


def last_week_start(today: date | None = None) -> date:
    today = today or date.today()
    return today - timedelta(days=today.weekday() + 7)


def scope_key(week_start: date) -> str:
    y, w, _ = week_start.isocalendar()
    return f"{y}-W{w:02d}"


def build_input(conn: sqlite3.Connection, week_start: date) -> dict | None:
    """week_start 주의 이행 수치 평면 dict. 활성 목표·집계 대상이 없으면 None."""
    from src.services import plan_service as ps
    from src.training import week_compliance
    from src.training.goals import get_active_goal
    goal = get_active_goal(conn)
    if not goal:
        return None
    end = week_start + timedelta(days=6)
    wk = week_compliance.compute(conn, week_start, end, ps._effective_start(goal), goal_id=goal["id"])
    comp = wk["compliance"]
    if not comp["sessions"]["total"]:
        return None
    days = []
    for d in wk["days"]:
        if d["state"] in _SKIP_STATES:
            continue
        eff = d.get("effective") or {}
        row = {"date": d["date"], "state": d["state"], "planned_type": eff.get("workout_type"),
               "planned_km": d.get("planned_km"), "actual_km": d.get("actual_km"),
               "outcome": d.get("label"), "reason": d.get("reason")}
        days.append({k: v for k, v in row.items() if v is not None})
    return {"week": scope_key(week_start), "sessions": comp["sessions"], "volume": comp["volume"],
            "quality": comp["quality"], "days": days, "unplanned_runs": len(wk["unplanned_runs"])}


def evidence_keys(inp: dict) -> set[str]:
    return {"sessions", "volume", "quality", "unplanned_runs"} | {f"day:{d['date']}" for d in inp["days"]}


def src_hash(inp: dict) -> str:
    return hashlib.sha256(json.dumps(inp, sort_keys=True, ensure_ascii=False).encode()).hexdigest()[:16]


def validate(inp: dict, out: str | None) -> dict | None:
    """응답 → 정규화된 {summary, points, next_focus}. 스키마·길이·숫자·evidence 위반이면 None."""
    m = re.search(r"\{.*\}", out or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else None
    except ValueError:
        return None
    if not isinstance(d, dict):
        return None
    summary, nxt, pts = d.get("summary"), d.get("next_focus"), d.get("points")
    if not (isinstance(summary, str) and isinstance(nxt, str) and isinstance(pts, list)):
        return None
    summary, nxt = summary.strip(), nxt.strip()
    if not summary or len(summary) > 160 or len(nxt) > 80 or len(pts) > 3:
        return None
    keys, clean = evidence_keys(inp), []
    for p in pts:
        if not isinstance(p, dict) or not isinstance(p.get("text"), str):
            return None
        text, ek = p["text"].strip(), p.get("evidence_key")
        if not text or len(text) > 80 or ek not in keys:
            return None
        clean.append({"text": text, "evidence_key": ek})
    from src.services.ai_wording import numbers_ok
    src = json.dumps(inp, ensure_ascii=False)
    for t in [summary, nxt, *[p["text"] for p in clean]]:
        if "#" in t or "*" in t or not numbers_ok(src, t):   # 입력 수치(반올림 허용)만
            return None
    return {"summary": summary, "points": clean, "next_focus": nxt}


def _consent_ok(conn: sqlite3.Connection) -> bool:
    from src.services.ai_wording import _consent_ok as ok   # 단일 동의 기준(ADR-059)
    return ok(conn)


def get_cached(conn: sqlite3.Connection, week_start: date) -> dict | None:
    r = conn.execute("SELECT body_json FROM ai_outputs WHERE kind=? AND scope_key=?",
                     (KIND, scope_key(week_start))).fetchone()
    return json.loads(r[0]) if r else None


def generate(conn: sqlite3.Connection, config: dict | None, week_start: date) -> dict | None:
    """캐시(입력 해시 일치) → 큐 호출 → 검증 → 저장. 큐 불가·검증 실패는 None."""
    from src.ai import provider_claude_queue as pcq
    inp = build_input(conn, week_start)
    if inp is None:
        return None
    h, sk = src_hash(inp), scope_key(week_start)
    row = conn.execute("SELECT src_hash, body_json FROM ai_outputs WHERE kind=? AND scope_key=?",
                       (KIND, sk)).fetchone()
    if row and row[0] == h:
        return json.loads(row[1])
    if not _consent_ok(conn) or not pcq.available(conn, config):
        return None   # 동의 없음 → AI 호출 없음(사용자 결정 2026-11-19)
    prompt = (_TEMPLATE.read_text(encoding="utf-8").replace("{{KEYS}}", ", ".join(sorted(evidence_keys(inp))))
              .replace("{{INPUT}}", json.dumps(inp, ensure_ascii=False)))
    body = validate(inp, pcq.try_complete(conn, config, kind="adherence", prompt=prompt))
    if body is None:
        return None
    conn.execute("INSERT OR REPLACE INTO ai_outputs(kind, scope_key, src_hash, body_json, created_at)"
                 " VALUES (?,?,?,?,?)",
                 (KIND, sk, h, json.dumps(body, ensure_ascii=False),
                  datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    conn.commit()
    return body


def review_for_view(conn: sqlite3.Connection, week_start: date | None = None) -> dict | None:
    """화면용 — 저장된 리뷰에 근거 요약(evidence 라벨)을 붙여 반환. 없으면 None."""
    ws = week_start or last_week_start()
    body = get_cached(conn, ws) if _consent_ok(conn) else None   # 동의 없으면 저장된 AI 리뷰도 숨김
    if body is None:
        return None
    return {"week": scope_key(ws), "week_start": ws.isoformat(), **body}


def generate_in_background(db_path: str, config: dict | None) -> None:
    """동기화·조회 경로를 막지 않도록 별도 스레드에서 생성한다. 예외는 전파하지 않는다."""
    def _run() -> None:
        try:
            with sqlite3.connect(db_path, timeout=30) as c:
                generate(c, config, last_week_start())
        except Exception:  # noqa: BLE001
            log.warning("adherence review thread failed", exc_info=True)
    threading.Thread(target=_run, daemon=True, name="adherence-review").start()
