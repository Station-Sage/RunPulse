"""Metrics Engine — 날짜 범위 일괄 메트릭 계산 오케스트레이터.

계산 의존 순서:
  1. 활동별 (per-activity): TRIMP → EF/Decoupling → FEARP → RelativeEffort → WLEI
  2. 일별 (daily): DailyTRIMP → ACWR → Monotony → UTRS → CIRS → LSI → DI → DARP → RMR → RTTI → TPDI
  3. 주별 (weekly, 해당 날짜가 일요일이거나 강제 실행 시): MarathonShape → ADTI
"""
from __future__ import annotations

import logging
import sqlite3
from collections.abc import Callable
from datetime import date, timedelta

from src.metrics.acwr import calc_and_save_acwr
from src.metrics.adti import calc_and_save_adti
from src.metrics.cirs import calc_and_save_cirs
from src.metrics.darp import calc_and_save_darp
from src.metrics.decoupling import calc_and_save_decoupling
from src.metrics.di import calc_and_save_di
from src.metrics.fearp import calc_and_save_fearp
from src.metrics.lsi import calc_and_save_lsi
from src.metrics.marathon_shape import calc_and_save_marathon_shape
from src.metrics.monotony import calc_and_save_monotony
from src.metrics.relative_effort import calc_and_save_relative_effort
from src.metrics.rmr import calc_and_save_rmr
from src.metrics.tids import calc_and_save_tids
from src.metrics.rtti import calc_and_save_rtti
from src.metrics.tpdi import calc_and_save_tpdi
from src.metrics.trimp import calc_and_save_daily_trimp, calc_and_save_trimp_for_activity
from src.metrics.utrs import calc_and_save_utrs
from src.metrics.vdot import calc_and_save_vdot
from src.metrics.wlei import calc_and_save_wlei
logger = logging.getLogger(__name__)


def run_activity_metrics(conn: sqlite3.Connection, activity_id: int) -> dict:
    """단일 활동에 대한 메트릭 계산.

    Args:
        conn: SQLite 커넥션.
        activity_id: activity_summaries.id.

    Returns:
        계산된 메트릭 이름 → 값 딕셔너리.
    """
    results: dict = {}

    try:
        trimp = calc_and_save_trimp_for_activity(conn, activity_id)
        if trimp is not None:
            results["TRIMP"] = trimp
    except Exception:
        logger.exception("TRIMP 계산 실패: activity_id=%d", activity_id)

    try:
        decoupling = calc_and_save_decoupling(conn, activity_id)
        if decoupling is not None:
            results["AerobicDecoupling"] = decoupling
    except Exception:
        logger.exception("Decoupling 계산 실패: activity_id=%d", activity_id)

    try:
        fearp = calc_and_save_fearp(conn, activity_id)
        if fearp is not None:
            results["FEARP"] = fearp
    except Exception:
        logger.exception("FEARP 계산 실패: activity_id=%d", activity_id)

    try:
        re = calc_and_save_relative_effort(conn, activity_id)
        if re is not None:
            results["RelativeEffort"] = re
    except Exception:
        logger.exception("RelativeEffort 계산 실패: activity_id=%d", activity_id)

    # WLEI는 TRIMP 계산 후에 실행 (날씨 × TRIMP)
    try:
        wlei = calc_and_save_wlei(conn, activity_id)
        if wlei is not None:
            results["WLEI"] = wlei
    except Exception:
        logger.exception("WLEI 계산 실패: activity_id=%d", activity_id)

    return results


def run_daily_metrics(conn: sqlite3.Connection, target_date: str) -> dict:
    """하루치 일별 메트릭 계산 (의존 순서 준수).

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.

    Returns:
        계산된 메트릭 이름 → 값 딕셔너리.
    """
    results: dict = {}

    # 1. TRIMP 일별 합산 (활동별 TRIMP가 이미 저장된 상태여야 함)
    try:
        daily_trimp = calc_and_save_daily_trimp(conn, target_date)
        results["TRIMP_daily"] = daily_trimp
    except Exception:
        logger.exception("DailyTRIMP 계산 실패: %s", target_date)

    # 2. ACWR (TRIMP 28일 필요)
    try:
        acwr = calc_and_save_acwr(conn, target_date)
        if acwr is not None:
            results["ACWR"] = acwr
    except Exception:
        logger.exception("ACWR 계산 실패: %s", target_date)

    # 3. Monotony & Strain (TRIMP 7일 필요)
    try:
        mono_result = calc_and_save_monotony(conn, target_date)
        if mono_result:
            results["Monotony"] = mono_result.get("monotony")
            results["Strain"] = mono_result.get("strain")
    except Exception:
        logger.exception("Monotony 계산 실패: %s", target_date)

    # 4. UTRS (wellness 데이터, TSB 필요)
    try:
        utrs_result = calc_and_save_utrs(conn, target_date)
        if utrs_result is not None:
            results["UTRS"] = utrs_result
    except Exception:
        logger.exception("UTRS 계산 실패: %s", target_date)

    # 5. CIRS (ACWR + Monotony 필요)
    try:
        cirs = calc_and_save_cirs(conn, target_date)
        if cirs is not None:
            results["CIRS"] = cirs
    except Exception:
        logger.exception("CIRS 계산 실패: %s", target_date)

    # 6. LSI (TRIMP 시계열 필요)
    try:
        lsi = calc_and_save_lsi(conn, target_date)
        if lsi is not None:
            results["LSI"] = lsi
    except Exception:
        logger.exception("LSI 계산 실패: %s", target_date)

    # 7. DI (90분+ 세션 8주치 필요)
    try:
        di = calc_and_save_di(conn, target_date)
        if di is not None:
            results["DI"] = di
    except Exception:
        logger.exception("DI 계산 실패: %s", target_date)

    # 7.5. VDOT (best_efforts / 고강도 활동 기반)
    try:
        vdot = calc_and_save_vdot(conn, target_date)
        if vdot is not None:
            results["VDOT"] = vdot
    except Exception:
        logger.exception("VDOT 계산 실패: %s", target_date)

    # 8. TIDS (훈련 강도 분포)
    try:
        tids = calc_and_save_tids(conn, target_date)
        if tids is not None:
            results["TIDS"] = tids
    except Exception:
        logger.exception("TIDS 계산 실패: %s", target_date)

    # 9. DARP (VDOT + DI 필요)
    try:
        darp_result = calc_and_save_darp(conn, target_date)
        if darp_result is not None:
            results["DARP"] = darp_result
    except Exception:
        logger.exception("DARP 계산 실패: %s", target_date)

    # 10. RMR (복합 웰니스/피트니스 데이터 필요)
    try:
        rmr_result = calc_and_save_rmr(conn, target_date)
        if rmr_result is not None:
            results["RMR"] = rmr_result.get("overall")
    except Exception:
        logger.exception("RMR 계산 실패: %s", target_date)

    # 11. RTTI (Garmin running_tolerance 기반)
    try:
        rtti = calc_and_save_rtti(conn, target_date)
        if rtti is not None:
            results["RTTI"] = rtti
    except Exception:
        logger.exception("RTTI 계산 실패: %s", target_date)

    # 12. TPDI (실내/실외 FEARP 격차, FEARP 계산 후)
    try:
        tpdi = calc_and_save_tpdi(conn, target_date)
        if tpdi is not None:
            results["TPDI"] = tpdi
    except Exception:
        logger.exception("TPDI 계산 실패: %s", target_date)

    return results


def run_weekly_metrics(conn: sqlite3.Connection, target_date: str) -> dict:
    """주간 메트릭 계산 (주별 집계 지표).

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD (기준일).

    Returns:
        계산된 메트릭 이름 → 값 딕셔너리.
    """
    results: dict = {}

    try:
        shape = calc_and_save_marathon_shape(conn, target_date)
        if shape is not None:
            results["MarathonShape"] = shape
    except Exception:
        logger.exception("MarathonShape 계산 실패: %s", target_date)

    try:
        adti = calc_and_save_adti(conn, target_date)
        if adti is not None:
            results["ADTI"] = adti
    except Exception:
        logger.exception("ADTI 계산 실패: %s", target_date)

    return results


def run_for_date(
    conn: sqlite3.Connection,
    target_date: str,
    include_weekly: bool = False,
) -> dict:
    """특정 날짜의 전체 메트릭 계산.

    활동별 메트릭 → 일별 메트릭 → 주별 메트릭(옵션) 순서로 실행.

    Args:
        conn: SQLite 커넥션.
        target_date: YYYY-MM-DD.
        include_weekly: 주별 메트릭도 함께 계산할지 여부.

    Returns:
        {'activity_metrics': {act_id: {...}}, 'daily': {...}, 'weekly': {...}}
    """
    # 해당 날짜 활동 조회
    activities = conn.execute(
        """SELECT id FROM v_canonical_activities
           WHERE DATE(start_time) = ? AND activity_type='running'""",
        (target_date,),
    ).fetchall()

    activity_results: dict = {}
    for (act_id,) in activities:
        activity_results[act_id] = run_activity_metrics(conn, act_id)

    daily_results = run_daily_metrics(conn, target_date)

    weekly_results: dict = {}
    if include_weekly:
        weekly_results = run_weekly_metrics(conn, target_date)

    logger.info(
        "메트릭 계산 완료 [%s] 활동=%d, 일별=%d개, 주별=%d개",
        target_date,
        len(activity_results),
        len(daily_results),
        len(weekly_results),
    )

    return {
        "activity_metrics": activity_results,
        "daily": daily_results,
        "weekly": weekly_results,
    }


def run_for_date_range(
    conn: sqlite3.Connection,
    start_date: str,
    end_date: str,
    weekly_on_sunday: bool = True,
    on_progress: "Callable[[str, int, int], None] | None" = None,
) -> dict[str, dict]:
    """날짜 범위 일괄 메트릭 계산.

    Args:
        conn: SQLite 커넥션.
        start_date: 시작일 YYYY-MM-DD.
        end_date: 종료일 YYYY-MM-DD.
        weekly_on_sunday: True면 일요일마다 주별 메트릭 추가 계산.
        on_progress: 날짜 완료 시 콜백 (date_str, completed, total).

    Returns:
        {date_str: run_for_date 결과} 딕셔너리.
    """
    results: dict = {}
    td = date.fromisoformat(start_date)
    end = date.fromisoformat(end_date)
    total = (end - td).days + 1
    completed = 0

    while td <= end:
        date_str = td.isoformat()
        is_sunday = td.weekday() == 6
        include_weekly = weekly_on_sunday and is_sunday

        results[date_str] = run_for_date(conn, date_str, include_weekly=include_weekly)
        completed += 1
        if on_progress is not None:
            try:
                on_progress(date_str, completed, total)
            except Exception:
                pass
        td += timedelta(days=1)

    return results


def recompute_all(
    conn: sqlite3.Connection,
    days: int = 90,
    target_date: str | None = None,
    on_progress: "Callable[[str, int, int], None] | None" = None,
) -> dict:
    """최근 N일 모든 메트릭 재계산.

    기존 computed_metrics는 덮어씀 (UPSERT).

    Args:
        conn: SQLite 커넥션.
        days: 계산할 일 수 (기본 90일).
        target_date: 기준일 (없으면 오늘).
        on_progress: 날짜 완료 시 콜백 (date_str, completed, total).

    Returns:
        run_for_date_range 결과.
    """
    end = date.fromisoformat(target_date) if target_date else date.today()
    start = end - timedelta(days=days - 1)
    logger.info("메트릭 전체 재계산 시작: %s ~ %s", start.isoformat(), end.isoformat())
    return run_for_date_range(
        conn, start.isoformat(), end.isoformat(),
        weekly_on_sunday=True, on_progress=on_progress,
    )
