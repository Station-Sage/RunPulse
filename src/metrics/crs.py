"""CRS (Composite Readiness Score) — 복합 훈련 준비도 평가.

게이트 필터 (논문 기반 hard rule) → 훈련 허용 강도 상한 결정.
CRS 참고 점수 (0~100) → UTRS 기반 + ACWR/CIRS 보정.

게이트:
  Gate 1: ACWR   — Gabbett 2016 (>1.5 위험)
  Gate 2: HRV    — Plews 2013 (rolling -10% 경계)
  Gate 3: Body Battery — Garmin (<20 휴식)
  Gate 4: TSB    — Coggan 2003 (<-30 과훈련)
  Gate 5: CIRS   — 내부 부상 위험 (>80 위험)

반환: level(0~4), crs(0~100), gates[], signals{}

evaluate(conn, target_date): 저장된 CRS 행을 읽는 읽기 전용 함수(계산하지 않음).
  replanner·matcher_context 가 사용. 행이 없거나 데이터가 손상됐으면 None.

v0.3 포팅: _v02_backup/crs.py → MetricCalculator 형식
"""
from __future__ import annotations

import json
import sqlite3
from datetime import date, timedelta
from src.metrics.base import MetricCalculator, CalcResult, CalcContext

# 훈련 레벨
LEVEL_REST = 0
LEVEL_Z1 = 1
LEVEL_Z1_Z2 = 2
LEVEL_FULL = 3
LEVEL_BOOST = 4

LEVEL_LABELS = {
    LEVEL_REST: "휴식",
    LEVEL_Z1: "이지런만",
    LEVEL_Z1_Z2: "템포 이하",
    LEVEL_FULL: "계획대로",
    LEVEL_BOOST: "볼륨 +5%",
}


# ── Gate 함수들 ──────────────────────────────────────────────────────

def _gate_acwr(acwr):
    if acwr is None:
        return LEVEL_FULL, "ACWR 데이터 없음 (통과)"
    if acwr > 1.5:
        return LEVEL_Z1, f"ACWR {acwr:.2f} > 1.5 — 부상 위험"
    if acwr > 1.3:
        return LEVEL_Z1_Z2, f"ACWR {acwr:.2f} > 1.3 — 주의"
    if acwr < 0.8:
        return LEVEL_FULL, f"ACWR {acwr:.2f} < 0.8 — 훈련 부족"
    return LEVEL_FULL, f"ACWR {acwr:.2f} — 최적"


def _gate_hrv(hrv_today, hrv_rolling):
    if hrv_today is None or hrv_rolling is None or hrv_rolling <= 0:
        return LEVEL_FULL, "HRV 데이터 없음 (통과)"
    ratio = (hrv_today - hrv_rolling) / hrv_rolling
    pct = ratio * 100
    if ratio < -0.15:
        return LEVEL_Z1, f"HRV {pct:+.1f}% — 회복 미완료"
    if ratio < -0.10:
        return LEVEL_Z1_Z2, f"HRV {pct:+.1f}% — 경계"
    return LEVEL_FULL, f"HRV {pct:+.1f}% — 정상"


def _gate_body_battery(bb):
    if bb is None:
        return LEVEL_FULL, "Body Battery 없음 (통과)"
    if bb < 20:
        return LEVEL_REST, f"BB {bb:.0f} < 20 — 휴식"
    if bb < 35:
        return LEVEL_Z1, f"BB {bb:.0f} < 35 — 이지런만"
    if bb < 50:
        return LEVEL_Z1_Z2, f"BB {bb:.0f} < 50 — 템포 이하"
    return LEVEL_FULL, f"BB {bb:.0f} — 충분"


def _gate_tsb(tsb):
    if tsb is None:
        return LEVEL_FULL, "TSB 없음 (통과)"
    if tsb < -30:
        return LEVEL_Z1, f"TSB {tsb:.1f} < -30 — 과훈련 경계"
    if tsb < -20:
        return LEVEL_Z1_Z2, f"TSB {tsb:.1f} < -20 — 피로 주의"
    return LEVEL_FULL, f"TSB {tsb:.1f} — 정상"


def _gate_cirs(cirs):
    if cirs is None:
        return LEVEL_FULL, "CIRS 없음 (통과)"
    if cirs > 80:
        return LEVEL_Z1, f"CIRS {cirs:.0f} > 80 — 부상 위험"
    if cirs > 50:
        return LEVEL_Z1_Z2, f"CIRS {cirs:.0f} > 50 — 경고"
    return LEVEL_FULL, f"CIRS {cirs:.0f} — 안전"


def _compute_crs_score(utrs, acwr, cirs):
    base = utrs if utrs is not None else 60.0
    if acwr is not None:
        if acwr > 1.5:
            base = min(base, 40.0)
        elif acwr > 1.3:
            base -= 10.0
        elif 1.0 <= acwr <= 1.3:
            base += 5.0
    if cirs is not None:
        if cirs > 80:
            base = min(base, 35.0)
        elif cirs > 50:
            base -= 8.0
    return max(0.0, min(100.0, round(base, 1)))


class CRSCalculator(MetricCalculator):
    name = "crs"
    provider = "runpulse:formula_v1"
    version = "1.0"
    scope_type = "daily"
    category = "readiness"
    requires = ["acwr", "tsb", "cirs", "utrs"]
    produces = ["crs"]

    display_name = "CRS (훈련 준비도)"
    description = "게이트 기반 복합 준비도. level 0~4 + CRS 참고 점수 0~100."
    unit = ""
    ranges = {"rest": [0, 20], "easy_only": [20, 40], "moderate": [40, 60], "full": [60, 80], "boost": [80, 100]}
    higher_is_better = True
    format_type = "json"
    decimal_places = 1

    def compute(self, ctx: CalcContext) -> list[CalcResult]:
        # NOTE: raw SQL 사용 — CalcContext API가 activity_type별 metric JOIN을 미지원
        # 신호 수집
        acwr = ctx.get_metric("acwr", provider="runpulse:formula_v1")
        acwr = float(acwr) if acwr is not None else None

        tsb = ctx.get_metric("tsb", provider="runpulse:formula_v1")
        tsb = float(tsb) if tsb is not None else None

        cirs = ctx.get_metric("cirs", provider="runpulse:formula_v1")
        cirs = float(cirs) if cirs is not None else None

        utrs = ctx.get_metric("utrs", provider="runpulse:formula_v1")
        utrs = float(utrs) if utrs is not None else None

        # 웰니스
        wellness = ctx.get_wellness()
        bb = None
        hrv_today = None
        if wellness:
            bb_val = wellness.get("body_battery_high")
            bb = float(bb_val) if bb_val is not None else None
            hrv_val = wellness.get("hrv_weekly_avg")
            hrv_today = float(hrv_val) if hrv_val is not None else None

        # HRV rolling (최근 7일)
        hrv_rolling = None
        if hrv_today is not None:
            td = date.fromisoformat(ctx.scope_id)
            since = (td - timedelta(days=7)).isoformat()
            wellness_hist = ctx.get_wellness_series(days=7, fields=["hrv_weekly_avg"])
            vals = [float(w["hrv_weekly_avg"]) for w in wellness_hist
                    if w.get("hrv_weekly_avg") is not None]
            hrv_rolling = sum(vals) / len(vals) if vals else None

        # 게이트 평가
        gates_raw = [
            ("ACWR", *_gate_acwr(acwr)),
            ("HRV", *_gate_hrv(hrv_today, hrv_rolling)),
            ("Body Battery", *_gate_body_battery(bb)),
            ("TSB", *_gate_tsb(tsb)),
            ("CIRS", *_gate_cirs(cirs)),
        ]
        gates = [{"name": g[0], "level": g[1], "message": g[2]} for g in gates_raw]
        min_level = min(g["level"] for g in gates)

        # CRS 점수
        crs_score = _compute_crs_score(utrs, acwr, cirs)

        # BOOST 판정
        boost = (min_level == LEVEL_FULL and crs_score >= 80.0
                 and tsb is not None and tsb > 5.0)
        final_level = LEVEL_BOOST if boost else min_level

        return [self._result(
            value=crs_score,
            text=LEVEL_LABELS[final_level],
            json_val={
                "level": final_level,
                "level_label": LEVEL_LABELS[final_level],
                "crs": crs_score,
                "gates": gates,
                "boost_allowed": boost,
                "signals": {
                    "acwr": acwr,
                    "tsb": tsb,
                    "body_battery": bb,
                    "hrv_today": hrv_today,
                    "hrv_rolling": round(hrv_rolling, 1) if hrv_rolling else None,
                    "cirs": cirs,
                    "utrs": utrs,
                },
            },
        
            confidence=1.0,
        )]


# ── 저장된 CRS 읽기 (읽기 전용) ───────────────────────────────────────

def _is_number(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def evaluate(conn: sqlite3.Connection, target_date: str) -> dict | None:
    """target_date(ISO) 하루의 저장된 CRS(is_primary=1)를 읽어 반환한다. 계산·쓰기 없음.

    정확히 그 날짜의 행만 읽는다(이전 날짜 행으로 대체하지 않음 — 오래된 값이
    그날 값처럼 쓰이는 것을 막는다). 같은 날짜에 대표 행이 여럿이면 id 가 큰 쪽.

    Returns:
        {"level": int 0~4, "level_label": str, "crs": float | None,
         "gates": list, "signals": dict, "boost_allowed": bool}
        행이 없거나 json_value 가 손상됐거나 level 이 유효하지 않으면 None.

    DB 오류(테이블 없음 등)는 잡지 않고 그대로 전파한다.
    """
    row = conn.execute(
        "SELECT json_value FROM metric_store "
        "WHERE scope_type='daily' AND scope_id=? AND metric_name='crs' "
        "AND is_primary=1 AND json_value IS NOT NULL ORDER BY id DESC LIMIT 1",
        (target_date,),
    ).fetchone()
    if row is None:
        return None
    try:
        data = json.loads(row[0])
    except (TypeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    level = data.get("level")
    if not isinstance(level, int) or isinstance(level, bool) or level not in LEVEL_LABELS:
        return None
    label = data.get("level_label")
    gates = data.get("gates")
    signals = data.get("signals")
    return {
        "level": level,
        "level_label": label if isinstance(label, str) and label else LEVEL_LABELS[level],
        "crs": data["crs"] if _is_number(data.get("crs")) else None,
        "gates": gates if isinstance(gates, list) else [],
        "signals": signals if isinstance(signals, dict) else {},
        "boost_allowed": data.get("boost_allowed") is True,
    }
