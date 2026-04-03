"""Metrics Engine — topological sort 기반 실행. 설계서 4-5 기준.

ALL_CALCULATORS 등록 → 의존성 그래프 해소 → scope별 순차 실행 → metric_store 저장.
"""
from __future__ import annotations

import logging
import sqlite3
from collections import defaultdict
from datetime import date, timedelta

from src.metrics.base import CalcContext, CalcResult, MetricCalculator
from src.utils.db_helpers import upsert_metric
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

log = logging.getLogger(__name__)

# ── Calculator 레지스트리 ──
ALL_CALCULATORS: list[MetricCalculator] = [
    # Activity-scope
    TRIMPCalculator(),
    HRSSCalculator(),
    AerobicDecouplingCalculator(),
    GAPCalculator(),
    WorkoutClassifier(),
    VDOTCalculator(),
    EfficiencyFactorCalculator(),
    FEARPCalculator(),
    # Daily-scope 1차
    PMCCalculator(),
    ACWRCalculator(),
    LSICalculator(),
    MonotonyStrainCalculator(),
    # Daily-scope 2차
    UTRSCalculator(),
    CIRSCalculator(),
    DICalculator(),
    DARPCalculator(),
    TIDSCalculator(),
    RMRCalculator(),
    ADTICalculator(),
]


def _topological_sort(calculators: list[MetricCalculator]) -> list[MetricCalculator]:
    """의존성 그래프 기반 위상 정렬."""
    # produces → calculator 매핑
    producer_map: dict[str, MetricCalculator] = {}
    for calc in calculators:
        for p in calc.produces:
            producer_map[p] = calc

    # 인접 리스트 (calc → 의존하는 calc 목록)
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

    # Kahn's algorithm
    queue = [k for k, v in in_degree.items() if v == 0]
    sorted_names: list[str] = []

    while queue:
        node = queue.pop(0)
        sorted_names.append(node)
        for neighbor in graph.get(node, []):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    # 이름 → calculator 매핑
    name_to_calc = {c.name: c for c in calculators}
    result = []
    for name in sorted_names:
        if name in name_to_calc:
            result.append(name_to_calc[name])

    # 그래프에 포함되지 않은 calculator 추가 (requires=[] 이고 produces가 다른 calc에 안 쓰이는 경우)
    included = {c.name for c in result}
    for calc in calculators:
        if calc.name not in included:
            result.append(calc)

    return result


def _save_results(conn: sqlite3.Connection, calc: MetricCalculator,
                  results: list[CalcResult], scope_id: str) -> int:
    """CalcResult 리스트를 metric_store에 저장."""
    saved = 0
    for r in results:
        if r.is_empty():
            continue
        r.scope_id = scope_id  # engine이 채워줌
        upsert_metric(
            conn,
            scope_type=r.scope_type,
            scope_id=r.scope_id,
            metric_name=r.metric_name,
            provider=calc.provider,
            numeric_value=r.numeric_value,
            text_value=r.text_value,
            json_value=r.json_value if isinstance(r.json_value, dict) else None,
            category=r.category,
            algorithm_version=calc.version,
            confidence=r.confidence,
        )
        saved += 1
    return saved


def run_activity_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """단일 활동에 대한 모든 activity-scope calculator 실행."""
    sorted_calcs = _topological_sort(
        [c for c in ALL_CALCULATORS if c.scope_type == "activity"]
    )
    results: dict = {}
    ctx = CalcContext(conn=conn, scope_type="activity", scope_id=str(activity_id))

    for calc in sorted_calcs:
        try:
            calc_results = calc.compute(ctx)
            saved = _save_results(conn, calc, calc_results, str(activity_id))
            if saved > 0:
                for r in calc_results:
                    if not r.is_empty():
                        results[r.metric_name] = r.numeric_value or r.text_value
        except Exception:
            log.exception("Calculator %s 실패: activity_id=%d", calc.name, activity_id)

    return results


def run_daily_metrics(conn: sqlite3.Connection, target_date: str) -> dict:
    """특정 날짜의 모든 daily-scope calculator 실행."""
    sorted_calcs = _topological_sort(
        [c for c in ALL_CALCULATORS if c.scope_type == "daily"]
    )
    results: dict = {}
    ctx = CalcContext(conn=conn, scope_type="daily", scope_id=target_date)

    for calc in sorted_calcs:
        try:
            calc_results = calc.compute(ctx)
            saved = _save_results(conn, calc, calc_results, target_date)
            if saved > 0:
                for r in calc_results:
                    if not r.is_empty():
                        results[r.metric_name] = r.numeric_value or r.text_value
        except Exception:
            log.exception("Calculator %s 실패: %s", calc.name, target_date)

    return results


def run_for_date(conn: sqlite3.Connection, target_date: str) -> dict:
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

    daily_results = run_daily_metrics(conn, target_date)

    return {
        "activity_metrics": activity_results,
        "daily": daily_results,
    }


def recompute_recent(conn: sqlite3.Connection, days: int = 7) -> dict:
    """최근 N일 메트릭 재계산."""
    today = date.today()
    all_results = {}

    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        all_results[d] = run_for_date(conn, d)

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
    """전체 재계산: RunPulse 메트릭 삭제 → 재실행."""
    clear_runpulse_metrics(conn)
    today = date.today()
    all_results = {}

    for i in range(days):
        d = (today - timedelta(days=days - 1 - i)).isoformat()
        all_results[d] = run_for_date(conn, d)

    resolve_all_primaries(conn)
    return all_results
