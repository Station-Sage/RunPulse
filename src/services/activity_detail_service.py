"""Phase 5 서비스 레이어 - 활동 상세 조회.

읽기 전용. DB 쓰기 없음. 첫 번째 인자는 sqlite3.Connection.
activity_service.py에서 300줄 규칙 위반으로 분리(get_activity_detail + 그 전용 헬퍼만).
"""
from __future__ import annotations

import sqlite3
from collections import defaultdict

from src.services.activity_impact_service import get_activity_impact
from src.services.activity_splits import build_series, compute_splits
from src.services import activity_summary_extras as extras
from src.utils import db_helpers
from src.utils.metric_groups import SEMANTIC_GROUPS
from src.utils.metric_registry import get_metric
from src.metrics.bands import with_grade
from src.metrics.display_rules import visible_activity_metrics
from src.services import activity_feedback_service, activity_gpx, activity_source_links
from src.utils.canonical import canonical_activity_id, group_activity_ids

_SUMMARY_STREAM_POINTS = 500


def _downsample_streams(rows: list[dict]) -> list[dict]:
    """요약 탭 차트(RouteMap·고도·페이스/HR)용 균등 다운샘플 — 최대 500포인트.

    activity_service._route_previews와 같은 균등 인덱스 선택 방식이지만 lat/lng만이 아니라 행 전체
    (고도·속도·심박 등)를 그대로 유지한다 — 이 필드들이 요약 화면 여러 차트에서 elapsed_sec 기준으로
    같이 쓰이기 때문에 서로 다른 다운샘플링을 적용하면 차트끼리 시간축이 어긋난다. 전체 해상도가
    필요하면 스트림 탭(get_activity_streams)에서 받는다.
    """
    n = _SUMMARY_STREAM_POINTS
    if len(rows) <= n:
        return rows
    return [rows[round(i * (len(rows) - 1) / (n - 1))] for i in range(n)]


def get_activity_detail(conn: sqlite3.Connection, activity_id: int, include_streams: bool = False) -> dict:
    """활동 상세: core + metrics_by_category + source_comparison + semantic_groups
    + streams(include_streams=True 일 때만 최대 500포인트 다운샘플, 기본 None — 전체는 get_activity_streams) + laps + best_efforts.
    """
    conn.row_factory = sqlite3.Row

    # core
    core_row = conn.execute(
        "SELECT * FROM activity_summaries WHERE id = ?", (activity_id,)
    ).fetchone()
    core = dict(core_row) if core_row else {}

    # metrics_by_category (is_primary=1)
    # RunPulse 계산값은 캐노니컬 사본에만 있다(그룹당 1회, 21 design §7.3 C3) — 사본을 열어도 같은 값을 보인다
    canonical_id = canonical_activity_id(conn, activity_id)
    primary_metrics = db_helpers.get_primary_metrics(conn, "activity", activity_id)
    if canonical_id != activity_id:
        own = {r["metric_name"] for r in primary_metrics}
        primary_metrics += [r for r in db_helpers.get_primary_metrics(conn, "activity", canonical_id)
                            if (r.get("provider") or "").startswith("runpulse") and r["metric_name"] not in own]
    primary_metrics = visible_activity_metrics(primary_metrics)
    metrics_by_category = _build_metrics_by_category(primary_metrics)

    # source_comparison (같은 matched_group의 다른 소스)
    source_comparison: dict = {}
    group_id = core.get("matched_group_id")
    if group_id:
        siblings = conn.execute(
            "SELECT * FROM activity_summaries WHERE matched_group_id = ?",
            (group_id,),
        ).fetchall()
        for row in siblings:
            row_dict = dict(row)
            source = row_dict.get("source", "unknown")
            source_comparison[source] = row_dict

    # semantic_groups (모든 provider)
    all_metrics_rows = conn.execute(
        "SELECT metric_name, provider, numeric_value, text_value, json_value, confidence"
        " FROM metric_store"
        " WHERE scope_type = 'activity' AND (scope_id = CAST(? AS TEXT)"
        "   OR (scope_id = CAST(? AS TEXT) AND provider LIKE 'runpulse%' AND ? != ?))"
        " ORDER BY metric_name, provider",
        (activity_id, canonical_id, canonical_id, activity_id),
    ).fetchall()
    all_metrics = visible_activity_metrics([dict(r) for r in all_metrics_rows])
    semantic_groups = _build_semantic_groups(all_metrics, core)

    # streams — 요약 탭 차트(RouteMap·고도·페이스/HR)용으로 다운샘플만 내려준다.
    # 전체 해상도는 /library/activities/<id>/streams(get_activity_streams)에서 별도 제공(02-performance.md P-4).
    stream_rows = conn.execute(
        "SELECT * FROM activity_streams WHERE activity_id = ? ORDER BY elapsed_sec",
        (activity_id,),
    ).fetchall()
    full_streams = [dict(r) for r in stream_rows]
    stream_point_count = len(full_streams)
    streams = (_downsample_streams(full_streams) or None) if include_streams else None
    total_sec = core.get("elapsed_time_sec") or core.get("duration_sec") or 0
    total_dist = core.get("distance_m") or 0
    splits = compute_splits(full_streams, total_sec, total_dist)
    series = build_series(full_streams, total_sec, total_dist)
    siblings = [{"id": r["id"], "provider": r["source"], "is_canonical": r["id"] == canonical_id}
                for r in (source_comparison.values() if source_comparison else [])]

    ids = sorted({activity_id, canonical_id})
    group_ids = group_activity_ids(conn, activity_id)
    wc = extras.build_workout_class(conn, ids, core, splits)
    environment = extras.build_environment(conn, ids, core)
    hr_zones = extras.build_hr_zones(conn, ids)
    source_diffs = extras.build_source_diffs(source_comparison)
    verdict = extras.build_verdict(core, wc, splits, environment)

    # laps
    lap_rows = conn.execute(
        "SELECT * FROM activity_laps WHERE activity_id = ? ORDER BY lap_index",
        (activity_id,),
    ).fetchall()
    laps = [dict(r) for r in lap_rows] or None

    # best_efforts
    effort_rows = conn.execute(
        "SELECT * FROM activity_best_efforts WHERE activity_id = ? ORDER BY distance_m",
        (activity_id,),
    ).fetchall()
    best_efforts = [dict(r) for r in effort_rows] or None

    try:
        impact = get_activity_impact(conn, activity_id)
    except Exception:
        impact = None

    has_gps = conn.execute(
        f"SELECT COUNT(*) FROM activity_streams WHERE latitude IS NOT NULL AND activity_id IN "
        f"({','.join('?' * len(group_ids))}) GROUP BY activity_id ORDER BY 1 DESC LIMIT 1",
        group_ids).fetchone()
    return {
        "feedback": activity_feedback_service.get_feedback(conn, activity_id),
        "menu": {"has_gps": bool(has_gps and has_gps[0] >= activity_gpx.MIN_POINTS),
                 "source_links": activity_source_links.source_links(conn, activity_id)},
        "core": core,
        "metrics_by_category": metrics_by_category,
        "source_comparison": source_comparison,
        "semantic_groups": semantic_groups,
        "streams": streams,
        "splits": splits,
        "series": series,
        "siblings": siblings,
        "workout_class": wc["workout_class"],
        "workout_class_label": wc["label"],
        "workout_class_basis": wc["workout_class_basis"],
        "environment": environment,
        "hr_zones": hr_zones,
        "source_diffs": source_diffs,
        "verdict": verdict,
        "stream_point_count": stream_point_count,
        "laps": laps,
        "best_efforts": best_efforts,
        "impact": impact,
    }


def _build_metrics_by_category(primary_metrics: list[dict]) -> dict[str, list[dict]]:
    """primary 메트릭을 category별로 그룹핑하고 registry에서 unit/description 추가."""
    grouped: dict[str, list] = defaultdict(list)
    for row in primary_metrics:
        metric_name = row["metric_name"]
        category = row.get("category") or "_unmapped"
        meta = get_metric(metric_name)
        entry = {
            "metric_name": metric_name,
            "numeric_value": row.get("numeric_value"),
            "text_value": row.get("text_value"),
            "json_value": row.get("json_value"),
            "provider": row.get("provider"),
            "confidence": row.get("confidence"),
            "unit": meta.unit if meta else "",
            "description": meta.description if meta else "",
        }
        with_grade(entry, metric_name, row.get("numeric_value"))
        grouped[category].append(entry)
    return dict(grouped)


def _build_semantic_groups(
    all_metrics: list[dict], core: dict
) -> dict[str, dict]:
    """SEMANTIC_GROUPS 기반으로 소스 비교 뷰 구성.

    metric_store에 없는 멤버는 activity_summaries 컬럼에서 fallback.
    """
    # index: (metric_name, provider) -> row
    idx: dict[tuple[str, str], dict] = {
        (r["metric_name"], r["provider"]): r for r in all_metrics
    }

    result: dict[str, dict] = {}
    for group_name, group_def in SEMANTIC_GROUPS.items():
        members: list[dict] = []
        for metric_name, provider in group_def["members"]:
            row = idx.get((metric_name, provider))
            if row:
                value = row.get("numeric_value") if row.get("numeric_value") is not None \
                    else row.get("text_value")
                members.append({
                    "metric_name": metric_name,
                    "provider": provider,
                    "value": value,
                })
            elif metric_name in core and core[metric_name] is not None:
                # activity_summaries 컬럼에서 fallback
                members.append({
                    "metric_name": metric_name,
                    "provider": provider,
                    "value": core[metric_name],
                    "source_table": "activity_summaries",
                })
        if members:
            result[group_name] = {
                "display_name": group_def["display_name"],
                "strategy": group_def.get("primary_strategy", "show_all"),
                "members": members,
            }
    return result
