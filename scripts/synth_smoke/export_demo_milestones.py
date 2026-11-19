"""/demo 스냅샷에 마일스톤 전체 이력을 넣는다 — 합성 DB + 지난 1년 데모 사건 → `/library/milestones` 키 (ADR-057).

사용(저장소 루트): python3 scripts/synth_smoke/export_demo_milestones.py [snapshot.json]
export_demo_snapshot.mjs 로 스냅샷을 새로 뜬 뒤 실행한다(그 크롤러는 이 키를 덮어쓴다).

합성 DB(seed_synth)에 최근 30일 밖의 데모 사건(대회 완주·최장거리·연속 주·누적 거리·질병/회복 등)을 더하고
1회 백필 후 실제 조회 함수(list_milestones)로 전체 목록(최대 100건)을 만든다. 날짜는 스냅샷 기준일
(`/today` 의 as_of.date)로 평행 이동해 다른 화면과 어긋나지 않게 한다. 종류 필터·'더 보기'는
프론트 demoMilestones.ts 가 이 목록에서 서버와 같은 규칙으로 잘라 응답한다.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.synth_smoke.seed_synth import seed  # noqa: E402
from src.services import milestone_backfill, milestone_query  # noqa: E402

SNAPSHOT = ROOT / "frontend/static/demo/snapshot.json"
KEY = "/library/milestones"

# (오늘로부터 며칠 전, 종류, 제목, 상세) — 최근 30일(시드 활동 구간)보다 앞선 지난 1년의 이야기
PAST_EVENTS = [
    (40, "streak_weeks", "8주 연속 훈련", "주 2회 이상 러닝"),
    (52, "recovery", "질병에서 회복", "6일 만"),
    (58, "illness_start", "질병 시작", None),
    (75, "distance_threshold", "누적 300km 돌파", None),
    (96, "longest_run", "최장거리 21.1km", "이전 최장 18.0km"),
    (96, "race_finish", "하프마라톤 완주", "강변 하프마라톤 · 1:52:40"),
    (110, "race_registered", "대회 등록: 강변 하프마라톤", "하프마라톤 · 대회일 확정"),
    (130, "longest_run", "최장거리 18.0km", "이전 최장 16.0km"),
    (150, "pb", "5K PB 23:05", "5k PB 23:05 (페이스 4:37/km)"),
    (180, "distance_threshold", "누적 100km 돌파", None),
    (200, "goal_set", "목표 설정: 첫 하프마라톤", "하프마라톤 · 목표 1:55:00"),
]


def _add_past_events(conn: sqlite3.Connection, today: date) -> None:
    for days, typ, title, detail in PAST_EVENTS:
        conn.execute("INSERT INTO milestones (type, date, title, detail) VALUES (?, ?, ?, ?)",
                     (typ, (today - timedelta(days=days)).isoformat(), title, detail))


def shift_dates(history: dict, delta_days: int) -> dict:
    """items[].date 와 next_before 를 delta_days 만큼 평행 이동한다(순서·id 유지)."""
    def mv(d: str) -> str:
        return (date.fromisoformat(d) + timedelta(days=delta_days)).isoformat()
    items = [{**m, "date": mv(m["date"])} for m in history["items"]]
    nxt = history.get("next_before")
    if nxt:
        d, i = nxt.split(":")
        nxt = f"{mv(d)}:{i}"
    return {**history, "items": items, "next_before": nxt}


def build_history(anchor: date) -> dict:
    """합성 DB로 마일스톤 전체 이력을 만들고 anchor(스냅샷 기준일) 로 날짜를 옮긴다."""
    with tempfile.TemporaryDirectory() as tmp:
        db = Path(tmp) / "demo.db"
        seed(db)
        conn = sqlite3.connect(db)
        try:
            _add_past_events(conn, date.today())
            conn.commit()
            milestone_backfill.run_backfill(conn, apply=True)
            history = milestone_query.list_milestones(conn, limit=100)
        finally:
            conn.close()
    return shift_dates(history, (anchor - date.today()).days)


def main(path: Path = SNAPSHOT) -> int:
    snap = json.loads(path.read_text(encoding="utf-8"))
    anchor = date.fromisoformat(snap["/today"]["data"]["as_of"]["date"])
    snap[KEY] = {"data": build_history(anchor)}
    path.write_text(json.dumps(snap, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{KEY}: {len(snap[KEY]['data']['items'])}건 (기준일 {anchor})")
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]) if len(sys.argv) > 1 else SNAPSHOT))
