"""능동 인사이트 규칙 평가 (V2-REPAIR D) — 신호 목록 → 사건 후보. 순수 함수(DB·외부 호출 없음).

새 계산은 만들지 않고 adjustment_triggers_v3 판정·ACWR 임계를 재사용한다. 질병·부상은 문구·근거 신호에 드러내지 않는다
(redact_health_for_ai 와 같은 원칙: 통증·질병·부상은 "몸 상태 이상 신호" 로만 표기, ADR-058).
"""
from __future__ import annotations

from datetime import date as _date

from src.services import adjustment_triggers_v3 as T

GAP_DAYS = 3
GAP_WATCH_DAYS = 7
_SNAP = ("signal", "value", "as_of", "freshness")
_HEALTH = ("illness", "injury")   # AI 도구(get_insights)로 나가는 근거 스냅샷에서 뺀다


def _snap(signals: list[dict], names: list[str]) -> list[dict]:
    return [{k: s.get(k) for k in _SNAP} for s in signals if s["signal"] in names and s.get("freshness") != "missing"]


def _cand(kind, severity, scope, text, signals, route, label):
    return {"kind": kind, "severity": severity, "dedupe_key": f"{kind}:{scope}", "text": text,
            "signals": signals, "action": {"label": label, "route": route}}


def evaluate_signal_rules(signals: list[dict]) -> list[dict]:
    """load_spike · recovery_low · pain_flag 후보."""
    sig = {s["signal"]: s for s in signals if s.get("freshness") != "missing"}
    trig = T.triggered(signals)
    out: list[dict] = []
    acwr = (sig.get("acwr") or {}).get("value")
    if acwr is not None and acwr >= T.ACWR_AND:
        sev = "act" if acwr >= T.ACWR_STRONG else "watch"
        out.append(_cand("load_spike", sev, "global", f"최근 훈련 부하가 급격히 늘었어요 (ACWR {acwr:.2f}). 오늘은 강도를 낮춰 보세요.",
                         _snap(signals, ["acwr"]), "/today", "오늘 세션 보기"))
    members = [n for n in T.AND_MEMBERS if n in trig]
    if len(members) >= 2:
        sev = "act" if (sig.get("crs") or {}).get("value") == 0 else "watch"
        out.append(_cand("recovery_low", sev, "global", "회복 신호가 여러 개 낮아요. 오늘은 쉬어 가는 쪽을 권해요.",
                         _snap(signals, members), "/today", "체크인 열기"))
    alone = [n for n in T.STANDALONE if n in trig]
    if alone:
        out.append(_cand("pain_flag", "act", "global", "몸 상태 이상 신호가 있어요. 무리하지 말고 오늘 세션을 확인하세요.",
                         _snap(signals, [n for n in alone if n not in _HEALTH]), "/today", "오늘 세션 보기"))
    return out


def evaluate_data_gap(day: str, last_success: dict[str, str | None]) -> list[dict]:
    """소스별 마지막 동기화 성공일(YYYY-MM-DD) → 3일 이상 끊긴 소스의 data_gap 후보. 이력 없는 소스는 제외."""
    out = []
    for prov, last in sorted(last_success.items()):
        if not last:
            continue
        gap = (_date.fromisoformat(day) - _date.fromisoformat(last[:10])).days
        if gap < GAP_DAYS:
            continue
        sev = "watch" if gap >= GAP_WATCH_DAYS else "info"
        out.append(_cand("data_gap", sev, prov, f"{prov} 동기화가 {gap}일째 멈췄어요. 데이터가 오래됐을 수 있어요.",
                         [{"signal": f"sync_{prov}", "value": gap, "as_of": last[:10], "freshness": "stale"}],
                         "/data/sources", "소스 확인"))
    return out
