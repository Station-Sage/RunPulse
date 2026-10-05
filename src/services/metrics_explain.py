"""Phase 7 UX 리뷰 2-5 — 메트릭 분해 v2(`explain=1`, §C3.2).

99-summary.md §7 로드맵 2-5, 10-today/design.md §7(API 계약)·§9 S2 참조.
설계가 값 채우기를 못박은 4개(TSB·CTL·ATL·UTRS)에 더해, 같은 가중 합성
구조(`parent_metric_id` 자식 행 + WEIGHTS)를 가진 CIRS와, 곱셈형 공식이라
별도 표현(`role="factor"`)이 필요한 RRI도 지원한다(2026-09-28 사용자 확인
"다른 지표들도"·"너무 최소한만"). UTRS/CIRS/RRI explainer는 파일당 300줄
규칙 때문에 `metrics_explain_composite.py`로 분리했다. 그 외 슬러그는
None을 반환하고 라우트가 기존 v1(`metrics_service.get_metric_breakdown`)로
폴백한다. 활동 범위(`scope_type=activity`, 드릴 토큰 `@a{id}`)는
`metrics_explain_activity.py`의 TRIMP만 지원한다.

**terms 형태가 메트릭 종류마다 다르다**: TSB/CTL/ATL은 `sign`+`contribution`
(합), UTRS/CIRS는 `weight`+`contribution`(가중 평균), RRI는 `ratio`+`role`
(곱). 프론트 DrillPanel이 아직 이 API를 안 쓰므로 지금은 백엔드 표현만
확정 — 실제 렌더 규격은 프론트 재작성 라운드에서 좁혀야 한다.

**추가 확장 시 주의**: VDOT 등 더 있는 메트릭도, "meaning.what/so_what"
카피는 registry(`metric_registry.py`)에 영문 약어 설명만 있어 실제
사용자向 문구는 매번 직접 작성이 필요하다. CIRS는 S7에서 개인 기준선
재설계 예정이라 이 explainer는 현재 v1 공식 기준이고 S7 착수 시 갱신 필요.

sources(원천 활동)는 최근 14일 내 TRIMP 상위 3개 활동으로 근사한다 — CTL은
252일 창 EMA라 정확한 기여도 배분은 하지 않는다(과설계 방지, 코멘트로 명시).
"""
from __future__ import annotations

import sqlite3
from datetime import datetime, timedelta

from src.metrics.bands import BANDS, grade
from src.services.metric_display import HIGHER_IS_BETTER, display_name
from src.services.metrics_explain_activity import explain_trimp_activity
from src.services.metrics_explain_conclusion import build_conclusion
from src.services.metrics_explain_composite import explain_cirs, explain_rri, explain_utrs
from src.services.metrics_explain_prediction import explain_prediction
from src.services.metrics_explain_shared import daily_trimp_sum, top_activity_sources
from src.services.metrics_service import _metric_label, _metric_unit
from src.utils.db_helpers import get_primary_metric
from src.utils.metric_labels import label_for

_PMC_ALPHA = {"ctl": 1.0 / 42, "atl": 1.0 / 7}
_PMC_LABEL = {"ctl": "체력", "atl": "피로"}
_HIGHER_IS_BETTER = HIGHER_IS_BETTER

_WHAT = {
    "tsb": "폼(TSB)은 최근 체력(CTL)과 피로(ATL)의 차이로, 지금 몸이 훈련을 받아들일 준비가 됐는지를 보여줍니다.",
    "ctl": "체력(CTL)은 최근 42일간 훈련 부하가 누적된 값입니다.",
    "atl": "피로(ATL)는 최근 7일간 훈련 부하를 반영한 값입니다.",
    "utrs": "훈련 준비도(UTRS)는 바디 배터리·폼·수면·심박변이·스트레스를 종합한 점수입니다.",
    "cirs": "부상 위험 지수(CIRS)는 급성:만성 부하비·부하 급증·연속 훈련일·피로를 종합한 위험 추정치입니다.",
    "trimp": "TRIMP는 운동 시간과 심박 강도를 합쳐 이 활동이 몸에 준 부하를 한 숫자로 나타낸 값입니다.",
    "rri": "레이스 준비도(RRI)는 예측 기록 진행률·체력(CTL) 충족률·훈련 강도 분포·부상 위험을 곱해 레이스 준비 정도를 나타냅니다.",
    **{k: f"{d} 예측 기록은 대회 기록·훈련 강도·심박-페이스 신호를 가중 결합해 기온 15°C 기준으로 환산한 값입니다."
       for k, d in (("race_pred_5k_sec", "5K"), ("race_pred_10k_sec", "10K"), ("race_pred_half_sec", "하프"),
                    ("race_pred_marathon_sec", "마라톤"))},
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
    return {"avg_7d": round(sum(vals) / len(vals), 2), "delta_1d": delta, "avg_90d": _avg_90d(conn, scope_type, scope_id, metric_name)}


def _avg_90d(conn: sqlite3.Connection, scope_type: str, scope_id: str, metric_name: str) -> float | None:
    """최근 90일 평균. 표본 14개 미만이면 None."""
    row = conn.execute(
        "SELECT AVG(numeric_value), COUNT(numeric_value) FROM metric_store "
        "WHERE scope_type=? AND metric_name=? AND is_primary=1 "
        "AND scope_id<=? AND scope_id>date(?, '-90 days')",
        (scope_type, metric_name, scope_id, scope_id),
    ).fetchone()
    return round(row[0], 2) if row and row[1] >= 14 else None


def personal_text(value: float | None, status_label: str | None, avg_90d: float | None) -> str | None:
    """'지금 {값} — {등급}. 90일 평균 {mean}보다 {높음/낮음}' (A-7)."""
    if value is None or avg_90d is None:
        return None
    rel = "높아요" if value > avg_90d else "낮아요" if value < avg_90d else "같아요"
    head = f"지금 {value:g}" + (f" — {status_label}" if status_label else "")
    return f"{head}. 90일 평균 {avg_90d:g}보다 {rel}" if rel != "같아요" else f"{head}. 90일 평균 {avg_90d:g}과 같아요"


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
    return terms, top_activity_sources(conn, scope_id), "폼 = 체력(CTL) − 피로(ATL)"


def _explain_pmc(conn: sqlite3.Connection, scope_type: str, scope_id: str, slug: str) -> tuple[list[dict], list[dict], str]:
    alpha = _PMC_ALPHA[slug]
    yesterday = (datetime.strptime(scope_id, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
    prev_row = get_primary_metric(conn, scope_type, yesterday, slug)
    prev_value = prev_row["numeric_value"] if prev_row and prev_row.get("numeric_value") is not None else 0.0
    today_load = daily_trimp_sum(conn, scope_id)
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
    return terms, top_activity_sources(conn, scope_id), text


_EXPLAINERS = {
    "tsb": lambda conn, st, sid: _explain_tsb(conn, st, sid),
    "ctl": lambda conn, st, sid: _explain_pmc(conn, st, sid, "ctl"),
    "atl": lambda conn, st, sid: _explain_pmc(conn, st, sid, "atl"),
    "utrs": lambda conn, st, sid: explain_utrs(conn, st, sid),
    "cirs": lambda conn, st, sid: explain_cirs(conn, st, sid),
    "rri": lambda conn, st, sid: explain_rri(conn, st, sid),
    **{s: (lambda conn, st, sid, _s=s: explain_prediction(conn, st, sid, _s))
       for s in ("race_pred_5k_sec", "race_pred_10k_sec", "race_pred_half_sec", "race_pred_marathon_sec")},
}
_ACTIVITY_EXPLAINERS = {"trimp": explain_trimp_activity}


def get_metric_explain(conn: sqlite3.Connection, scope_type: str, scope_id: str, slug: str) -> dict | None:
    """분해 v2(§C3.2) — TSB/CTL/ATL/UTRS/CIRS/RRI만 지원, 그 외는 None(라우트가 v1로 폴백)."""
    builder = (_ACTIVITY_EXPLAINERS if scope_type == "activity" else _EXPLAINERS).get(slug)
    if builder is None:
        return None
    self_row = get_primary_metric(conn, scope_type, scope_id, slug)
    if self_row is None:
        return None

    built = builder(conn, scope_type, scope_id)
    terms, sources, formula_text = built[:3]
    evidence = built[3] if len(built) > 3 else None
    if scope_type == "activity" and not terms:
        return None
    base = _baseline(conn, scope_type, scope_id, slug) if scope_type != "activity" else None
    conclusion = build_conclusion(slug, terms) if scope_type != "activity" else None
    value = self_row.get("numeric_value")
    band = grade(slug, value)
    name_ko, abbr = display_name(slug, _metric_label(slug))

    return {
        "slug": slug,
        "name_ko": name_ko,
        "abbr": abbr,
        "scope": {"type": scope_type, "id": scope_id, "basis": "activity" if scope_type == "activity" else "morning"},
        "value": value,
        "display": value,
        "unit": _metric_unit(slug),
        "status": band["status"] if band else None,
        "status_label": band["label"] if band else None,
        "higher_is_better": _HIGHER_IS_BETTER.get(slug),
        "meaning": {
            "what": _WHAT.get(slug) or label_for(slug).description_short or "",
            "bands": _bands_v2(slug),
            "baseline": base or {"avg_7d": None, "delta_1d": None},
            "personal": personal_text(value, band["label"] if band else None, base["avg_90d"]) if base else None,
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
        **({"evidence": evidence} if evidence else {}),
        **({"conclusion": conclusion} if conclusion else {}),
    }
