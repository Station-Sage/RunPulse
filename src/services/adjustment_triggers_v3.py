"""adjuster_v3 트리거 판정 (ADR-035 개정, ADJ) — 신호 목록 → 단독 OR / 2개 이상 AND 판정. 순수 함수(DB 접근 없음).

단독(OR): 통증 기록, 체크인 통증 moderate/severe, 확정 질병, 확정 부상(진행 중 + 종료 후 복귀 구간, ADR-058). AND(2개 이상): CRS level<=1, ACWR>=1.5, 체크인 피로>=7.
1개만 충족하면 support. 부상은 종류(source)상 통증(pain)으로 묶는다(plan_adjustments.source 스키마 불변).
강도: 통증·질병·진행 중 부상(많이 아파요, severity>=2) → rest, 가벼운 부상·복귀 구간 → reduce, CRS level 0 → rest, ACWR>=1.8 → Q 데이 이지 대체, 그 외 reduce.
"""
from __future__ import annotations

ACWR_AND = 1.5
ACWR_STRONG = 1.8
FATIGUE_AND = 7
CRS_AND_LEVEL = 1
INJURY_REST_SEVERITY = 2
STANDALONE = ("pain", "checkin_pain", "illness", "injury")
AND_MEMBERS = ("crs", "acwr", "checkin_fatigue")
KIND_OF = {"checkin_pain": "checkin", "checkin_fatigue": "checkin", "injury": "pain"}
PRIORITY = ("pain", "illness", "checkin", "race", "crs", "acwr", "readiness")


def kind_of(signal: str) -> str:
    return KIND_OF.get(signal, "race" if signal == "race_plan" else signal)


def _by_name(signals: list[dict]) -> dict[str, dict]:
    return {s["signal"]: s for s in signals if s.get("freshness") != "missing"}


def _met(name: str, s: dict) -> bool:
    v = s.get("value")
    if name in ("pain", "illness", "injury"):
        return bool(v)
    if name == "checkin_pain":
        return v in ("moderate", "severe")
    if v is None:
        return False
    return {"crs": v <= CRS_AND_LEVEL, "acwr": v >= ACWR_AND, "checkin_fatigue": v >= FATIGUE_AND}[name]


def triggered(signals: list[dict]) -> list[str]:
    """트리거 역할을 맡는 신호 이름 목록(빈 리스트면 트리거 없음)."""
    sig = _by_name(signals)
    alone = [n for n in STANDALONE if n in sig and _met(n, sig[n])]
    members = [n for n in AND_MEMBERS if n in sig and _met(n, sig[n])]
    return alone + (members if len(members) >= 2 else [])


def _injury_rest(s: dict) -> bool:
    """진행 중이고 정도가 '많이 아파요'(>=2)면 휴식. 가벼운 부상·복귀 구간은 reduce(품질 → 이지)."""
    d = s.get("detail") or {}
    return d.get("phase") == "active" and isinstance(s.get("value"), int) and s["value"] >= INJURY_REST_SEVERITY


def intensity(signals: list[dict], trig: list[str]) -> str:
    """'rest' | 'easy_replace' | 'reduce'."""
    sig = _by_name(signals)
    if any(n in trig for n in ("pain", "illness")) or sig.get("checkin_pain", {}).get("value") == "severe":
        return "rest"
    if "injury" in trig and _injury_rest(sig["injury"]):
        return "rest"
    if "crs" in trig and sig["crs"].get("value") == 0:
        return "rest"
    if "acwr" in trig and sig["acwr"].get("value", 0) >= ACWR_STRONG:
        return "easy_replace"
    return "reduce"


def primary(trig: list[str]) -> str | None:
    """주 트리거 종류. 우선순위 pain > illness > checkin > race > crs > acwr > readiness."""
    kinds = {kind_of(n) for n in trig}
    return next((k for k in PRIORITY if k in kinds), None)


def classify(signals: list[dict], trig: list[str]) -> list[dict]:
    """각 신호에 role(trigger/support/counter/hold/context)을 매긴 새 목록."""
    out = []
    for s in signals:
        s = dict(s)
        n = s["signal"]
        if n in trig:
            s["role"] = "trigger"
        elif s.get("role") in ("hold", "context"):
            pass
        elif s.get("freshness") != "missing" and n in STANDALONE + AND_MEMBERS and _met(n, s):
            s["role"] = "support"
        else:
            s["role"] = s.get("role") or "counter"
        out.append(s)
    return out
