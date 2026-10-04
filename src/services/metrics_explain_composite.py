"""분해 v2 — 합성형(UTRS·CIRS) + 곱셈형(RRI) explainer.

`metrics_explain.py`(TSB/CTL/ATL)에서 파일당 300줄 규칙 때문에 분리했다.
UTRS/CIRS는 `parent_metric_id` 자식 행 + `WEIGHTS` dict 구조가 같아 같은
가중 평균 패턴을 쓰고, RRI는 곱셈형이라 별도 표현(`role="factor"`)을 쓴다
(2026-09-28 사용자 확인 "다른 지표들도"·"너무 최소한만" — CIRS·RRI 추가).
"""
from __future__ import annotations

import json
import sqlite3

from src.metrics.cirs import CIRSCalculator
from src.metrics.utrs import UTRSCalculator
from src.services.metrics_explain_shared import top_activity_sources
from src.services.metrics_service import _metric_label, _metric_unit
from src.utils.db_helpers import get_primary_metric

_UTRS_CHILD_LABEL = {
    "utrs_body_battery": ("바디 배터리", "body_battery"),
    "utrs_tsb": ("폼", "tsb"),
    "utrs_sleep": ("수면", "sleep"),
    "utrs_hrv": ("심박변이(HRV)", "hrv"),
    "utrs_stress": ("스트레스", "stress"),
}

# 입력 항목 → 추세 보기용 원천 지표(웰니스 컬럼 또는 daily 메트릭). 없으면 drill 생략
_UTRS_CHILD_DRILL = {
    "utrs_body_battery": "m.body_battery_high",
    "utrs_tsb": "m.tsb",
    "utrs_sleep": "m.sleep_score",
    "utrs_hrv": "m.hrv_weekly_avg",
    "utrs_stress": "m.avg_stress",
}


def explain_utrs(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
    self_row = get_primary_metric(conn, scope_type, scope_id, "utrs")
    self_id = self_row["id"] if self_row else None
    conn.row_factory = sqlite3.Row
    child_rows = conn.execute(
        "SELECT metric_name, numeric_value FROM metric_store "
        "WHERE scope_type=? AND scope_id=? AND parent_metric_id=? ORDER BY id",
        (scope_type, str(scope_id), self_id),
    ).fetchall()
    weights = UTRSCalculator.WEIGHTS
    present = [(r["metric_name"], r["numeric_value"]) for r in child_rows if r["metric_name"] in _UTRS_CHILD_LABEL]
    total_weight = sum(weights[_UTRS_CHILD_LABEL[name][1]] for name, _ in present) or 1.0
    terms = []
    for name, value in present:
        label, key = _UTRS_CHILD_LABEL[name]
        w = weights[key] / total_weight
        terms.append({
            "slug": name, "label": label, "raw": value, "normalized": value,
            "weight": round(w, 4), "contribution": round(w * value, 1),
            "loss": round(w * (100 - value), 1), "drill": _UTRS_CHILD_DRILL[name],
        })
    terms.sort(key=lambda t: t["loss"], reverse=True)
    sources = [{
        "type": "wellness_day", "date": scope_id, "label": "웰니스 기록",
        "value": None, "unit": "", "effect": f"입력 {len(present)}개 반영",
    }]
    return terms, sources, "준비도 = Σ(정규화값 × 가중치) / Σ가중치(가용 항목만)"


_CIRS_CHILD_LABEL = {
    "cirs_acwr": ("ACWR 편차", "acwr"),
    "cirs_lsi": ("부하 스파이크(LSI)", "lsi"),
    "cirs_consecutive": ("연속 훈련일", "consecutive"),
    "cirs_fatigue": ("피로(CTL−ATL)", "fatigue"),
}


def explain_cirs(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
    """CIRS는 UTRS와 동일한 가중 합성 구조지만 위험 점수라 `loss` 없이 `contribution` 자체가 위험 기여분이다.

    현재 v1 공식(ACWR·LSI·연속일·피로) 기준 — S7 CIRS v2(개인 기준선 재설계) 시 이 explainer도 갱신 필요.
    """
    self_row = get_primary_metric(conn, scope_type, scope_id, "cirs")
    self_id = self_row["id"] if self_row else None
    conn.row_factory = sqlite3.Row
    child_rows = conn.execute(
        "SELECT metric_name, numeric_value FROM metric_store "
        "WHERE scope_type=? AND scope_id=? AND parent_metric_id=? ORDER BY id",
        (scope_type, str(scope_id), self_id),
    ).fetchall()
    weights = CIRSCalculator.WEIGHTS
    present = [(r["metric_name"], r["numeric_value"]) for r in child_rows if r["metric_name"] in _CIRS_CHILD_LABEL]
    total_weight = sum(weights[_CIRS_CHILD_LABEL[name][1]] for name, _ in present) or 1.0
    terms = []
    for name, value in present:
        label, key = _CIRS_CHILD_LABEL[name]
        w = weights[key] / total_weight
        terms.append({
            "slug": name, "label": label, "raw": value, "normalized": value,
            "weight": round(w, 4), "contribution": round(w * value, 1),
        })
    terms.sort(key=lambda t: t["contribution"], reverse=True)
    return terms, top_activity_sources(conn, scope_id), "부상 위험 = Σ(위험 점수 × 가중치) / Σ가중치(가용 항목만)"


_RRI_SOURCE_SLUG = {"vdot": "race_pred_vdot", "ctl": "ctl", "di": "di", "cirs": "cirs"}


def explain_rri(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
    """RRI는 곱셈형 공식(요인이 `metric_store` 자식 행이 아니라 `json_value`에만 있음)이라
    UTRS/CIRS의 가중치 분해가 아니라 요인별 비율(role="factor")로 표현한다.
    """
    self_row = get_primary_metric(conn, scope_type, scope_id, "rri")
    factors = json.loads(self_row["json_value"]) if self_row and self_row.get("json_value") else {}

    terms = []
    vdot, vdot_target = factors.get("vdot"), factors.get("vdot_target")
    if vdot is not None and vdot_target:
        terms.append({
            "slug": "vdot_pct", "label": "예측 기록 진행률", "raw": vdot, "target": vdot_target,
            "ratio": round(min(1.0, vdot / vdot_target), 3), "role": "factor",
        })
    ctl, target_ctl = factors.get("ctl"), factors.get("target_ctl")
    if ctl is not None and target_ctl:
        terms.append({
            "slug": "ctl_pct", "label": "체력(CTL) 충족률", "raw": ctl, "target": target_ctl,
            "ratio": round(min(1.0, ctl / target_ctl), 3), "role": "factor",
        })
    di = factors.get("di")
    terms.append({
        "slug": "di_factor", "label": "훈련 강도 분포(DI)", "raw": di,
        "ratio": round(min(1.0, (di if di is not None else 50) / 70), 3), "role": "factor",
    })
    cirs = factors.get("cirs")
    terms.append({
        "slug": "safety", "label": "부상 위험 안전계수", "raw": cirs,
        "ratio": round((100 - min(100, cirs if cirs is not None else 0)) / 100, 3), "role": "factor",
    })

    sources = [
        {"type": "metric", "slug": slug, "label": _metric_label(slug), "value": factors.get(key), "unit": _metric_unit(slug), "effect": ""}
        for key, slug in _RRI_SOURCE_SLUG.items() if factors.get(key) is not None
    ]
    return terms, sources, "RRI = 예측 기록 진행률 × 체력 충족률 × DI계수 × 안전계수 × 100"
