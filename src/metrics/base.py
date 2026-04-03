"""MetricCalculator 기본 클래스 + CalcContext + CalcResult.

Phase 4 핵심 인프라. 설계서 4-1 기준.
"""
from __future__ import annotations

import json as json_mod
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Optional

log = logging.getLogger(__name__)


@dataclass
class CalcResult:
    """계산 결과 하나. metric_store에 저장될 데이터."""
    metric_name: str
    scope_type: str
    scope_id: str
    category: str
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    json_value: Optional[str] = None
    confidence: Optional[float] = None

    def is_empty(self) -> bool:
        return (self.numeric_value is None
                and self.text_value is None
                and self.json_value is None)


class MetricCalculator(ABC):
    """모든 RunPulse 메트릭 계산기의 기본 클래스."""
    name: str = ""
    provider: str = "runpulse:formula_v1"
    version: str = "1.0"
    scope_type: str = "activity"
    category: str = ""
    requires: list[str] = []
    produces: list[str] = []

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not cls.produces:
            cls.produces = [cls.name] if cls.name else []

    @abstractmethod
    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        ...

    def _result(self, value=None, text=None, json_val=None,
                confidence=None, scope_id=None, metric_name=None) -> CalcResult:
        return CalcResult(
            metric_name=metric_name or self.name,
            scope_type=self.scope_type,
            scope_id=scope_id or "",
            category=self.category,
            numeric_value=float(value) if value is not None else None,
            text_value=text,
            json_value=(json_mod.dumps(json_val, ensure_ascii=False)
                        if json_val is not None else None),
            confidence=confidence,
        )


@dataclass
class CalcContext:
    """Calculator에 전달되는 컨텍스트. lazy-load."""
    conn: object
    scope_type: str
    scope_id: str
    _activity_cache: Optional[dict] = field(default=None, repr=False)

    @property
    def activity(self) -> dict:
        if self._activity_cache is None and self.scope_type == "activity":
            row = self.conn.execute(
                "SELECT * FROM activity_summaries WHERE id = ?",
                [int(self.scope_id)],
            ).fetchone()
            if row:
                cols = [d[0] for d in self.conn.execute(
                    "SELECT * FROM activity_summaries LIMIT 0"
                ).description]
                self._activity_cache = dict(zip(cols, row))
            else:
                self._activity_cache = {}
        return self._activity_cache or {}

    def get_metric(self, metric_name: str, provider: str = None,
                   scope_type: str = None, scope_id: str = None) -> Optional[float]:
        st = scope_type or self.scope_type
        sid = scope_id or self.scope_id
        if provider:
            row = self.conn.execute(
                "SELECT numeric_value FROM metric_store "
                "WHERE scope_type=? AND scope_id=? AND metric_name=? AND provider=?",
                [st, sid, metric_name, provider],
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT numeric_value FROM metric_store "
                "WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1",
                [st, sid, metric_name],
            ).fetchone()
        return row[0] if row else None

    def get_metric_json(self, metric_name: str, provider: str = None) -> Optional[str]:
        if provider:
            row = self.conn.execute(
                "SELECT json_value FROM metric_store "
                "WHERE scope_type=? AND scope_id=? AND metric_name=? AND provider=?",
                [self.scope_type, self.scope_id, metric_name, provider],
            ).fetchone()
        else:
            row = self.conn.execute(
                "SELECT json_value FROM metric_store "
                "WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1",
                [self.scope_type, self.scope_id, metric_name],
            ).fetchone()
        return row[0] if row else None

    def get_metric_text(self, metric_name: str) -> Optional[str]:
        row = self.conn.execute(
            "SELECT text_value FROM metric_store "
            "WHERE scope_type=? AND scope_id=? AND metric_name=? AND is_primary=1",
            [self.scope_type, self.scope_id, metric_name],
        ).fetchone()
        return row[0] if row else None

    def get_daily_metric_series(self, metric_name: str, days: int,
                                provider: str = None) -> list[tuple[str, float]]:
        if self.scope_type == "daily":
            end_date = self.scope_id
        else:
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)
        ).strftime("%Y-%m-%d")
        if provider:
            rows = self.conn.execute(
                "SELECT scope_id, numeric_value FROM metric_store "
                "WHERE scope_type='daily' AND metric_name=? AND provider=? "
                "AND scope_id BETWEEN ? AND ? ORDER BY scope_id",
                [metric_name, provider, start_date, end_date],
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT scope_id, numeric_value FROM metric_store "
                "WHERE scope_type='daily' AND metric_name=? AND is_primary=1 "
                "AND scope_id BETWEEN ? AND ? ORDER BY scope_id",
                [metric_name, start_date, end_date],
            ).fetchall()
        return [(r[0], r[1]) for r in rows if r[1] is not None]

    def get_activities_in_range(self, days: int, activity_type: str = None) -> list[dict]:
        if self.scope_type == "daily":
            end = datetime.strptime(self.scope_id, "%Y-%m-%d")
        else:
            end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)
        sql = ("SELECT * FROM activity_summaries "
               "WHERE start_time >= ? AND start_time <= ?")
        params: list = [start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d 23:59:59")]
        if activity_type:
            sql += " AND activity_type = ?"
            params.append(activity_type)
        sql += " ORDER BY start_time"
        rows = self.conn.execute(sql, params).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self.conn.execute(
            "SELECT * FROM activity_summaries LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]

    def get_activity_metric(self, activity_id: int, metric_name: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE scope_type='activity' AND scope_id=? AND metric_name=? AND is_primary=1",
            [str(activity_id), metric_name],
        ).fetchone()
        return row[0] if row else None

    def get_streams(self, activity_id: int = None) -> list[dict]:
        aid = activity_id or (int(self.scope_id) if self.scope_type == "activity" else None)
        if aid is None:
            return []
        rows = self.conn.execute(
            "SELECT * FROM activity_streams WHERE activity_id = ? ORDER BY elapsed_sec",
            [aid],
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self.conn.execute(
            "SELECT * FROM activity_streams LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]

    def get_laps(self, activity_id: int = None) -> list[dict]:
        aid = activity_id or (int(self.scope_id) if self.scope_type == "activity" else None)
        if aid is None:
            return []
        rows = self.conn.execute(
            "SELECT * FROM activity_laps WHERE activity_id = ? ORDER BY lap_index",
            [aid],
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self.conn.execute(
            "SELECT * FROM activity_laps LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]

    def get_wellness(self, date: str = None) -> dict:
        d = date or self.scope_id
        row = self.conn.execute(
            "SELECT * FROM daily_wellness WHERE date = ?", [d]
        ).fetchone()
        if row:
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info(daily_wellness)"
            ).fetchall()]
            return dict(zip(cols, row))
        return {}
