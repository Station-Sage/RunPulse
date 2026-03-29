"""훈련 계획 — 상수 및 설정/메트릭 조회 헬퍼.

planner.py에서 분리. 상수 정의 + user_training_prefs 로드 +
가용일 계산 + 피트니스·VDOT·eFTP·MarathonShape 조회.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta

# ── 상수 ──────────────────────────────────────────────────────────────────

# 목표 거리 → km 매핑
DISTANCE_LABEL_KM: dict[str, float] = {
    "1.5k": 1.5,
    "3k":   3.0,
    "5k":   5.0,
    "10k":  10.0,
    "half": 21.095,
    "full": 42.195,
}

# Daniels 훈련 단계 (레이스까지 남은 주 수 기준)
_PHASE_THRESHOLDS = {
    "taper": 3,   # 3주 이하
    "peak":  8,   # 3~8주
    "build": 16,  # 8~16주
    # > 16주 → base
}

# workout_type별 HR zone 목표
HR_ZONE: dict[str, int | None] = {
    "rest": None, "recovery": 1,
    "easy": 2, "long": 2,
    "tempo": 3, "interval": 4,
}

# Seiler 2010: 강도별 분류
Q_TYPES = {"tempo", "interval"}   # Quality day 타입
Z1_TYPES = {"easy", "recovery", "rest"}  # Zone 1 타입

# Buchheit & Laursen 2013: 인터벌 타입별 볼륨 가중치
TYPE_WEIGHT: dict[str, float] = {
    "easy": 1.0, "recovery": 0.6, "tempo": 0.8,
    "interval": 0.5, "long": 1.0,
}

# 거리별 롱런 최대 거리 기준 (Daniels, Pfitzinger)
LONG_RUN_BASE: dict[str, float] = {
    "1.5k": 8.0,
    "3k":   10.0,
    "5k":   12.0,
    "10k":  16.0,
    "half": 22.0,
    "full": 32.0,
    "custom": 14.0,
}

# 단계별 롱런 비율
LONG_RUN_PHASE_FACTOR = {
    "base": 0.80, "build": 1.0, "peak": 1.0, "taper": 0.55
}

# 주간 볼륨 단계 배율 (Daniels 원칙)
PHASE_VOLUME_FACTOR = {
    "base": 0.88, "build": 1.0, "peak": 1.05,
    "taper": 0.55,  # Mujika & Padilla 2003: 40~55% 감소
}

# 거리별 Q-day 최대 횟수 (Daniels 권장)
MAX_Q_DAYS_BY_LABEL: dict[str, int] = {
    "1.5k": 3, "3k": 3, "5k": 2, "10k": 2, "half": 2, "full": 2, "custom": 2
}


# ── 사용자 설정 로드 ───────────────────────────────────────────────────────

def load_prefs(conn: sqlite3.Connection) -> dict:
    """user_training_prefs 로드. 없으면 기본값."""
    row = conn.execute("SELECT * FROM user_training_prefs LIMIT 1").fetchone()
    if not row:
        return {
            "rest_weekdays_mask": 0,
            "blocked_dates": [],
            "interval_rep_m": 1000,
            "max_q_days": 0,
        }
    cols = [d[1] for d in conn.execute("PRAGMA table_info(user_training_prefs)").fetchall()]
    d = dict(zip(cols, row))
    try:
        d["blocked_dates"] = json.loads(d.get("blocked_dates") or "[]")
    except (json.JSONDecodeError, TypeError):
        d["blocked_dates"] = []
    return d


def get_available_days(week_start: date, prefs: dict) -> list[int]:
    """이번 주 훈련 가능 요일 인덱스(0=월~6=일) 반환.

    비트마스크: bit0=월(1), bit1=화(2), ..., bit6=일(64)
    """
    mask = prefs.get("rest_weekdays_mask", 0)
    blocked = set(prefs.get("blocked_dates") or [])
    available = []
    for i in range(7):
        day = week_start + timedelta(days=i)
        bit = 1 << i
        if (mask & bit) or day.isoformat() in blocked:
            continue
        available.append(i)
    return available


# ── 메트릭 조회 ───────────────────────────────────────────────────────────

def get_latest_fitness(conn: sqlite3.Connection) -> dict:
    """최근 CTL/ATL/TSB 조회."""
    row = conn.execute(
        "SELECT ctl, atl, tsb FROM daily_fitness ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if row:
        return {"ctl": row[0] or 0.0, "atl": row[1] or 0.0, "tsb": row[2] or 0.0}
    return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0}


def get_vdot_adj(conn: sqlite3.Connection) -> float | None:
    """VDOT_ADJ 조회 (최근)."""
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='VDOT_ADJ' AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return float(row[0]) if row else None


def get_eftp(conn: sqlite3.Connection) -> int | None:
    """eFTP (sec/km) 조회."""
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='eFTP' AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None


def get_marathon_shape_pct(conn: sqlite3.Connection) -> float | None:
    """MarathonShape 점수 (0~100) 조회."""
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='MarathonShape' AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return float(row[0]) if row else None


def get_week_index(week_start: date, conn: sqlite3.Connection) -> int:
    """3:1 사이클에서 현재가 몇 번째 주인지 계산 (0=1주차, 3=회복주).

    Foster 1998: Monotony 기반 3:1 사이클 권장.
    """
    earliest = conn.execute(
        "SELECT MIN(date) FROM planned_workouts WHERE source='planner'"
    ).fetchone()[0]
    if not earliest:
        return 0
    try:
        first_week = date.fromisoformat(earliest)
        first_week -= timedelta(days=first_week.weekday())
        delta_weeks = (week_start - first_week).days // 7
        return delta_weeks % 4  # 0,1,2 = 부하주, 3 = 회복주
    except (ValueError, TypeError):
        return 0
