"""MetricCalculator 기본 클래스 + CalcContext + CalcResult.

Phase 4 핵심 인프라. 설계서 4-1 + 보강 #1,#2,#11 기준.
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
    parent_metric_id: Optional[int] = None

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
    needs_streams: bool = False  # 보강 #2: stream prefetch 플래그

    # ── UI 메타데이터 (보강 #7) ──
    display_name: str = ""
    description: str = ""
    unit: str = ""
    ranges: dict = None           # {"low": [0,50], "high": [50,999]}
    higher_is_better: bool = None  # True/False/None(적절 범위가 중요)
    format_type: str = "number"   # "number"|"time"|"pace"|"percentage"|"json"
    decimal_places: int = 1

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
    """Calculator에 전달되는 컨텍스트. prefetch + cache-first, fallback DB."""
    conn: object
    scope_type: str
    scope_id: str

    # ── Per-scope cache (engine이 prefetch하거나 lazy-load) ──
    _activity_cache: Optional[dict] = field(default=None, repr=False)
    _metric_cache: Optional[dict] = field(default=None, repr=False)
    _stream_cache: Optional[list] = field(default=None, repr=False)

    # ── Prefetched shared data (engine이 일괄 로드) ──
    _prefetched_daily_loads: Optional[dict] = field(default=None, repr=False)
    _prefetched_wellness_map: Optional[dict] = field(default=None, repr=False)
    _prefetched_daily_metrics: Optional[dict] = field(default=None, repr=False)

    # ── Activity 데이터 접근 ──

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

    # ── Metric 데이터 접근 (cache-first) ──

    def get_metric(self, metric_name: str, provider: str = None,
                   scope_type: str = None, scope_id: str = None) -> Optional[float]:
        st = scope_type or self.scope_type
        sid = scope_id or self.scope_id

        # cache-first: 현재 scope의 요청이면 캐시 조회
        if st == self.scope_type and sid == self.scope_id and self._metric_cache is not None:
            key = (metric_name, provider)
            entry = self._metric_cache.get(key)
            if entry:
                return entry.get("numeric")
            # provider=None이면 primary 조회
            if provider is None:
                entry = self._metric_cache.get((metric_name, None))
                if entry:
                    return entry.get("numeric")
            return None

        # daily scope prefetch 데이터 참조
        if st == "daily" and self._prefetched_daily_metrics is not None:
            day_cache = self._prefetched_daily_metrics.get(sid, {})
            key = (metric_name, provider)
            entry = day_cache.get(key)
            if entry:
                return entry.get("numeric")
            if provider is None:
                entry = day_cache.get((metric_name, None))
                if entry:
                    return entry.get("numeric")
            return None

        # fallback: DB 직접 쿼리
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
        # cache-first
        if self._metric_cache is not None:
            key = (metric_name, provider) if provider else (metric_name, None)
            entry = self._metric_cache.get(key)
            if entry:
                return entry.get("json")
            return None
        # fallback
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
        # cache-first
        if self._metric_cache is not None:
            entry = self._metric_cache.get((metric_name, None))
            if entry:
                return entry.get("text")
            return None
        # fallback
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

        # prefetch된 daily metrics가 있으면 활용
        if self._prefetched_daily_metrics is not None:
            results = []
            current = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            while current <= end_dt:
                ds = current.strftime("%Y-%m-%d")
                day_cache = self._prefetched_daily_metrics.get(ds, {})
                key = (metric_name, provider) if provider else (metric_name, None)
                entry = day_cache.get(key)
                if entry and entry.get("numeric") is not None:
                    results.append((ds, entry["numeric"]))
                current += timedelta(days=1)
            return results

        # fallback: DB
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
        sql = ("SELECT * FROM v_canonical_activities "
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
            "SELECT * FROM v_canonical_activities LIMIT 0"
        ).description]
        return [dict(zip(cols, row)) for row in rows]

    def get_activity_metric(self, activity_id: int, metric_name: str) -> Optional[float]:
        row = self.conn.execute(
            "SELECT numeric_value FROM metric_store "
            "WHERE scope_type='activity' AND scope_id=? AND metric_name=? AND is_primary=1",
            [str(activity_id), metric_name],
        ).fetchone()
        return row[0] if row else None

    # ── Stream 접근 (cache-first) ──

    def get_streams(self, activity_id: int = None) -> list[dict]:
        aid = activity_id or (int(self.scope_id) if self.scope_type == "activity" else None)
        if aid is None:
            return []

        # cache-first
        if self._stream_cache is not None and (activity_id is None or activity_id == int(self.scope_id)):
            return self._stream_cache

        rows = self.conn.execute(
            "SELECT * FROM activity_streams WHERE activity_id = ? ORDER BY elapsed_sec",
            [aid],
        ).fetchall()
        if not rows:
            return []
        cols = [d[0] for d in self.conn.execute(
            "SELECT * FROM activity_streams LIMIT 0"
        ).description]
        result = [dict(zip(cols, row)) for row in rows]

        # 현재 scope의 stream이면 캐시
        if activity_id is None or (self.scope_type == "activity" and str(aid) == self.scope_id):
            self._stream_cache = result
        return result

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

    # ── Wellness 접근 (prefetch-first) ──

    def get_wellness(self, date: str = None) -> dict:
        d = date or self.scope_id
        # prefetch-first
        if self._prefetched_wellness_map is not None:
            return self._prefetched_wellness_map.get(d, {})
        # fallback: DB
        row = self.conn.execute(
            "SELECT * FROM daily_wellness WHERE date = ?", [d]
        ).fetchone()
        if row:
            cols = [c[1] for c in self.conn.execute(
                "PRAGMA table_info(daily_wellness)"
            ).fetchall()]
            return dict(zip(cols, row))
        return {}

    # ── Daily Load 접근 (prefetch-first, PMC/LSI/Monotony용) ──

    def get_daily_load(self, date_str: str) -> float:
        """prefetch된 daily TRIMP 합산. PMC, LSI, Monotony에서 사용."""
        if self._prefetched_daily_loads is not None:
            return self._prefetched_daily_loads.get(date_str, 0)
        # fallback: direct query
        rows = self.conn.execute("""
            SELECT m.numeric_value
            FROM metric_store m
            JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
            WHERE m.scope_type = 'activity'
            AND m.metric_name = 'trimp' AND m.is_primary = 1
            AND substr(a.start_time, 1, 10) = ?
        """, [date_str]).fetchall()
        return sum(r[0] or 0 for r in rows)

    # ── 계산 결과를 metric_cache에 즉시 반영 ──

    def get_activity_metric_series(self, metric_name: str, days: int,
                                    activity_type: str = None,
                                    include_json: bool = False,
                                    ) -> list[dict]:
        """activity-scope metric을 날짜 범위로 조회.

        반환: [{"activity_id": int, "date": str, "numeric": float,
                "json": str|None, "activity_type": str}, ...]
        패턴 A 쿼리를 범용화: tpdi, rec, sapi, teroi 등에서 사용.
        """
        if self.scope_type == "daily":
            end_date = self.scope_id
        else:
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)
        ).strftime("%Y-%m-%d")

        cols = "ms.numeric_value, a.id, DATE(a.start_time), a.activity_type"
        if include_json:
            cols += ", ms.json_value"

        sql = (
            f"SELECT {cols} FROM metric_store ms "
            "JOIN activity_summaries a ON CAST(ms.scope_id AS INTEGER) = a.id "
            "WHERE ms.metric_name=? AND ms.scope_type='activity' "
            "AND ms.numeric_value IS NOT NULL "
            "AND DATE(a.start_time) BETWEEN ? AND ?"
        )
        params: list = [metric_name, start_date, end_date]
        if activity_type:
            sql += " AND a.activity_type = ?"
            params.append(activity_type)
        sql += " ORDER BY a.start_time"

        rows = self.conn.execute(sql, params).fetchall()
        results = []
        for r in rows:
            entry = {
                "numeric": r[0], "activity_id": r[1],
                "date": r[2], "activity_type": r[3],
            }
            if include_json:
                entry["json"] = r[4]
            results.append(entry)
        return results

    def get_wellness_series(self, days: int,
                            fields: list[str] = None) -> list[dict]:
        """daily_wellness 이력을 날짜 범위로 조회.

        반환: [{"date": str, field1: val, field2: val, ...}, ...]
        패턴 C 쿼리를 범용화: crs 등에서 사용.
        """
        if self.scope_type == "daily":
            end_date = self.scope_id
        else:
            end_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        start_date = (
            datetime.strptime(end_date, "%Y-%m-%d") - timedelta(days=days)
        ).strftime("%Y-%m-%d")

        if fields:
            cols = ", ".join(["date"] + fields)
        else:
            cols = "*"

        rows = self.conn.execute(
            f"SELECT {cols} FROM daily_wellness "
            "WHERE date BETWEEN ? AND ? ORDER BY date",
            [start_date, end_date],
        ).fetchall()

        if not rows:
            return []
        col_names = [d[0] for d in self.conn.execute(
            f"SELECT {cols} FROM daily_wellness LIMIT 0"
        ).description]
        return [dict(zip(col_names, row)) for row in rows]

    def update_metric_cache(self, metric_name: str, provider: str,
                            numeric: float = None, text: str = None, json_val: str = None):
        """후속 calculator가 방금 계산된 값을 참조할 수 있도록 캐시 업데이트."""
        if self._metric_cache is None:
            self._metric_cache = {}
        entry = {"numeric": numeric, "text": text, "json": json_val}
        self._metric_cache[(metric_name, provider)] = entry
        self._metric_cache[(metric_name, None)] = entry  # primary로도 매핑

        # daily prefetched에도 반영
        if self.scope_type == "daily" and self._prefetched_daily_metrics is not None:
            if self.scope_id not in self._prefetched_daily_metrics:
                self._prefetched_daily_metrics[self.scope_id] = {}
            self._prefetched_daily_metrics[self.scope_id][(metric_name, provider)] = entry
            self._prefetched_daily_metrics[self.scope_id][(metric_name, None)] = entry


class ConfidenceBuilder:
    """메트릭 confidence를 체계적으로 계산하는 헬퍼 (보강 #6).

    사용법:
        cb = ConfidenceBuilder()
        cb.add_input("avg_hr", is_available=True, weight=0.3)
        cb.add_input("max_hr", is_available=True, weight=0.2, is_estimated=True)
        cb.add_input("streams", is_available=False, weight=0.5)
        confidence = cb.compute()  # → 0.4
    """

    def __init__(self):
        self._inputs: list[dict] = []

    def add_input(self, name: str, is_available: bool, weight: float = 1.0,
                  is_estimated: bool = False) -> "ConfidenceBuilder":
        self._inputs.append({
            "name": name,
            "available": is_available,
            "weight": weight,
            "estimated": is_estimated,
        })
        return self

    def compute(self) -> float:
        if not self._inputs:
            return 0.0
        total_weight = sum(i["weight"] for i in self._inputs)
        if total_weight == 0:
            return 0.0
        score = 0.0
        for inp in self._inputs:
            if inp["available"]:
                contribution = inp["weight"] / total_weight
                if inp["estimated"]:
                    contribution *= 0.7  # 추정값 30% 페널티
                score += contribution
        return round(min(score, 1.0), 2)
