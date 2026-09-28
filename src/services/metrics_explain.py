"""Phase 7 UX 리뷰 2-5 — 메트릭 분해 v2(`explain=1`, §C3.2).

99-summary.md §7 로드맵 2-5, 10-today/design.md §7(API 계약)·§9 S2 참조.
설계가 값 채우기를 못박은 4개(TSB·CTL·ATL·UTRS)에 더해, 같은 가중 합성
구조(`parent_metric_id` 자식 행 + WEIGHTS)를 가진 CIRS도 지원한다(2026-09-28
사용자 확인 "다른 지표들도"). 그 외 슬러그는 None을 반환하고 라우트가 기존
v1(`metrics_service.get_metric_breakdown`)로 폴백한다.

**확장 시 주의**: RRI·VDOT 등은 곱셈형 공식이라 UTRS/CIRS식 가중치 분해가
맞지 않고(요인이 metric_store 자식 행이 아니라 json_value에만 있음),
"meaning.what/so_what" 카피는 registry(`metric_registry.py`)에 영문
약어 설명만 있어 실제 사용자向 문구는 직접 작성이 필요하다 — 추가할 때마다
이 트레이드오프를 확인할 것. CIRS는 S7에서 개인 기준선 재설계 예정이라
이 explainer는 현재 v1 공식 기준이고 S7 착수 시 갱신 필요.

sources(원천 활동)는 최근 14일 내 TRIMP 상위 3개 활동으로 근사한다 — CTL은
252일 창 EMA라 정확한 기여도 배분은 하지 않는다(과설계 방지, 코멘트로 명시).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from src.metrics.bands import BANDS, grade
from src.metrics.cirs import CIRSCalculator
from src.metrics.utrs import UTRSCalculator
from src.services.metrics_service import _metric_label, _metric_unit
from src.utils.db_helpers import get_primary_metric

_PMC_ALPHA = {"ctl": 1.0 / 42, "atl": 1.0 / 7}
_PMC_LABEL = {"ctl": "체력", "atl": "피로"}
_HIGHER_IS_BETTER = {"tsb": True, "ctl": None, "atl": None, "utrs": True, "cirs": False}

_WHAT = {
    "tsb": "폼(TSB)은 최근 체력(CTL)과 피로(ATL)의 차이로, 지금 몸이 훈련을 받아들일 준비가 됐는지를 보여줍니다.",
    "ctl": "체력(CTL)은 최근 42일간 훈련 부하가 누적된 값입니다.",
    "atl": "피로(ATL)는 최근 7일간 훈련 부하를 반영한 값입니다.",
    "utrs": "훈련 준비도(UTRS)는 바디 배터리·폼·수면·심박변이·스트레스를 종합한 점수입니다.",
    "cirs": "부상 위험 지수(CIRS)는 급성:만성 부하비·부하 급증·연속 훈련일·피로를 종합한 위험 추정치입니다.",
}
_SO_WHAT = {
    "tsb": {
        "poor": "휴식이 필요해요.",
        "caution": "강도 높은 훈련은 피하세요.",
        "neutral": "지금 강도를 유지해도 좋아요.",
        "good": "훈련 효과가 잘 쌓이고 있어요.",
        "excellent": "몸이 가벼운 상태 — 중요한 세션이나 레이스에 적합해요.",
    },
    "utrs": {
        "poor": "오늘은 쉬는 게 좋아요.",
        "caution": "가벼운 훈련만 권장해요.",
        "neutral": "계획대로 진행해도 좋아요.",
        "good": "컨디션이 좋아요 — 계획된 훈련을 소화하세요.",
        "excellent": "컨디션이 훌륭해요 — 강도 높은 세션도 가능해요.",
    },
    "cirs": {
        "poor": "부상 위험이 매우 높아요 — 강도·볼륨을 줄이고 회복에 집중하세요.",
        "caution": "부상 위험이 높은 편이에요 — 급격한 부하 증가는 피하세요.",
        "neutral": "부상 위험이 보통이에요 — 평소 관리대로 진행하세요.",
        "good": "부상 위험이 낮아요.",
    },
}


def _bands_v2(metric_name: str) -> list[dict]:
    """`bands.py` BANDS → API 계약 `bands[{max,status,label}]`(마지막 구간은 max=None)."""
    band = BANDS.get(metric_name)
    if band is None:
        return []
    cuts, last = band
    out = [{"max": upper, "status": s, "label": lab} for upper, s, lab in cuts]
    out.append({"max": None, "status": last[0], "label": last[1]})
    return out


def _baseline(conn: sqlite3.Connection, scope_type: str, scope_id: str, metric_name: str) -> dict:
    """최근 7일 평균·전일 대비 변화(일별 scope 전제)."""
    rows = conn.execute(
        "SELECT scope_id, numeric_value FROM metric_store "
        "WHERE scope_type=? AND metric_name=? AND is_primary=1 "
        "AND scope_id<=? AND scope_id>date(?, '-8 days') ORDER BY scope_id",
        (scope_type, metric_name, scope_id, scope_id),
    ).fetchall()
    vals = [r[1] for r in rows if r[1] is not None]
    if not vals:
        return {"avg_7d": None, "delta_1d": None}
    delta = round(vals[-1] - vals[-2], 2) if len(vals) >= 2 else None
    return {"avg_7d": round(sum(vals) / len(vals), 2), "delta_1d": delta}


def _daily_trimp_sum(conn: sqlite3.Connection, date_str: str) -> float:
    """그날 활동들의 TRIMP 합 — `CalcContext.get_daily_load()` 폴백 쿼리와 동일 패턴."""
    rows = conn.execute(
        "SELECT m.numeric_value FROM metric_store m "
        "JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER)=a.id "
        "WHERE m.scope_type='activity' AND m.metric_name='trimp' AND m.is_primary=1 "
        "AND substr(a.start_time,1,10)=?",
        (date_str,),
    ).fetchall()
    return sum(r[0] or 0 for r in rows)


def _top_activity_sources(conn: sqlite3.Connection, scope_id: str, window_days: int = 14, limit: int = 3) -> list[dict]:
    """최근 window_days 내 TRIMP 상위 활동(근사 — 정확한 EMA 기여 배분 아님)."""
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT a.id, a.name, m.numeric_value AS trimp FROM metric_store m "
        "JOIN v_canonical_activities a ON CAST(m.scope_id AS INTEGER)=a.id "
        "WHERE m.scope_type='activity' AND m.metric_name='trimp' AND m.is_primary=1 "
        "AND substr(a.start_time,1,10)<=? AND substr(a.start_time,1,10)>date(?, ?) "
        "ORDER BY m.numeric_value DESC LIMIT ?",
        (scope_id, scope_id, f"-{window_days} days", limit),
    ).fetchall()
    return [
        {
            "type": "activity",
            "id": r["id"],
            "label": r["name"] or "활동",
            "value": round(r["trimp"], 1) if r["trimp"] is not None else None,
            "unit": "TRIMP",
            "effect": f"부하 +{round(r['trimp'], 1)}" if r["trimp"] is not None else "",
        }
        for r in rows
    ]


def _explain_tsb(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
    ctl_row = get_primary_metric(conn, scope_type, scope_id, "ctl")
    atl_row = get_primary_metric(conn, scope_type, scope_id, "atl")
    terms = []
    if ctl_row and ctl_row.get("numeric_value") is not None:
        v = ctl_row["numeric_value"]
        terms.append({"slug": "ctl", "label": "체력", "raw": v, "sign": "+", "contribution": v, "drill": "m.ctl"})
    if atl_row and atl_row.get("numeric_value") is not None:
        v = atl_row["numeric_value"]
        terms.append({"slug": "atl", "label": "피로", "raw": v, "sign": "-", "contribution": -v, "drill": "m.atl"})
    return terms, _top_activity_sources(conn, scope_id), "폼 = 체력(CTL) − 피로(ATL)"


def _explain_pmc(conn: sqlite3.Connection, scope_type: str, scope_id: str, slug: str) -> tuple[list[dict], list[dict], str]:
    alpha = _PMC_ALPHA[slug]
    yesterday = (datetime.strptime(scope_id, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_row = get_primary_metric(conn, scope_type, yesterday, slug)
    prev_value = prev_row["numeric_value"] if prev_row and prev_row.get("numeric_value") is not None else 0.0
    today_load = _daily_trimp_sum(conn, scope_id)
    terms = [
        {
            "slug": f"{slug}_prev", "label": f"어제 {_PMC_LABEL[slug]}", "raw": round(prev_value, 1),
            "weight": round(1 - alpha, 4), "contribution": round(prev_value * (1 - alpha), 1),
        },
        {
            "slug": "trimp_today", "label": "오늘 부하", "raw": round(today_load, 1),
            "weight": round(alpha, 4), "contribution": round(today_load * alpha, 1), "drill": "m.trimp",
        },
    ]
    days = round(1 / alpha)
    text = f"{_PMC_LABEL[slug]} = 어제 {_PMC_LABEL[slug]} × (1 − 1/{days}) + 오늘 부하 × (1/{days})"
    return terms, _top_activity_sources(conn, scope_id), text


_UTRS_CHILD_LABEL = {
    "utrs_body_battery": ("바디 배터리", "body_battery"),
    "utrs_tsb": ("폼", "tsb"),
    "utrs_sleep": ("수면", "sleep"),
    "utrs_hrv": ("심박변이(HRV)", "hrv"),
    "utrs_stress": ("스트레스", "stress"),
}


def _explain_utrs(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
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
            "loss": round(w * (100 - value), 1),
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


def _explain_cirs(conn: sqlite3.Connection, scope_type: str, scope_id: str) -> tuple[list[dict], list[dict], str]:
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
    return terms, _top_activity_sources(conn, scope_id), "부상 위험 = Σ(위험 점수 × 가중치) / Σ가중치(가용 항목만)"


_EXPLAINERS = {
    "tsb": lambda conn, st, sid: _explain_tsb(conn, st, sid),
    "ctl": lambda conn, st, sid: _explain_pmc(conn, st, sid, "ctl"),
    "atl": lambda conn, st, sid: _explain_pmc(conn, st, sid, "atl"),
    "utrs": lambda conn, st, sid: _explain_utrs(conn, st, sid),
    "cirs": lambda conn, st, sid: _explain_cirs(conn, st, sid),
}


def get_metric_explain(conn: sqlite3.Connection, scope_type: str, scope_id: str, slug: str) -> dict | None:
    """분해 v2(§C3.2) — TSB/CTL/ATL/UTRS만 지원, 그 외는 None(라우트가 v1로 폴백)."""
    builder = _EXPLAINERS.get(slug)
    if builder is None:
        return None
    self_row = get_primary_metric(conn, scope_type, scope_id, slug)
    if self_row is None:
        return None

    terms, sources, formula_text = builder(conn, scope_type, scope_id)
    value = self_row.get("numeric_value")
    band = grade(slug, value)

    return {
        "slug": slug,
        "name_ko": _metric_label(slug),
        "abbr": slug.upper(),
        "scope": {"type": scope_type, "id": scope_id, "basis": "morning"},
        "value": value,
        "display": value,
        "unit": _metric_unit(slug),
        "status": band["status"] if band else None,
        "status_label": band["label"] if band else None,
        "higher_is_better": _HIGHER_IS_BETTER.get(slug),
        "meaning": {
            "what": _WHAT.get(slug, ""),
            "bands": _bands_v2(slug),
            "baseline": _baseline(conn, scope_type, scope_id, slug),
            "so_what": _SO_WHAT.get(slug, {}).get(band["status"] if band else "", ""),
        },
        "formula": {
            "text": formula_text,
            "version": self_row.get("algorithm_version", ""),
            "computed_at": self_row.get("updated_at", ""),
            "terms": terms,
        },
        "sources": sources,
        "provider": {
            "kind": "runpulse_calc",
            "version": self_row.get("algorithm_version", ""),
            "computed_at": self_row.get("updated_at", ""),
        },
        "compare": [],
        "links": {"trend": f"/library/metrics/{slug}"},
    }
