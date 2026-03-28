"""규칙 기반 주간 훈련 계획 생성 (v2 — 논문 기반 재설계).

설계 원칙:
  1. 사용자 가용일 우선 (휴식 요일/날짜 먼저 차단)
  2. Seiler 2010 80/20 원칙 + Daniels Q-day 규칙 (주 2~3회)
  3. Hard-Easy 원칙: Q-day 후 반드시 1일 이상 Z1/rest
  4. CRS 게이트(crs.py): 훈련 강도 상한 실시간 조정
  5. Daniels Running Formula 3rd Ed: VDOT_ADJ → 페이스 처방
  6. Buchheit & Laursen 2013: 인터벌 처방 (interval_calc.py)
  7. Mujika & Padilla 2003 / Bosquet 2007: 테이퍼 (볼륨 -40~50%, 강도 유지)
  8. 3:1 사이클: 3주 부하 후 1주 회복 (Foster 1998 Monotony 근거)

DISTANCE_LABELS (goals.distance_label):
  '1.5k', '3k', '5k', '10k', 'half', 'full', 'custom'

훈련 타입:
  'easy', 'tempo', 'interval', 'long', 'rest', 'recovery'
  (marathon_pace는 향후 추가 예정)
"""
from __future__ import annotations

import json
import logging
import sqlite3
from datetime import date, timedelta

log = logging.getLogger(__name__)

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
_HR_ZONE: dict[str, int | None] = {
    "rest": None, "recovery": 1,
    "easy": 2, "long": 2,
    "tempo": 3, "interval": 4,
}

# Seiler 2010: 강도별 분류
_Q_TYPES = {"tempo", "interval"}   # Quality day 타입
_Z1_TYPES = {"easy", "recovery", "rest"}  # Zone 1 타입

# Buchheit & Laursen 2013: 인터벌 타입별 볼륨 가중치
_TYPE_WEIGHT: dict[str, float] = {
    "easy": 1.0, "recovery": 0.6, "tempo": 0.8,
    "interval": 0.5, "long": 1.0,
}

# 거리별 롱런 최대 거리 기준 (Daniels, Pfitzinger)
_LONG_RUN_BASE: dict[str, float] = {
    "1.5k": 8.0,
    "3k":   10.0,
    "5k":   12.0,
    "10k":  16.0,
    "half": 22.0,
    "full": 32.0,
    "custom": 14.0,
}

# 단계별 롱런 비율
_LONG_RUN_PHASE_FACTOR = {
    "base": 0.80, "build": 1.0, "peak": 1.0, "taper": 0.55
}

# 주간 볼륨 단계 배율 (Daniels 원칙)
_PHASE_VOLUME_FACTOR = {
    "base": 0.88, "build": 1.0, "peak": 1.05,
    "taper": 0.55,  # Mujika & Padilla 2003: 40~55% 감소
}

# 거리별 Q-day 최대 횟수 (Daniels 권장)
# 5K: 최대 2~3회, 마라톤: 2회 + 롱런
_MAX_Q_DAYS_BY_LABEL: dict[str, int] = {
    "1.5k": 3, "3k": 3, "5k": 2, "10k": 2, "half": 2, "full": 2, "custom": 2
}


# ── 사용자 설정 로드 ───────────────────────────────────────────────────────

def _load_prefs(conn: sqlite3.Connection) -> dict:
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


def _get_available_days(week_start: date, prefs: dict) -> list[int]:
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

def _get_latest_fitness(conn: sqlite3.Connection) -> dict:
    """최근 CTL/ATL/TSB 조회."""
    row = conn.execute(
        "SELECT ctl, atl, tsb FROM daily_fitness ORDER BY date DESC LIMIT 1"
    ).fetchone()
    if row:
        return {"ctl": row[0] or 0.0, "atl": row[1] or 0.0, "tsb": row[2] or 0.0}
    return {"ctl": 0.0, "atl": 0.0, "tsb": 0.0}


def _get_vdot_adj(conn: sqlite3.Connection) -> float | None:
    """VDOT_ADJ 조회 (최근 30일)."""
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='VDOT_ADJ' AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return float(row[0]) if row else None


def _get_eftp(conn: sqlite3.Connection) -> int | None:
    """eFTP (sec/km) 조회."""
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='eFTP' AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return int(row[0]) if row else None


def _get_marathon_shape_pct(conn: sqlite3.Connection) -> float | None:
    """MarathonShape 점수 (0~100) 조회."""
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name='MarathonShape' AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1"
    ).fetchone()
    return float(row[0]) if row else None


def _get_week_index(week_start: date, conn: sqlite3.Connection) -> int:
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


# ── 훈련 단계 결정 ────────────────────────────────────────────────────────

def _weeks_to_race(race_date_str: str | None) -> int | None:
    if not race_date_str:
        return None
    try:
        delta = (date.fromisoformat(race_date_str) - date.today()).days
        return max(0, delta // 7)
    except ValueError:
        return None


def _training_phase(weeks_left: int | None, week_idx: int) -> str:
    """훈련 단계 결정.

    3:1 회복주(week_idx==3)이면 단계와 무관하게 'recovery_week' 표시.
    """
    if week_idx == 3:
        return "recovery_week"  # Foster 1998 3:1 사이클
    if weeks_left is None or weeks_left > 16:
        return "base"
    if weeks_left > 8:
        return "build"
    if weeks_left > 3:
        return "peak"
    return "taper"


# ── 주간 볼륨 계산 ────────────────────────────────────────────────────────

def _resolve_distance_label(goal_distance_km: float,
                             distance_label: str | None) -> str:
    """거리 레이블 결정."""
    if distance_label and distance_label in _LONG_RUN_BASE:
        return distance_label
    # distance_km으로 추정
    if goal_distance_km >= 40:   return "full"
    if goal_distance_km >= 18:   return "half"
    if goal_distance_km >= 8:    return "10k"
    if goal_distance_km >= 4:    return "5k"
    if goal_distance_km >= 2.5:  return "3k"
    return "1.5k"


def _weekly_volume_km(ctl: float, phase: str, tsb: float,
                      shape_pct: float | None) -> float:
    """주간 목표 거리 계산.

    근거:
    - CTL → 기본 볼륨 (Coggan 2003 / Banister 1991)
    - Pfitzinger 방식: 절대값 상한 병행 (주간 최대 증가 20km)
    - TSB 보정: Coggan 2003 TSB < -30 과훈련 경계
    - MarathonShape 보정: 현재 훈련 완성도가 낮으면 볼륨 조정
    """
    # CTL 기반 기본 볼륨 (Pfitzinger 절대값 상한 포함)
    if ctl < 20:
        base = 25.0
    elif ctl < 40:
        base = 30.0 + (ctl - 20) * 0.80   # 30~46km
    elif ctl < 60:
        base = 46.0 + (ctl - 40) * 0.90   # 46~64km
    else:
        base = 64.0 + min(ctl - 60, 25) * 0.5  # 64~76.5km 상한

    # 훈련 단계 보정
    if phase == "recovery_week":
        # Foster 1998 3:1 사이클: 회복주 볼륨 -30%
        volume = base * 0.70
    else:
        volume = base * _PHASE_VOLUME_FACTOR.get(phase, 1.0)

    # TSB 보정 (Coggan 2003)
    if tsb < -30:
        volume *= 0.78
    elif tsb < -20:
        volume *= 0.88
    elif tsb > 15:
        volume *= 1.05

    # Shape 보정: 현재 완성도가 매우 낮으면 볼륨 억제
    if shape_pct is not None and shape_pct < 40:
        volume *= 0.85  # 준비 부족 → 볼륨 과하게 올리지 않음

    return round(volume, 1)


# ── Q-day 배치 (Hard-Easy 원칙) ───────────────────────────────────────────

def _assign_qdayslots(available_days: list[int], n_q: int,
                      label: str, phase: str) -> list[int]:
    """Q-day 요일 인덱스 선택.

    Hard-Easy 원칙 (Lydiard/Bowerman): Q-day 사이 최소 1일 간격.
    Long run은 주말(5=토, 6=일) 우선 배치.
    """
    if not available_days or n_q == 0:
        return []

    # Long run 선호일 (주말 우선, phase != taper)
    prefer_long = [d for d in available_days if d >= 5]
    if not prefer_long:
        prefer_long = [available_days[-1]]  # 없으면 마지막 가용일

    selected: list[int] = []
    last_q = -2  # 직전 Q-day 요일 (간격 체크용)

    # 첫 Q-day: 가용일 중 2번째 이후 (첫날은 easy/rest로 시작)
    candidates = [d for d in available_days if d > available_days[0]]
    for d in candidates:
        if len(selected) >= n_q:
            break
        if d - last_q >= 2:  # Hard-Easy: 2일 이상 간격
            selected.append(d)
            last_q = d

    return sorted(selected)


def _assign_long_run_slot(available_days: list[int],
                          q_slots: list[int]) -> int | None:
    """Long run 배치: 주말 가용일 우선, Q-day와 겹치지 않게."""
    prefer = [d for d in available_days if d >= 5 and d not in q_slots]
    if prefer:
        return prefer[-1]  # 일요일 우선
    # 주말 없으면 Q-day 제외 가용일 중 마지막
    others = [d for d in available_days if d not in q_slots]
    return others[-1] if others else None


# ── 페이스 처방 (Daniels VDOT 테이블) ────────────────────────────────────

def _get_paces_from_vdot(vdot: float | None,
                          config: dict | None) -> dict[str, int]:
    """VDOT_ADJ → E/T/I/R 페이스 (sec/km).

    VDOT 없으면 eFTP 기반 fallback, 없으면 config threshold_pace fallback.
    """
    if vdot and vdot > 20:
        try:
            from src.metrics.daniels_table import get_training_paces
            return get_training_paces(vdot)
        except Exception:
            pass

    # fallback: threshold_pace 기반 오프셋
    tp = 300
    if config:
        tp_cfg = config.get("user", {}).get("threshold_pace_sec_km")
        if tp_cfg:
            try:
                tp = int(tp_cfg)
            except (ValueError, TypeError):
                pass
    return {
        "E": tp + 75, "M": tp + 20, "T": tp,
        "I": tp - 30, "R": tp - 55,
    }


def _pace_range(workout_type: str, paces: dict[str, int]) -> tuple[int | None, int | None]:
    """훈련 유형 → 페이스 범위 (min, max) sec/km."""
    mapping = {
        "easy":     ("E", 30),   # E pace ± 30초
        "long":     ("E", 30),
        "recovery": ("E", 50),   # E+50 느리게
        "tempo":    ("T", 10),   # T pace ± 10초
        "interval": ("I", 10),   # I pace ± 10초
        "rest":     None,
    }
    spec = mapping.get(workout_type)
    if spec is None:
        return None, None
    key, delta = spec
    base = paces.get(key, 300)
    return base - delta, base + delta


# ── 볼륨 배분 ─────────────────────────────────────────────────────────────

def _distribute_volume(template: list[str], total_km: float,
                        long_km: float) -> list[float | None]:
    """타입별 거리 배분.

    Long run 고정 후 Seiler 80/20 원칙:
    - 전체 볼륨 중 Q-day(tempo+interval) 비중 ≤ 20%
    - 나머지 80%를 easy/recovery에 배분
    """
    dists: list[float | None] = []
    long_count = template.count("long")
    q_max_km = total_km * 0.20  # Seiler 2010: Q-day 최대 20%
    long_total = long_km * long_count
    remaining = max(0.0, total_km - long_total)

    # Q-day와 easy 분리
    non_rest = [t for t in template if t not in ("rest", "long")]
    q_types = [t for t in non_rest if t in _Q_TYPES]
    e_types = [t for t in non_rest if t not in _Q_TYPES]

    # Q-day 볼륨 계산 (가중치 비례 + 20% 상한)
    q_weight_sum = sum(_TYPE_WEIGHT.get(t, 1.0) for t in q_types)
    e_weight_sum = sum(_TYPE_WEIGHT.get(t, 1.0) for t in e_types)
    total_weight = q_weight_sum + e_weight_sum

    q_budget = min(q_max_km, remaining * q_weight_sum / total_weight) if total_weight else 0
    e_budget = remaining - q_budget

    # 타입별 거리 dict
    type_km: dict[str, float] = {}
    if q_weight_sum > 0:
        for t in _Q_TYPES:
            w = _TYPE_WEIGHT.get(t, 1.0)
            cnt = q_types.count(t)
            if cnt:
                type_km[t] = round(q_budget * w / q_weight_sum, 1)
    if e_weight_sum > 0:
        for t in ("easy", "recovery"):
            w = _TYPE_WEIGHT.get(t, 1.0)
            cnt = e_types.count(t)
            if cnt:
                # e_weight_sum은 cnt*w를 이미 포함 → 슬롯당 거리
                type_km[t] = round(e_budget * w / e_weight_sum, 1)

    for wtype in template:
        if wtype == "rest":
            dists.append(None)
        elif wtype == "long":
            dists.append(long_km)
        else:
            km = type_km.get(wtype, 5.0)
            dists.append(max(2.0, km))

    return dists


# ── 설명/근거 ─────────────────────────────────────────────────────────────

_TYPE_NAMES = {
    "easy": "이지런", "tempo": "템포런", "interval": "인터벌",
    "long": "장거리런", "rest": "휴식", "recovery": "회복조깅",
}

_RATIONALE = {
    "rest":
        "충분한 회복. 다음 훈련 품질을 높입니다.",
    "recovery":
        "극저강도 회복 조깅 (HR Zone 1). 혈류 촉진으로 피로 물질 제거.",
    "easy":
        "저강도 유산소 (HR Zone 2). Seiler 2010: 전체 볼륨의 80% 이상 유지.",
    "tempo":
        "젖산 역치 훈련 (HR Zone 3~4). Daniels T-pace 유지. 20~60분 연속.",
    "interval":
        "VO2max 자극 (HR Zone 4~5). Billat 2001: 반복당 60초+ 유지.",
    "long":
        "지구력 기반 장거리 (HR Zone 2). 대화 가능 페이스. "
        "Daniels: E-pace 유지. Friel: 디커플링 5% 이하 목표.",
}


def _description(wtype: str, dist: float | None, day: date) -> str:
    day_names = ["월", "화", "수", "목", "금", "토", "일"]
    dn = day_names[day.weekday()]
    if wtype == "rest":
        return f"{dn}요일 휴식"
    name = _TYPE_NAMES.get(wtype, wtype)
    dist_str = f"{dist:.1f}km " if dist else ""
    return f"{dn}요일 {dist_str}{name}"


# ── 메인 계획 생성 함수 ───────────────────────────────────────────────────

def generate_weekly_plan(
    conn: sqlite3.Connection,
    goal_id: int | None = None,
    config: dict | None = None,
    week_start: date | None = None,
) -> list[dict]:
    """규칙 기반 주간 훈련 계획 생성 (v2).

    Args:
        conn: SQLite 연결.
        goal_id: 목표 id. None이면 active 목표 자동 선택.
        config: 설정 딕셔너리.
        week_start: 주 시작일 (월요일). None이면 이번 주 월요일.

    Returns:
        7개 planned_workout dict 리스트 (월~일).
    """
    from src.training.goals import get_active_goal, get_goal

    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())

    # 목표 로드
    goal = get_goal(conn, goal_id) if goal_id is not None else None
    if goal is None:
        goal = get_active_goal(conn)

    goal_distance = goal["distance_km"] if goal else 10.0
    race_date = goal["race_date"] if goal else None
    distance_label = goal.get("distance_label") if goal else None
    dlabel = _resolve_distance_label(goal_distance, distance_label)

    # 피트니스 데이터
    fitness = _get_latest_fitness(conn)
    ctl, tsb = fitness["ctl"], fitness["tsb"]
    vdot = _get_vdot_adj(conn)
    eftp = _get_eftp(conn)
    shape_pct = _get_marathon_shape_pct(conn)

    # 훈련 단계
    weeks_left = _weeks_to_race(race_date)
    week_idx = _get_week_index(week_start, conn)
    phase = _training_phase(weeks_left, week_idx)

    # 주간 볼륨
    total_km = _weekly_volume_km(ctl, phase, tsb, shape_pct)
    long_km = _LONG_RUN_BASE.get(dlabel, 14.0) * _LONG_RUN_PHASE_FACTOR.get(
        phase if phase != "recovery_week" else "base", 1.0
    )
    long_km = min(long_km, total_km * 0.35)  # Long run 상한: 주간 볼륨의 35%

    # 사용자 설정 (휴식 요일/날짜)
    prefs = _load_prefs(conn)
    available = _get_available_days(week_start, prefs)
    if not available:
        # 전부 휴식으로 설정된 경우 — 기본 월만 허용
        available = list(range(7))

    # Q-day 수 결정
    max_q = prefs.get("max_q_days") or _MAX_Q_DAYS_BY_LABEL.get(dlabel, 2)
    if phase in ("taper", "base", "recovery_week"):
        max_q = min(max_q, 1)  # 베이스/테이퍼: Q-day 최대 1회
    n_avail = len(available)
    # Seiler: 80/20 → 가용일의 20% = Q-day
    n_q = min(max_q, max(1, round(n_avail * 0.20)))
    if n_avail <= 3:
        n_q = min(1, n_q)  # 3일 이하이면 Q-day 최대 1회

    # Q-day 슬롯 배치 (Hard-Easy 원칙)
    q_slots = _assign_qdayslots(available, n_q, dlabel, phase)

    # Long run 슬롯 (Q-day와 별도, 주말 우선)
    has_long = dlabel not in ("1.5k", "3k") and phase != "taper"
    long_slot = _assign_long_run_slot(available, q_slots) if has_long else None

    # 테이퍼: interval→tempo로 전환 (Mujika 2003: 강도 유지, 볼륨 감소)
    q_type_for_slot = "interval" if phase not in ("taper", "base", "recovery_week") else "tempo"

    # CRS 게이트 (오늘 기준)
    try:
        from src.metrics.crs import evaluate as crs_evaluate, LEVEL_Z1, LEVEL_Z1_Z2
        crs_result = crs_evaluate(conn)
        crs_level = crs_result["level"]
        crs_score = crs_result["crs"]
    except Exception:
        crs_level = 3  # fallback: FULL
        crs_score = 60.0

    # 7일 템플릿 구성
    template: list[str] = []
    for i in range(7):
        if i not in available:
            template.append("rest")
        elif i == long_slot and has_long:
            template.append("long")
        elif i in q_slots:
            # CRS 게이트: Z1만 허용이면 easy로 다운그레이드
            if crs_level <= 1:
                template.append("easy")
            elif crs_level == 2:
                template.append("tempo")  # Z1~Z2: interval→tempo
            else:
                template.append(q_type_for_slot)
        elif i == available[0]:
            # 첫 가용일: 항상 easy (워밍업 역할)
            template.append("easy")
        else:
            template.append("easy")

    # 거리 배분
    paces = _get_paces_from_vdot(vdot, config)
    dists = _distribute_volume(template, total_km, long_km)

    # 인터벌 처방 JSON 생성
    interval_rep_m = prefs.get("interval_rep_m", 1000)

    plan: list[dict] = []
    for i, (wtype, dist) in enumerate(zip(template, dists)):
        day = week_start + timedelta(days=i)
        pace_min, pace_max = _pace_range(wtype, paces)

        # 인터벌 처방 JSON
        interval_json: str | None = None
        if wtype == "interval" and vdot:
            try:
                from src.training.interval_calc import prescribe_from_vdot
                rx = prescribe_from_vdot(interval_rep_m, vdot, eftp)
                interval_json = json.dumps(rx, ensure_ascii=False)
            except Exception as e:
                log.warning("인터벌 처방 오류: %s", e)

        plan.append({
            "date": day.isoformat(),
            "workout_type": wtype,
            "distance_km": dist,
            "target_pace_min": pace_min,
            "target_pace_max": pace_max,
            "target_hr_zone": _HR_ZONE.get(wtype),
            "description": _description(wtype, dist, day),
            "rationale": _RATIONALE.get(wtype, ""),
            "source": "planner",
            "interval_prescription": interval_json,
            # 메타 (저장 시 제외)
            "_phase": phase,
            "_crs": crs_score,
            "_vdot": vdot,
        })

    return plan


def save_weekly_plan(conn: sqlite3.Connection, plan: list[dict]) -> int:
    """주간 계획을 planned_workouts 테이블에 저장.

    같은 날짜의 source='planner' 기존 레코드를 삭제 후 재삽입.

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
                target_hr_zone, description, rationale, source, interval_prescription)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                w["date"], w["workout_type"], w.get("distance_km"),
                w.get("target_pace_min"), w.get("target_pace_max"),
                w.get("target_hr_zone"), w.get("description"),
                w.get("rationale"), w.get("source", "planner"),
                w.get("interval_prescription"),
            ),
        )
        count += 1

    conn.commit()
    return count


def get_planned_workouts(
    conn: sqlite3.Connection,
    week_start: date | None = None,
) -> list[dict]:
    """이번 주 (또는 지정 주) planned_workouts 조회."""
    if week_start is None:
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=7)

    rows = conn.execute(
        """SELECT id, date, workout_type, distance_km, target_pace_min, target_pace_max,
                  target_hr_zone, description, rationale, completed, source, ai_model,
                  interval_prescription
           FROM planned_workouts
           WHERE date >= ? AND date < ?
           ORDER BY date""",
        (week_start.isoformat(), week_end.isoformat()),
    ).fetchall()

    keys = ["id", "date", "workout_type", "distance_km", "target_pace_min",
            "target_pace_max", "target_hr_zone", "description", "rationale",
            "completed", "source", "ai_model", "interval_prescription"]
    return [dict(zip(keys, r)) for r in rows]


def upsert_user_training_prefs(
    conn: sqlite3.Connection,
    rest_weekdays_mask: int = 0,
    blocked_dates: list[str] | None = None,
    interval_rep_m: int = 1000,
    max_q_days: int = 0,
    long_run_weekday_mask: int = 0,
) -> None:
    """user_training_prefs 저장 (id=1 고정 upsert).

    Args:
        long_run_weekday_mask: 롱런 요일 비트마스크 (0=자동 선택).
    """
    conn.execute(
        """INSERT INTO user_training_prefs
           (id, rest_weekdays_mask, blocked_dates, interval_rep_m, max_q_days,
            long_run_weekday_mask, updated_at)
           VALUES (1, ?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(id) DO UPDATE SET
               rest_weekdays_mask=excluded.rest_weekdays_mask,
               blocked_dates=excluded.blocked_dates,
               interval_rep_m=excluded.interval_rep_m,
               max_q_days=excluded.max_q_days,
               long_run_weekday_mask=excluded.long_run_weekday_mask,
               updated_at=excluded.updated_at""",
        (
            rest_weekdays_mask,
            json.dumps(blocked_dates or [], ensure_ascii=False),
            interval_rep_m,
            max_q_days,
            long_run_weekday_mask,
        ),
    )
    conn.commit()
