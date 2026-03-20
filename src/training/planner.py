"""규칙 기반 주간 훈련 계획 생성 (Daniels 원칙 기반)."""

import sqlite3
from datetime import date, timedelta


# 요일별 훈련 패턴 (0=월, 6=일) — 거리 구간별
_WEEKLY_TEMPLATE: dict[str, list[str]] = {
    "marathon": ["rest", "easy", "tempo",    "easy", "interval", "easy", "long"],
    "half":     ["rest", "easy", "interval", "easy", "tempo",    "easy", "long"],
    "10k":      ["rest", "easy", "interval", "easy", "tempo",    "rest", "easy"],
    "5k":       ["rest", "easy", "interval", "rest", "interval", "easy", "easy"],
}

# long run 기준 거리 (베이스, km)
_LONG_RUN_BASE: dict[float, float] = {
    5.0: 10.0,
    10.0: 14.0,
    21.095: 20.0,
    42.195: 30.0,
}

# workout_type 별 HR zone 목표
_HR_ZONE: dict[str, int | None] = {
    "rest": None, "easy": 2, "tempo": 3, "interval": 4, "long": 2,
}

# workout_type 별 볼륨 가중치
_TYPE_WEIGHT: dict[str, float] = {
    "easy": 1.0, "tempo": 0.8, "interval": 0.6, "long": 1.0,
}


def _get_latest_fitness(conn: sqlite3.Connection) -> dict:
    """최근 CTL/ATL/TSB 조회."""
    row = conn.execute(
        "SELECT ctl, atl, tsb FROM daily_fitness ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if row:
        return {"ctl": row[0] or 0.0, "atl": row[1] or 0.0, "tsb": row[2] or 0.0}
    return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0}


def _weeks_to_race(race_date_str: str | None) -> int | None:
    """레이스까지 남은 주 수. 날짜 없으면 None."""
    if not race_date_str:
        return None
    try:
        delta = (date.fromisoformat(race_date_str) - date.today()).days
        return max(0, delta // 7)
    except ValueError:
        return None


def _training_phase(weeks_left: int | None) -> str:
    """훈련 단계 결정.

    Returns:
        'base' | 'build' | 'peak' | 'taper'
    """
    if weeks_left is None or weeks_left > 16:
        return "base"
    if weeks_left > 8:
        return "build"
    if weeks_left > 3:
        return "peak"
    return "taper"


def _weekly_volume_km(ctl: float, phase: str, tsb: float) -> float:
    """CTL/단계/TSB 기반 주간 목표 거리 계산."""
    if ctl < 20:
        base = 25.0
    elif ctl < 40:
        base = 35.0 + (ctl - 20) * 0.75   # 35~50
    elif ctl < 60:
        base = 50.0 + (ctl - 40) * 1.0    # 50~70
    else:
        base = 70.0 + min(ctl - 60, 20) * 0.5  # 70~80 상한

    phase_factor = {"base": 0.9, "build": 1.0, "peak": 1.05, "taper": 0.6}
    volume = base * phase_factor.get(phase, 1.0)

    # TSB 보정: 누적 피로 또는 여유 반영
    if tsb < -25:
        volume *= 0.8
    elif tsb < -15:
        volume *= 0.9
    elif tsb > 10:
        volume *= 1.05

    return round(volume, 1)


def _long_run_km(goal_distance_km: float, phase: str) -> float:
    """Long run 목표 거리."""
    keys = sorted(_LONG_RUN_BASE.keys())
    base_km = _LONG_RUN_BASE[keys[0]]
    for k in keys:
        if goal_distance_km >= k:
            base_km = _LONG_RUN_BASE[k]

    phase_factor = {"base": 0.85, "build": 1.0, "peak": 1.0, "taper": 0.6}
    return round(base_km * phase_factor.get(phase, 1.0), 1)


def _pick_template(goal_distance_km: float, phase: str) -> list[str]:
    """목표 거리/단계에 맞는 요일 패턴 선택."""
    if goal_distance_km >= 40:
        template = list(_WEEKLY_TEMPLATE["marathon"])
    elif goal_distance_km >= 18:
        template = list(_WEEKLY_TEMPLATE["half"])
    elif goal_distance_km >= 8:
        template = list(_WEEKLY_TEMPLATE["10k"])
    else:
        template = list(_WEEKLY_TEMPLATE["5k"])

    if phase == "taper":
        # 테이퍼: 인터벌 → easy 전환
        template = ["easy" if t == "interval" else t for t in template]
    elif phase == "base":
        # 베이스: 인터벌 → easy 전환 (기초 볼륨 중심)
        template = ["easy" if t == "interval" else t for t in template]

    return template


def _threshold_pace(config: dict | None) -> int:
    """설정에서 역치 페이스(sec/km) 추출. 없으면 300(5:00/km) 기본값."""
    if not config:
        return 300
    tp = config.get("user", {}).get("threshold_pace_sec_km")
    if tp:
        try:
            return int(tp)
        except (ValueError, TypeError):
            pass
    return 300


def _pace_range(workout_type: str, tp: int) -> tuple[int | None, int | None]:
    """훈련 유형별 목표 페이스 범위 (min, max) sec/km."""
    ranges = {
        "easy":     (tp + 60, tp + 90),
        "tempo":    (tp - 10, tp + 10),
        "interval": (tp - 40, tp - 20),
        "long":     (tp + 60, tp + 90),
        "rest":     (None, None),
    }
    return ranges.get(workout_type, (None, None))


def _rationale(workout_type: str, phase: str) -> str:
    """훈련 근거 설명."""
    base = {
        "rest":     "충분한 회복으로 다음 훈련 품질을 높입니다.",
        "easy":     "유산소 기반을 강화하는 저강도 훈련입니다. HR Zone 1-2 유지.",
        "tempo":    "젖산역치를 개선하는 중강도 훈련입니다. HR Zone 3-4 유지.",
        "interval": "최대 유산소 능력(VO2Max)을 향상하는 고강도 인터벌입니다.",
        "long":     "지구력을 키우는 장거리 훈련입니다. 대화 가능한 페이스 유지.",
    }.get(workout_type, "")

    if phase == "taper":
        base += " (테이퍼 기간: 신선도 유지에 집중)"
    return base


def _description(workout_type: str, distance_km: float | None, day: date) -> str:
    """훈련 설명 문자열."""
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    dname = day_names[day.weekday()]
    if workout_type == "rest":
        return f"{dname}요일 휴식"
    type_names = {
        "easy": "이지런", "tempo": "템포런",
        "interval": "인터벌", "long": "장거리런",
    }
    dist_str = f"{distance_km:.1f}km " if distance_km else ""
    return f"{dname}요일 {dist_str}{type_names.get(workout_type, workout_type)}"


def generate_weekly_plan(
    conn: sqlite3.Connection,
    goal_id: int | None = None,
    config: dict | None = None,
    week_start: date | None = None,
) -> list[dict]:
    """규칙 기반 주간 훈련 계획 생성.

    Args:
        conn: SQLite 연결.
        goal_id: 목표 id. None이면 active 목표 자동 선택.
        config: 설정 딕셔너리.
        week_start: 주 시작일 (월요일). None이면 이번 주 월요일.

    Returns:
        7개 planned_workout dict 리스트 (월~일).
    """
    from src.training.goals import get_active_goal, get_goal

    goal = get_goal(conn, goal_id) if goal_id is not None else None
    if goal is None:
        goal = get_active_goal(conn)

    goal_distance = goal["distance_km"] if goal else 10.0
    race_date = goal["race_date"] if goal else None

    fitness = _get_latest_fitness(conn)
    ctl = fitness["ctl"]
    tsb = fitness["tsb"]

    weeks_left = _weeks_to_race(race_date)
    phase = _training_phase(weeks_left)

    total_km = _weekly_volume_km(ctl, phase, tsb)
    long_km = _long_run_km(goal_distance, phase)
    template = _pick_template(goal_distance, phase)

    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    tp = _threshold_pace(config)

    # 볼륨 배분: long 고정 후 나머지를 가중치 비율로 분배
    long_count = template.count("long")
    remaining_km = max(0.0, total_km - long_km * long_count)
    non_long_non_rest = [t for t in template if t not in ("rest", "long")]
    total_weight = sum(_TYPE_WEIGHT.get(t, 1.0) for t in non_long_non_rest)

    plan = []
    for i, wtype in enumerate(template):
        day = week_start + timedelta(days=i)

        if wtype == "rest":
            dist = None
        elif wtype == "long":
            dist = long_km
        else:
            w = _TYPE_WEIGHT.get(wtype, 1.0)
            dist = round(remaining_km * w / total_weight, 1) if total_weight > 0 else 0.0
            dist = dist if dist > 0 else None

        pace_min, pace_max = _pace_range(wtype, tp)

        plan.append({
            "date": day.isoformat(),
            "workout_type": wtype,
            "distance_km": dist,
            "target_pace_min": pace_min,
            "target_pace_max": pace_max,
            "target_hr_zone": _HR_ZONE.get(wtype),
            "description": _description(wtype, dist, day),
            "rationale": _rationale(wtype, phase),
            "source": "planner",
        })

    return plan


def save_weekly_plan(conn: sqlite3.Connection, plan: list[dict]) -> int:
    """주간 계획을 planned_workouts 테이블에 저장.

    같은 날짜의 source='planner' 기존 레코드를 삭제 후 재삽입한다.

    Returns:
        저장된 레코드 수.
    """
    if not plan:
        return 0

    for w in plan:
        conn.execute(
            "DELETE FROM planned_workouts WHERE date = ? AND source = 'planner'",
            (w["date"],),
        )

    count = 0
    for w in plan:
        conn.execute(
            """INSERT INTO planned_workouts
               (date, workout_type, distance_km, target_pace_min, target_pace_max,
                target_hr_zone, description, rationale, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                w["date"], w["workout_type"], w.get("distance_km"),
                w.get("target_pace_min"), w.get("target_pace_max"),
                w.get("target_hr_zone"), w.get("description"),
                w.get("rationale"), w.get("source", "planner"),
            ),
        )
        count += 1

    conn.commit()
    return count


def get_planned_workouts(
    conn: sqlite3.Connection,
    week_start: date | None = None,
) -> list[dict]:
    """이번 주 (또는 지정 주) planned_workouts 조회.

    Returns:
        날짜 오름차순 planned_workout dict 리스트.
    """
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)

    rows = conn.execute(
        """SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max,
                  target_hr_zone, description, rationale, completed, source, ai_model
           FROM planned_workouts
           WHERE date >= ? AND date < ?
           ORDER BY date""",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    keys = ["id", "date", "workout_type", "distance_km", "target_pace_min",
            "target_pace_max", "target_hr_zone", "description", "rationale",
            "completed", "source", "ai_model"]
    return [dict(zip(keys, r)) for r in rows]
