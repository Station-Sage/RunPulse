"""AI 채팅 의도별 컨텍스트 빌더 회귀 테스트 — 스키마 드리프트 방지.

v12에서 activity_summaries.calories 컬럼이 metric_store로 옮겨졌는데 today/lookup 빌더가 계속
그 컬럼을 SELECT해 `no such column: calories`로 실패하고, build_chat_context의 try/except가 삼켜서
"오늘 훈련 조언"·특정 날짜 조회 컨텍스트에 활동 상세가 통째로 빠져 있었다(2026-09-24 합성 데이터
검증으로 발견). 모든 빌더가 현재 스키마에서 예외 없이 도는지 확인한다.
"""
from __future__ import annotations

from datetime import date

import pytest

from src.ai.chat_context_builders import (
    INTENT_BUILDERS, _add_lookup_context, _add_today_context, _build_base_context,
)


def _seed_run(conn, *, act_id, day, name="Easy Run"):
    conn.execute(
        "INSERT INTO activity_summaries (id, source, source_id, name, activity_type, start_time,"
        " distance_m, duration_sec, avg_hr, avg_pace_sec_km, elevation_gain)"
        " VALUES (?, 'garmin', ?, ?, 'running', ?, 10000, 3000, 140, 300, 50)",
        (act_id, str(act_id), name, f"{day}T06:00:00"),
    )
    conn.execute(
        "INSERT INTO metric_store (scope_type, scope_id, metric_name, provider, numeric_value, is_primary)"
        " VALUES ('activity', ?, 'calories', 'garmin', 512, 1)",
        (str(act_id),),
    )
    conn.commit()


@pytest.mark.parametrize("intent", sorted(INTENT_BUILDERS))
def test_every_intent_builder_runs_on_current_schema(db_conn, intent):
    """빈 DB에서도 모든 의도 빌더가 예외 없이 끝난다(스키마 드리프트 가드)."""
    today = date.today().isoformat()
    ctx = _build_base_context(db_conn, today)
    INTENT_BUILDERS[intent](db_conn, ctx, today)


def test_today_context_reads_todays_activity(db_conn):
    today = date.today().isoformat()
    _seed_run(db_conn, act_id=1, day=today)
    ctx = _build_base_context(db_conn, today)
    _add_today_context(db_conn, ctx, today)
    detail = ctx["today_detail"]
    assert detail["distance_km"] == 10.0
    assert detail["avg_hr"] == 140
    assert detail["calories"] == 512  # metric_store에서


def test_today_context_without_activity_is_none(db_conn):
    today = date.today().isoformat()
    ctx = _build_base_context(db_conn, today)
    _add_today_context(db_conn, ctx, today)
    assert ctx["today_detail"] is None


def test_lookup_context_reads_target_date_activities(db_conn):
    _seed_run(db_conn, act_id=2, day="2026-09-20", name="Long Run")
    today = date.today().isoformat()
    ctx = _build_base_context(db_conn, today)
    ctx["_target_date"] = "2026-09-20"
    _add_lookup_context(db_conn, ctx, today)
    acts = ctx["lookup_activities"]
    assert len(acts) == 1
    assert acts[0]["name"] == "Long Run"
    assert acts[0]["calories"] == 512
