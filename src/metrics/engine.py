"""Metrics Engine — topological sort 기반 실행. 설계서 4-5 + 보강 #1,#2,#11 기준.

ALL_CALCULATORS 등록 → 의존성 그래프 해소 → prefetch → scope별 순차 실행 → metric_store 저장.
"""
from __future__ import annotations

import json as json_mod
import logging
import sqlite3
from collections import defaultdict
from datetime import date, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.utils.db_helpers import upsert_metric
from src.utils.metric_priority import resolve_for_scope
from src.utils.metric_priority import resolve_all_primaries

# ── Calculator 임포트 ──
from src.metrics.trimp import TRIMPCalculator
from src.metrics.hrss import HRSSCalculator
from src.metrics.decoupling import AerobicDecouplingCalculator
from src.metrics.gap import GAPCalculator
from src.metrics.classifier import WorkoutClassifier
from src.metrics.vdot import VDOTCalculator
from src.metrics.efficiency import EfficiencyFactorCalculator
from src.metrics.fearp import FEARPCalculator

from src.metrics.pmc import PMCCalculator
from src.metrics.acwr import ACWRCalculator
from src.metrics.lsi import LSICalculator
from src.metrics.monotony import MonotonyStrainCalculator
from src.metrics.utrs import UTRSCalculator
from src.metrics.cirs import CIRSCalculator
from src.metrics.di import DICalculator
from src.metrics.darp import DARPCalculator
from src.metrics.tids import TIDSCalculator
from src.metrics.rmr import RMRCalculator
from src.metrics.adti import ADTICalculator
from src.metrics.relative_effort import RelativeEffortCalculator
from src.metrics.wlei import WLEICalculator
from src.metrics.teroi import TEROICalculator
from src.metrics.tpdi import TPDICalculator
from src.metrics.rec import RECCalculator
from src.metrics.rtti import RTTICalculator
from src.metrics.critical_power import CriticalPowerCalculator
from src.metrics.sapi import SAPICalculator
from src.metrics.rri import RRICalculator
from src.metrics.eftp import EFTPCalculator
from src.metrics.vdot_adj import VDOTAdjCalculator
from src.metrics.marathon_shape import MarathonShapeCalculator
from src.metrics.crs import CRSCalculator

log = logging.getLogger(__name__)

from dataclasses import dataclass, field
import time as _time


@dataclass
class ComputeResult:
    """메트릭 계산 전체 결과 (보강 #3)."""
    total_calculators: int = 0
    total_scopes: int = 0
    computed_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    errors: list = field(default_factory=list)
    elapsed_seconds: float = 0.0

    def summary(self) -> str:
        return (f"Computed: {self.computed_count}, Skipped: {self.skipped_count}, "
                f"Errors: {self.error_count}, Time: {self.elapsed_seconds:.1f}s")


# ── Calculator 레지스트리 ──
ALL_CALCULATORS: list[MetricCalculator] = [
    TRIMPCalculator(),
    HRSSCalculator(),
    AerobicDecouplingCalculator(),
    GAPCalculator(),
    WorkoutClassifier(),
    VDOTCalculator(),
    EfficiencyFactorCalculator(),
    FEARPCalculator(),
    PMCCalculator(),
    ACWRCalculator(),
    LSICalculator(),
    MonotonyStrainCalculator(),
    UTRSCalculator(),
    CIRSCalculator(),
    DICalculator(),
    DARPCalculator(),
    TIDSCalculator(),
    RMRCalculator(),
    ADTICalculator(),
    RelativeEffortCalculator(),
    WLEICalculator(),
    TEROICalculator(),
    TPDICalculator(),
    RECCalculator(),
    RTTICalculator(),
    CriticalPowerCalculator(),
    SAPICalculator(),
    RRICalculator(),
    EFTPCalculator(),
    VDOTAdjCalculator(),
    MarathonShapeCalculator(),
    CRSCalculator(),
]


# ═══════════════════════════════════════════
# Topological Sort
# ═══════════════════════════════════════════

def _topological_sort(calculators: list[MetricCalculator]) -> list[MetricCalculator]:
    """의존성 그래프 기반 위상 정렬 (Kahn's algorithm)."""
    producer_map: dict[str, MetricCalculator] = {}
    for calc in calculators:
        for p in calc.produces:
            producer_map[p] = calc

    graph: dict[str, list[str]] = defaultdict(list)
    in_degree: dict[str, int] = {}

    for calc in calculators:
        key = calc.name
        if key not in in_degree:
            in_degree[key] = 0
        for req in calc.requires:
            if req in producer_map:
                dep_name = producer_map[req].name
                graph[dep_name].append(key)
                in_degree[key] = in_degree.get(key, 0) + 1

    queue = [k for k, v in in_degree.items() if v == 0]
    sorted_names: list[str] = []

    while queue:
        node = queue.pop(0)
        sorted_names.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    name_to_calc = {c.name: c for c in calculators}
    result = [name_to_calc[n] for n in sorted_names if n in name_to_calc]

    included = {c.name for c in result}
    for calc in calculators:
        if calc.name not in included:
            result.append(calc)

    return result


# ═══════════════════════════════════════════
# Prefetch 함수들 (보강 #1, #11)
# ═══════════════════════════════════════════

def _load_all_metrics_for_scope(conn: sqlite3.Connection,
                                scope_type: str, scope_id: str) -> dict:
    """한 scope의 모든 메트릭을 dict로 로드.
    key: (metric_name, provider) → {numeric, text, json}
    is_primary인 것은 (metric_name, None)으로도 매핑.
    """
    rows = conn.execute("""
        SELECT metric_name, provider, numeric_value, text_value, json_value, is_primary
        FROM metric_store WHERE scope_type = ? AND scope_id = ?
    """, [scope_type, scope_id]).fetchall()

    cache = {}
    for name, provider, num, text, json_val, is_primary in rows:
        entry = {"numeric": num, "text": text, "json": json_val}
        cache[(name, provider)] = entry
        if is_primary:
            cache[(name, None)] = entry
    return cache


def _prefetch_daily_trimp_sums(conn: sqlite3.Connection,
                               start_date: str, end_date: str) -> dict:
    """전체 기간의 날짜별 TRIMP 합산을 한 번에 로드. {date: trimp_sum}"""
    rows = conn.execute("""
        SELECT substr(a.start_time, 1, 10) as date,
               SUM(m.numeric_value) as total_trimp
        FROM metric_store m
        JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER) = a.id
        WHERE m.scope_type = 'activity'
        AND m.metric_name = 'trimp' AND m.is_primary = 1
        AND substr(a.start_time, 1, 10) BETWEEN ? AND ?
        GROUP BY date
    """, [start_date, end_date]).fetchall()
    return {r[0]: r[1] for r in rows}


def _prefetch_all_wellness(conn: sqlite3.Connection,
                           start_date: str, end_date: str) -> dict:
    """전체 기간의 daily_wellness를 한 번에 로드. {date: {col: value}}"""
    rows = conn.execute(
        "SELECT * FROM daily_wellness WHERE date BETWEEN ? AND ?",
        [start_date, end_date],
    ).fetchall()
    if not rows:
        return {}
    cols = [c[1] for c in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
    result = {}
    for row in rows:
        d = dict(zip(cols, row))
        result[d["date"]] = d
    return result


def _prefetch_daily_metrics(conn: sqlite3.Connection,
                            start_date: str, end_date: str) -> dict:
    """전체 기간의 daily scope metric_store를 한 번에 로드.
    {date: {(metric_name, provider): {numeric, text, json}}}
    """
    rows = conn.execute("""
        SELECT scope_id, metric_name, provider, numeric_value, text_value, json_value, is_primary
        FROM metric_store
        WHERE scope_type = 'daily' AND scope_id BETWEEN ? AND ?
    """, [start_date, end_date]).fetchall()

    result: dict = {}
    for scope_id, name, provider, num, text, json_val, is_primary in rows:
        if scope_id not in result:
            result[scope_id] = {}
        entry = {"numeric": num, "text": text, "json": json_val}
        result[scope_id][(name, provider)] = entry
        if is_primary:
            result[scope_id][(name, None)] = entry
    return result


def _load_streams(conn: sqlite3.Connection, activity_id: int) -> list[dict]:
    """활동의 stream 데이터를 로드."""
    rows = conn.execute(
        "SELECT * FROM activity_streams WHERE activity_id = ? ORDER BY elapsed_sec",
        [activity_id],
    ).fetchall()
    if not rows:
        return []
    cols = [d[0] for d in conn.execute(
        "SELECT * FROM activity_streams LIMIT 0"
    ).description]
    return [dict(zip(cols, row)) for row in rows]


# ═══════════════════════════════════════════
# Save Results
# ═══════════════════════════════════════════

def _save_results(conn: sqlite3.Connection, calc: MetricCalculator,
                  results: list[CalcResult], scope_id: str) -> int:
    """CalcResult 리스트를 metric_store에 저장."""
    saved = 0
    for r in results:
        if r.is_empty():
            continue
        r.scope_id = scope_id
        upsert_metric(
            conn,
            scope_type=r.scope_type,
            scope_id=r.scope_id,
            metric_name=r.metric_name,
            provider=calc.provider,
            numeric_value=r.numeric_value,
            text_value=r.text_value,
            json_value=(json_mod.loads(r.json_value) if isinstance(r.json_value, str) else r.json_value) if r.json_value else None,
            category=r.category,
            algorithm_version=calc.version,
            confidence=r.confidence,
        )
        saved += 1
    return saved


# ═══════════════════════════════════════════
# Activity-Scope 실행 (prefetch 적용)
# ═══════════════════════════════════════════

def run_activity_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """단일 활동에 대한 모든 activity-scope calculator 실행 (prefetch 포함)."""
    sorted_calcs = _topological_sort(
        [c for c in ALL_CALCULATORS if c.scope_type == "activity"]
    )
    results: dict = {}
    failed: list[dict] = []

    # prefetch: activity row
    row = conn.execute(
        "SELECT * FROM activity_summaries WHERE id = ?", [activity_id]
    ).fetchone()
    activity_cache = None
    if row:
        cols = [d[0] for d in conn.execute(
            "SELECT * FROM activity_summaries LIMIT 0"
        ).description]
        activity_cache = dict(zip(cols, row))

    # prefetch: metrics for this scope
    metric_cache = _load_all_metrics_for_scope(conn, "activity", str(activity_id))

    # prefetch: streams (only if any calculator needs them)
    stream_cache = None
    if any(c.needs_streams for c in sorted_calcs):
        stream_cache = _load_streams(conn, activity_id)

    ctx = CalcContext(
        conn=conn,
        scope_type="activity",
        scope_id=str(activity_id),
        _activity_cache=activity_cache,
        _metric_cache=metric_cache,
        _stream_cache=stream_cache,
    )

    for calc in sorted_calcs:
        try:
            calc_results = calc.compute(ctx)
            saved = _save_results(conn, calc, calc_results, str(activity_id))
            if saved > 0:
                for r in calc_results:
                    if not r.is_empty():
                        results[r.metric_name] = r.numeric_value or r.text_value
                        # 후속 calculator용 캐시 업데이트
                        ctx.update_metric_cache(
                            r.metric_name, calc.provider,
                            numeric=r.numeric_value,
                            text=r.text_value,
                            json_val=r.json_value,
                        )
        except Exception as e:
            log.exception("Calculator %s 실패: activity_id=%d", calc.name, activity_id)
            failed.append({"calculator": calc.name, "error": str(e)})

    if failed:
        results["_failed"] = failed
    # Phase 3 sync와 동일: scope별 is_primary 재결정
    resolve_for_scope(conn, "activity", str(activity_id))
    return results


# ═══════════════════════════════════════════
# Daily-Scope 실행 (prefetch 적용)
# ═══════════════════════════════════════════

def run_daily_metrics(conn: sqlite3.Connection, target_date: str,
                      prefetched_daily_loads: dict = None,
                      prefetched_wellness_map: dict = None,
                      prefetched_daily_metrics: dict = None) -> dict:
    """특정 날짜의 모든 daily-scope calculator 실행 (prefetch 지원)."""
    sorted_calcs = _topological_sort(
        [c for c in ALL_CALCULATORS if c.scope_type == "daily"]
    )
    results: dict = {}
    failed: list[dict] = []

    # per-scope metric cache
    metric_cache = None
    if prefetched_daily_metrics is not None:
        metric_cache = prefetched_daily_metrics.get(target_date, {})

    ctx = CalcContext(
        conn=conn,
        scope_type="daily",
        scope_id=target_date,
        _metric_cache=metric_cache,
        _prefetched_daily_loads=prefetched_daily_loads,
        _prefetched_wellness_map=prefetched_wellness_map,
        _prefetched_daily_metrics=prefetched_daily_metrics,
    )

    for calc in sorted_calcs:
        try:
            calc_results = calc.compute(ctx)
            saved = _save_results(conn, calc, calc_results, target_date)
            if saved > 0:
                for r in calc_results:
                    if not r.is_empty():
                        results[r.metric_name] = r.numeric_value or r.text_value
                        ctx.update_metric_cache(
                            r.metric_name, calc.provider,
                            numeric=r.numeric_value,
                            text=r.text_value,
                            json_val=r.json_value,
                        )
        except Exception as e:
            log.exception("Calculator %s 실패: %s", calc.name, target_date)
            failed.append({"calculator": calc.name, "error": str(e)})

    if failed:
        results["_failed"] = failed
    # Phase 3 sync와 동일: scope별 is_primary 재결정
    resolve_for_scope(conn, "daily", target_date)
    return results


# ═══════════════════════════════════════════
# Composite: run_for_date (prefetch 적용)
# ═══════════════════════════════════════════

def run_for_date(conn: sqlite3.Connection, target_date: str,
                 prefetched_daily_loads: dict = None,
                 prefetched_wellness_map: dict = None,
                 prefetched_daily_metrics: dict = None) -> dict:
    """특정 날짜의 전체 메트릭 계산 (활동별 → 일별)."""
    activities = conn.execute(
        "SELECT id FROM activity_summaries "
        "WHERE substr(start_time, 1, 10) = ? AND activity_type IN "
        "('running','trail_running','treadmill')",
        (target_date,),
    ).fetchall()

    activity_results = {}
    for (act_id,) in activities:
        activity_results[act_id] = run_activity_metrics(conn, act_id)

    daily_results = run_daily_metrics(
        conn, target_date,
        prefetched_daily_loads=prefetched_daily_loads,
        prefetched_wellness_map=prefetched_wellness_map,
        prefetched_daily_metrics=prefetched_daily_metrics,
    )

    return {
        "activity_metrics": activity_results,
        "daily": daily_results,
    }


# ═══════════════════════════════════════════
# Recompute (batch prefetch 적용)
# ═══════════════════════════════════════════


# ═══════════════════════════════════════════
# Dirty Tracking — 선택적 실행 (보강 #4)
# ═══════════════════════════════════════════

def compute_for_activities(conn: sqlite3.Connection,
                           activity_ids: list[int]) -> ComputeResult:
    """특정 활동들에 대해서만 activity-scope calculator 실행."""
    result = ComputeResult()
    start = _time.monotonic()
    sorted_calcs = _topological_sort(
        [c for c in ALL_CALCULATORS if c.scope_type == "activity"]
    )

    for activity_id in activity_ids:
        result.total_scopes += 1
        metrics = run_activity_metrics(conn, activity_id)
        for k, v in metrics.items():
            if k == "_failed":
                for f in v:
                    result.error_count += 1
                    result.errors.append((f["calculator"], str(activity_id), f["error"]))
            else:
                result.computed_count += 1
        result.total_calculators += len(sorted_calcs)

    conn.commit()
    result.elapsed_seconds = _time.monotonic() - start
    return result


def compute_for_dates(conn: sqlite3.Connection,
                      dates: list[str]) -> ComputeResult:
    """특정 날짜들에 대해서만 daily-scope calculator 실행."""
    result = ComputeResult()
    start = _time.monotonic()
    sorted_calcs = _topological_sort(
        [c for c in ALL_CALCULATORS if c.scope_type == "daily"]
    )

    # batch prefetch
    if dates:
        from datetime import timedelta as _td
        from datetime import date as _date
        earliest = min(dates)
        latest = max(dates)
        # CTL은 42일 이전 데이터 필요
        prefetch_start = (_date.fromisoformat(earliest) - _td(days=49)).isoformat()
        daily_loads = _prefetch_daily_trimp_sums(conn, prefetch_start, latest)
        wellness_map = _prefetch_all_wellness(conn, prefetch_start, latest)
        daily_metrics = _prefetch_daily_metrics(conn, prefetch_start, latest)
    else:
        daily_loads = wellness_map = daily_metrics = None

    for d in sorted(dates):
        result.total_scopes += 1
        metrics = run_daily_metrics(
            conn, d,
            prefetched_daily_loads=daily_loads,
            prefetched_wellness_map=wellness_map,
            prefetched_daily_metrics=daily_metrics,
        )
        for k, v in metrics.items():
            if k == "_failed":
                for f in v:
                    result.error_count += 1
                    result.errors.append((f["calculator"], d, f["error"]))
            else:
                result.computed_count += 1
        result.total_calculators += len(sorted_calcs)

    conn.commit()
    resolve_all_primaries(conn)
    result.elapsed_seconds = _time.monotonic() - start
    return result


def recompute_single_metric(conn: sqlite3.Connection,
                            metric_name: str, days: int = 30) -> ComputeResult:
    """특정 메트릭만 재계산 (보강 #10 일부)."""
    result = ComputeResult()
    start = _time.monotonic()

    calc = None
    for c in ALL_CALCULATORS:
        if metric_name in c.produces:
            calc = c
            break
    if not calc:
        raise ValueError(f"No calculator found for '{metric_name}'")

    # 기존 값 삭제
    for name in calc.produces:
        conn.execute(
            "DELETE FROM metric_store WHERE metric_name = ? AND provider = ?",
            [name, calc.provider],
        )
    conn.commit()

    today = date.today()
    if calc.scope_type == "activity":
        start_date = (today - timedelta(days=days)).isoformat()
        activities = conn.execute(
            "SELECT id FROM activity_summaries "
            "WHERE substr(start_time,1,10) >= ? AND activity_type IN "
            "('running','trail_running','treadmill')",
            (start_date,),
        ).fetchall()
        for (aid,) in activities:
            result.total_scopes += 1
            ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(aid))
            try:
                outcomes = calc.compute(ctx)
                saved = _save_results(conn, calc, outcomes, str(aid))
                if saved > 0:
                    result.computed_count += 1
                else:
                    result.skipped_count += 1
            except Exception as e:
                result.error_count += 1
                result.errors.append((calc.name, str(aid), str(e)))

    elif calc.scope_type == "daily":
        for i in range(days):
            d = (today - timedelta(days=days - 1 - i)).isoformat()
            result.total_scopes += 1
            ctx = CalcContext(conn=conn, scope_type="daily", scope_id=d)
            try:
                outcomes = calc.compute(ctx)
                saved = _save_results(conn, calc, outcomes, d)
                if saved > 0:
                    result.computed_count += 1
                else:
                    result.skipped_count += 1
            except Exception as e:
                result.error_count += 1
                result.errors.append((calc.name, d, str(e)))

    conn.commit()
    resolve_all_primaries(conn)
    result.elapsed_seconds = _time.monotonic() - start
    return result
def recompute_recent(conn: sqlite3.Connection, days: int = 7) -> dict:
    """최근 N일 메트릭 재계산 (batch prefetch 포함)."""
    today = date.today()
    start_date = (today - timedelta(days=days + 49)).isoformat()  # CTL 42일 + 여유
    end_date = today.isoformat()

    # batch prefetch
    daily_loads = _prefetch_daily_trimp_sums(conn, start_date, end_date)
    wellness_map = _prefetch_all_wellness(conn, start_date, end_date)
    daily_metrics = _prefetch_daily_metrics(conn, start_date, end_date)

    all_results = {}
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        all_results[d] = run_for_date(
            conn, d,
            prefetched_daily_loads=daily_loads,
            prefetched_wellness_map=wellness_map,
            prefetched_daily_metrics=daily_metrics,
        )

    resolve_all_primaries(conn)
    return all_results


def clear_runpulse_metrics(conn: sqlite3.Connection) -> int:
    """RunPulse 계산 메트릭만 삭제 (소스 메트릭 보존)."""
    cur = conn.execute(
        "DELETE FROM metric_store WHERE provider LIKE 'runpulse%'"
    )
    deleted = cur.rowcount
    conn.commit()
    log.info("clear_runpulse_metrics: %d행 삭제", deleted)
    return deleted


def recompute_all(conn: sqlite3.Connection, days: int = 90) -> dict:
    """전체 재계산: RunPulse 메트릭 삭제 → batch prefetch → 재실행."""
    clear_runpulse_metrics(conn)
    today = date.today()
    start_date = (today - timedelta(days=days + 49)).isoformat()
    end_date = today.isoformat()

    # batch prefetch
    daily_loads = _prefetch_daily_trimp_sums(conn, start_date, end_date)
    wellness_map = _prefetch_all_wellness(conn, start_date, end_date)
    daily_metrics = _prefetch_daily_metrics(conn, start_date, end_date)

    all_results = {}
    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        all_results[d] = run_for_date(
            conn, d,
            prefetched_daily_loads=daily_loads,
            prefetched_wellness_map=wellness_map,
            prefetched_daily_metrics=daily_metrics,
        )

    resolve_all_primaries(conn)
    return all_results
