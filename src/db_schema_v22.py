"""스키마 v22 — 마일스톤 재계산의 종류 분리(A/B 비교용 원본 보존).

metric_recompute  = 같은 알고리즘 버전 안에서 값이 바뀐 것(데이터 변화) — 사용자에게 보여 준다.
algo_recompute    = 알고리즘 버전이 바뀌어 값이 달라진 것 — 저장만 하고 표시하지 않는다(알고리즘 A/B 기록).
milestones.provider = 그 값을 낸 provider (검토 중 알고리즘·참조값도 함께 저장해 A/B 비교에 쓴다).
"""
from __future__ import annotations

import sqlite3


def ensure_v22(conn: sqlite3.Connection) -> None:
    """milestones.provider 컬럼 보장 + 옛 재계산 행 분류(버전이 다른 것 → algo_recompute). 멱등."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(milestones)").fetchall()}
    if not cols:
        return
    if "provider" not in cols:
        conn.execute("ALTER TABLE milestones ADD COLUMN provider TEXT")
    # 옛 형식 detail = '1.0→2.0 적용' — 앞뒤 버전이 다르면 알고리즘 변경으로 인한 재계산
    for mid, detail in conn.execute(
            "SELECT id, detail FROM milestones WHERE type='metric_recompute' AND detail LIKE '%→%'").fetchall():
        old, _, new = (detail or "").replace(" 적용", "").partition("→")
        if old.strip() != new.strip():
            conn.execute("UPDATE milestones SET type='algo_recompute' WHERE id=?", (mid,))
