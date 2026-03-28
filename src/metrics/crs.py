"""CRS (Composite Readiness Score) — 복합 훈련 준비도 평가.

설계 원칙:
  1. 게이트 필터 (논문 기반 hard rule) — 훈련 허용 강도 상한 결정
  2. CRS 참고 점수 (0~100) — 여유도 표현, ML 피처용 (가중치 미검증)

게이트 필터 근거:
  - Gate 1: ACWR   — Gabbett 2016, BJSM (1.0~1.3 최적, >1.5 위험)
  - Gate 2: HRV    — Plews et al. 2013, IJSPP (7일 rolling 대비 -10% 경계)
  - Gate 3: Body Battery — Garmin 에너지 지표
  - Gate 4: TSB    — Coggan 2003 / Banister 1991 (<-30 과훈련 경계)
  - Gate 5: CIRS   — 내부 복합 부상 위험 점수 (>80 위험)

CRS 참고 점수:
  UTRS(기존 통합 준비도) 기반 + ACWR/CIRS 보정.
  향후 ML session_outcomes로 가중치 보정 예정.

반환 훈련 레벨:
  0 = rest    : 휴식 (게이트 차단)
  1 = z1_only : Z1 이지런만 허용
  2 = z1_z2   : Z1~Z2 (tempo 가능, interval 금지)
  3 = full    : 계획대로 (모든 강도 허용)
  4 = boost   : +5% 볼륨 허용 (컨디션 매우 양호)
"""
from __future__ import annotations

import sqlite3
from datetime import date, timedelta


# ── 상수 ──────────────────────────────────────────────────────────────────

# 훈련 레벨 레이블
LEVEL_REST = 0
LEVEL_Z1 = 1
LEVEL_Z1_Z2 = 2
LEVEL_FULL = 3
LEVEL_BOOST = 4

LEVEL_LABELS = {
    LEVEL_REST:  "휴식",
    LEVEL_Z1:    "이지런만",
    LEVEL_Z1_Z2: "템포 이하",
    LEVEL_FULL:  "계획대로",
    LEVEL_BOOST: "볼륨 +5%",
}


# ── 데이터 로드 헬퍼 ───────────────────────────────────────────────────────

def _get_metric(conn: sqlite3.Connection, name: str, target_date: str,
                days_back: int = 7) -> float | None:
    """computed_metrics에서 최근 N일 내 가장 최근 값 조회."""
    since = (date.fromisoformat(target_date) - timedelta(days=days_back)).isoformat()
    row = conn.execute(
        "SELECT metric_value FROM computed_metrics "
        "WHERE metric_name=? AND date<=? AND date>=? AND metric_value IS NOT NULL "
        "ORDER BY date DESC LIMIT 1",
        (name, target_date, since),
    ).fetchone()
    return float(row[0]) if row else None


def _get_wellness(conn: sqlite3.Connection, col: str, target_date: str,
                  days_back: int = 3) -> float | None:
    """daily_wellness에서 최근 N일 내 가장 최근 값 조회."""
    since = (date.fromisoformat(target_date) - timedelta(days=days_back)).isoformat()
    row = conn.execute(
        f"SELECT {col} FROM daily_wellness "
        f"WHERE {col} IS NOT NULL AND date<=? AND date>=? "
        f"ORDER BY date DESC LIMIT 1",
        (target_date, since),
    ).fetchone()
    return float(row[0]) if row else None


def _get_hrv_rolling_avg(conn: sqlite3.Connection, target_date: str) -> float | None:
    """최근 7일 HRV rolling 평균 (Plews 2013 기준값)."""
    since = (date.fromisoformat(target_date) - timedelta(days=7)).isoformat()
    rows = conn.execute(
        "SELECT hrv_value FROM daily_wellness "
        "WHERE hrv_value IS NOT NULL AND date<=? AND date>=? "
        "ORDER BY date DESC",
        (target_date, since),
    ).fetchall()
    vals = [float(r[0]) for r in rows if r[0]]
    return sum(vals) / len(vals) if vals else None


# ── Gate 1: ACWR (Gabbett 2016) ───────────────────────────────────────────

def _gate_acwr(acwr: float | None) -> tuple[int, str]:
    """ACWR → 최대 허용 레벨 + 메시지.

    Gabbett 2016 (BJSM): ACWR > 1.5 → 부상 위험 급증.
    """
    if acwr is None:
        return LEVEL_FULL, "ACWR 데이터 없음 (통과)"
    if acwr > 1.5:
        return LEVEL_Z1, f"ACWR {acwr:.2f} > 1.5 — 부상 위험 (Gabbett 2016)"
    if acwr > 1.3:
        return LEVEL_Z1_Z2, f"ACWR {acwr:.2f} > 1.3 — 주의 구간"
    if acwr < 0.8:
        return LEVEL_FULL, f"ACWR {acwr:.2f} < 0.8 — 훈련 부족 (볼륨 증가 고려)"
    return LEVEL_FULL, f"ACWR {acwr:.2f} — 최적 구간 (0.8~1.3)"


# ── Gate 2: HRV (Plews et al. 2013) ──────────────────────────────────────

def _gate_hrv(hrv_today: float | None, hrv_rolling: float | None) -> tuple[int, str]:
    """HRV 오늘값 vs 7일 rolling 평균 비교.

    Plews 2013 (IJSPP): rolling 평균 대비 -10% 이하 → Z3 금지.
    """
    if hrv_today is None or hrv_rolling is None:
        return LEVEL_FULL, "HRV 데이터 없음 (통과)"
    if hrv_rolling <= 0:
        return LEVEL_FULL, "HRV rolling 평균 이상 (통과)"

    ratio = (hrv_today - hrv_rolling) / hrv_rolling  # 양수 = 오늘이 더 높음
    pct = ratio * 100

    if ratio < -0.15:
        return LEVEL_Z1, f"HRV {pct:+.1f}% — 회복 미완료 (Plews 2013: -15% 이하)"
    if ratio < -0.10:
        return LEVEL_Z1_Z2, f"HRV {pct:+.1f}% — 경계 (Plews 2013: -10% 기준)"
    return LEVEL_FULL, f"HRV {pct:+.1f}% — 정상 범위"


# ── Gate 3: Body Battery ──────────────────────────────────────────────────

def _gate_body_battery(bb: float | None) -> tuple[int, str]:
    """Garmin Body Battery → 허용 레벨."""
    if bb is None:
        return LEVEL_FULL, "Body Battery 데이터 없음 (통과)"
    if bb < 20:
        return LEVEL_REST, f"Body Battery {bb:.0f} < 20 — 휴식 필요"
    if bb < 35:
        return LEVEL_Z1, f"Body Battery {bb:.0f} < 35 — 이지런만 허용"
    if bb < 50:
        return LEVEL_Z1_Z2, f"Body Battery {bb:.0f} < 50 — 템포 이하"
    return LEVEL_FULL, f"Body Battery {bb:.0f} — 충분한 에너지"


# ── Gate 4: TSB (Coggan 2003 / Banister 1991) ─────────────────────────────

def _gate_tsb(tsb: float | None) -> tuple[int, str]:
    """TSB → 허용 레벨.

    Coggan 2003: TSB < -30 과훈련 위험 경계.
    Banister 1991: 퍼포먼스 = fitness - fatigue.
    """
    if tsb is None:
        return LEVEL_FULL, "TSB 데이터 없음 (통과)"
    if tsb < -30:
        return LEVEL_Z1, f"TSB {tsb:.1f} < -30 — 과훈련 경계 (Coggan 2003)"
    if tsb < -20:
        return LEVEL_Z1_Z2, f"TSB {tsb:.1f} < -20 — 누적 피로 주의"
    if tsb > 15:
        return LEVEL_FULL, f"TSB {tsb:.1f} > 15 — 레이스 준비 최적"
    return LEVEL_FULL, f"TSB {tsb:.1f} — 정상 훈련 상태"


# ── Gate 5: CIRS (내부 부상 위험 복합 점수) ───────────────────────────────

def _gate_cirs(cirs: float | None) -> tuple[int, str]:
    """CIRS > 80 → Z3 금지."""
    if cirs is None:
        return LEVEL_FULL, "CIRS 데이터 없음 (통과)"
    if cirs > 80:
        return LEVEL_Z1, f"CIRS {cirs:.0f} > 80 — 부상 위험 구간"
    if cirs > 50:
        return LEVEL_Z1_Z2, f"CIRS {cirs:.0f} > 50 — 경고 구간"
    return LEVEL_FULL, f"CIRS {cirs:.0f} — 안전 구간"


# ── CRS 참고 점수 ─────────────────────────────────────────────────────────

def _compute_crs_score(utrs: float | None, acwr: float | None,
                       cirs: float | None) -> float:
    """CRS 참고 점수 (0~100).

    UTRS 기반 + ACWR/CIRS 보정.
    주의: 가중치는 논문 미검증. ML session_outcomes 축적 후 보정 예정.
    현재는 게이트 필터가 실제 결정권, CRS는 참고/ML 피처용.
    """
    base = utrs if utrs is not None else 60.0  # 중립값

    # ACWR 보정: 위험 구간이면 감점
    if acwr is not None:
        if acwr > 1.5:
            base = min(base, 40.0)
        elif acwr > 1.3:
            base -= 10.0
        elif 1.0 <= acwr <= 1.3:
            base += 5.0  # 최적 구간 소폭 가점

    # CIRS 보정
    if cirs is not None:
        if cirs > 80:
            base = min(base, 35.0)
        elif cirs > 50:
            base -= 8.0

    return max(0.0, min(100.0, round(base, 1)))


# ── 메인 공개 함수 ────────────────────────────────────────────────────────

def evaluate(conn: sqlite3.Connection, target_date: str | None = None) -> dict:
    """훈련 준비도 평가.

    Args:
        conn: SQLite 연결.
        target_date: 평가 날짜 (ISO, 기본값: 오늘).

    Returns:
        {
            "level": int (0~4),
            "level_label": str,
            "crs": float (0~100, 참고용),
            "gates": [{"name", "level", "message"}, ...],
            "signals": {acwr, tsb, hrv, bb, cirs, utrs},
            "boost_allowed": bool,
        }
    """
    td = target_date or date.today().isoformat()

    # 신호 수집
    acwr = _get_metric(conn, "ACWR", td, days_back=3)
    tsb_row = conn.execute(
        "SELECT tsb FROM daily_fitness WHERE date<=? AND tsb IS NOT NULL "
        "ORDER BY date DESC LIMIT 1", (td,)
    ).fetchone()
    tsb = float(tsb_row[0]) if tsb_row else None

    hrv_today = _get_wellness(conn, "hrv_value", td, days_back=2)
    hrv_rolling = _get_hrv_rolling_avg(conn, td)
    bb = _get_wellness(conn, "body_battery", td, days_back=2)
    cirs = _get_metric(conn, "CIRS", td, days_back=7)
    utrs = _get_metric(conn, "UTRS", td, days_back=7)

    # 게이트 평가
    gates_raw = [
        ("ACWR",         *_gate_acwr(acwr)),
        ("HRV",          *_gate_hrv(hrv_today, hrv_rolling)),
        ("Body Battery", *_gate_body_battery(bb)),
        ("TSB",          *_gate_tsb(tsb)),
        ("CIRS",         *_gate_cirs(cirs)),
    ]
    gates = [{"name": g[0], "level": g[1], "message": g[2]} for g in gates_raw]

    # 최종 레벨 = 모든 게이트 중 최솟값
    min_level = min(g["level"] for g in gates)

    # CRS 참고 점수
    crs = _compute_crs_score(utrs, acwr, cirs)

    # BOOST 조건: 모든 게이트 FULL + CRS >= 80 + TSB > 5
    boost = (min_level == LEVEL_FULL and crs >= 80.0
             and tsb is not None and tsb > 5.0)
    final_level = LEVEL_BOOST if boost else min_level

    return {
        "level": final_level,
        "level_label": LEVEL_LABELS[final_level],
        "crs": crs,
        "gates": gates,
        "boost_allowed": boost,
        "signals": {
            "acwr": acwr,
            "tsb": tsb,
            "hrv_today": hrv_today,
            "hrv_rolling": hrv_rolling,
            "body_battery": bb,
            "cirs": cirs,
            "utrs": utrs,
        },
    }


def get_training_level(conn: sqlite3.Connection,
                       target_date: str | None = None) -> int:
    """훈련 레벨만 반환 (0~4). planner에서 단순 사용 시."""
    return evaluate(conn, target_date)["level"]
