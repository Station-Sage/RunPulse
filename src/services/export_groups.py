"""내보내기 그룹 정의 — 허용 목록(allow-list). 목록에 없는 테이블은 절대 내보내지 않는다(data-export §2.1).

그룹마다 테이블·날짜 열·기본 선택을 정한다. 자격증명·토큰·캐시 테이블은 ALWAYS_EXCLUDED.
"""
from __future__ import annotations

import re
import sqlite3
from dataclasses import dataclass

SECRET_COLUMN_RE = re.compile(r"token|secret|password|api_key|cookie", re.I)
SECRET_VALUE_PREFIX = "enc:"

ALWAYS_EXCLUDED = frozenset({
    "mcp_tokens", "calendar_feeds", "mcp_audit", "sync_gates", "ai_cache", "caldav_pushes", "sync_jobs",
    "weather_cache", "plan_adjustments_new", "plan_replans_new",
})


@dataclass(frozen=True)
class TableDef:
    name: str
    date_col: str | None = None   # 그룹 날짜 열(없으면 기간 필터 미적용)
    activity_fk: bool = False     # activity_id 로 활동 기간에 종속
    optional: bool = False        # 마이그레이션 전 DB 에 없을 수 있음(v38)


@dataclass(frozen=True)
class GroupDef:
    key: str
    label: str
    tables: tuple[TableDef, ...]
    default: bool = False
    sensitive: bool = False


def _t(name, date_col=None, fk=False, optional=False) -> TableDef:
    return TableDef(name, date_col, fk, optional)


EXPORT_GROUPS: tuple[GroupDef, ...] = (
    GroupDef("activities", "활동 (요약·랩·최고 기록·피드백·장비)", (
        _t("activity_summaries", "start_time"), _t("activity_laps", fk=True), _t("activity_best_efforts", fk=True),
        _t("activity_exercise_sets", fk=True), _t("activity_groups", "activity_date"),
        _t("activity_feedback", fk=True), _t("gear"), _t("user_shoes", optional=True),
        _t("activity_shoe", fk=True, optional=True)), default=True),
    GroupDef("streams", "활동 스트림 (초 단위 심박·위치, 용량 큼)", (
        _t("activity_streams", fk=True), _t("activity_stream_meta", fk=True))),
    GroupDef("metrics", "지표·웰니스·예측·마일스톤", (
        _t("metric_store", "scope_id"), _t("daily_wellness", "date"), _t("prediction_snapshots", "as_of"),
        _t("milestones", "date")), default=True),
    GroupDef("plans", "목표·훈련 계획", (
        _t("goals"), _t("planned_workouts", "date"), _t("plan_adjustments"), _t("plan_progression"),
        _t("plan_replans"), _t("user_training_prefs"), _t("session_outcomes"))),
    GroupDef("checkins", "컨디션 체크인", (_t("user_inputs", "input_date"),)),
    GroupDef("episodes", "컨텍스트 기록 (질병·여행·고도)", (_t("context_episodes", "start_date", optional=True),),
             default=True, sensitive=True),
    GroupDef("races", "대회 일정·결과", (
        _t("race_calendar", "race_date", optional=True), _t("race_results", fk=True)), default=True),
    GroupDef("coach", "Coach 대화·피드백", (_t("chat_threads"), _t("chat_messages"), _t("ai_feedback")),
             sensitive=True),
    GroupDef("profile", "프로필·설정·동의", (
        _t("athlete_profile"), _t("athlete_stats"), _t("user_settings"), _t("coach_consent"),
        _t("illness_consent_events", optional=True)), sensitive=True),
    GroupDef("raw", "원본 payload (소스별 jsonl)", (_t("source_payloads", "entity_date"),), default=True),
)

GROUP_KEYS = tuple(g.key for g in EXPORT_GROUPS)
DEFAULT_GROUPS = tuple(g.key for g in EXPORT_GROUPS if g.default)
LEGACY_GROUPS = ("activities", "metrics", "raw")
SENSITIVE_GROUPS = tuple(g.key for g in EXPORT_GROUPS if g.sensitive)
_BY_KEY = {g.key: g for g in EXPORT_GROUPS}


def get_group(key: str) -> GroupDef:
    return _BY_KEY[key]


def all_group_tables() -> set[str]:
    return {t.name for g in EXPORT_GROUPS for t in g.tables}


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def safe_columns(conn: sqlite3.Connection, table: str) -> list[str]:
    """비밀 이름 열은 제외하지 않고 거부한다 — 허용 목록 테이블에 그런 열이 생기면 설계를 다시 봐야 한다."""
    cols = [r[1] for r in conn.execute(f"PRAGMA table_info({table})")]  # noqa: S608 — 상수 테이블명
    bad = [c for c in cols if SECRET_COLUMN_RE.search(c)]
    if bad:
        raise ValueError(f"{table}: 비밀 의심 열 {bad}")
    return cols


def has_secret_value(row) -> bool:
    return any(isinstance(v, str) and v.startswith(SECRET_VALUE_PREFIX) for v in row)
