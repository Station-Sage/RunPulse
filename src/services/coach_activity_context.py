"""Coach 활동 컨텍스트 — `/coach/new?activity={id}` 근거 카드·추천 질문·프롬프트 요약.

읽기 전용. 근거 카드(거리·페이스·디커플링·TSB)와 훈련 유형별 추천 질문 3개를 만들고,
활동 스레드의 답변 프롬프트에 붙일 짧은 요약 문장을 만든다(20-library-activities design §코치에게 묻기).
"""
from __future__ import annotations

import sqlite3

from src.services.activity_feedback_service import get_feedback
from src.services.activity_impact_service import _load_metrics
from src.services.coach_consent import get_consent
from src.services.activity_summary_extras import _fmt_pace, _metric
from src.metrics.workout_classifier import TAG_LABELS
from src.utils.canonical import canonical_activity_id

_DEFAULT_QUESTIONS = [
    "이 러닝은 계획 대비 어땠나요?",
    "오늘 훈련의 강도는 적절했나요?",
    "다음 훈련은 어떻게 잡으면 좋을까요?",
]
_QUESTIONS: dict[str, list[str]] = {
    "long": ["후반 심박 상승이 걱정할 수준인가요?", "롱런 후 회복은 어떻게 하면 좋을까요?",
             "이 페이스로 목표 대회를 준비해도 될까요?"],
    "interval": ["목표 페이스를 지켰나요?", "세트 간 회복은 충분했나요?",
                 "다음 인터벌 강도는 어떻게 조정할까요?"],
    "tempo": ["템포 강도가 적절했나요?", "페이스 유지가 안정적이었나요?",
              "다음 템포런은 어떻게 조정할까요?"],
    "threshold": ["역치 페이스를 잘 유지했나요?", "심박이 너무 높지 않았나요?",
                  "다음 역치 훈련은 어떻게 조정할까요?"],
    "easy": ["충분히 편하게 달렸나요?", "심박이 이지런 범위였나요?", "이번 주 볼륨은 괜찮은가요?"],
    "recovery": ["회복런으로 적절했나요?", "다음 훈련 강도를 올려도 될까요?",
                 "피로가 풀리고 있나요?"],
    "race": ["이 레이스 기록은 어떻게 평가하나요?", "후반 페이스 저하의 원인은 무엇인가요?",
             "회복과 다음 목표는 어떻게 잡을까요?"],
}


def suggested_questions(workout_class: str | None) -> list[str]:
    """훈련 유형별 추천 질문 3개. 분류가 없거나 모르는 값이면 기본 질문."""
    return list(_QUESTIONS.get(workout_class or "", _DEFAULT_QUESTIONS))


def get_activity_context(conn: sqlite3.Connection, activity_id: int) -> dict | None:
    """근거 카드 + 추천 질문. 활동이 없으면 None."""
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT id, name, start_time, distance_m, avg_pace_sec_km FROM activity_summaries WHERE id = ?",
        (activity_id,)).fetchone()
    if row is None:
        return None
    ids = list({activity_id, canonical_activity_id(conn, activity_id)})
    wc = _metric(conn, ids, "workout_type_classified", ("runpulse:auto", "runpulse"))
    tag = wc["text"] if wc else None
    dec = _metric(conn, ids, "aerobic_decoupling_rp", ("runpulse:auto", "runpulse"))
    start = row["start_time"] or ""
    date = start[:10]
    tsb = _load_metrics(conn, date)[1] if date else None
    pace = row["avg_pace_sec_km"]
    return {
        "id": row["id"], "name": row["name"], "date": date or None,
        "workout_class": tag, "workout_class_label": TAG_LABELS.get(tag) if tag else None,
        "distance_km": round(row["distance_m"] / 1000, 2) if row["distance_m"] else None,
        "pace": _fmt_pace(pace) if pace else None,
        "decoupling_pct": round(dec["numeric"], 1) if dec and dec["numeric"] is not None else None,
        "tsb": tsb,
        "suggestions": suggested_questions(tag),
        "feedback": get_feedback(conn, activity_id),
    }


def activity_prompt_summary(conn: sqlite3.Connection, activity_id: int) -> str | None:
    """활동 스레드 프롬프트에 붙일 한 줄 요약. 활동이 없으면 None."""
    ctx = get_activity_context(conn, activity_id)
    if ctx is None:
        return None
    parts = [f"{ctx['date']} {ctx['workout_class_label'] or '러닝'}"]
    if ctx["distance_km"]:
        parts.append(f"{ctx['distance_km']}km")
    if ctx["pace"]:
        parts.append(f"평균 페이스 {ctx['pace']}")
    if ctx["decoupling_pct"] is not None:
        parts.append(f"유산소 디커플링 {ctx['decoupling_pct']}%")
    if ctx["tsb"] is not None:
        parts.append(f"당일 TSB {ctx['tsb']}")
    fb = ctx["feedback"]
    if fb:
        if fb["rpe"]:
            parts.append(f"체감 강도 RPE {fb['rpe']}")
        if fb["pain"] and fb["pain"] != "none":
            sites = f"({', '.join(fb['pain_sites'])})" if fb["pain_sites"] else ""
            parts.append(f"통증 {fb['pain']}{sites}")
        consent = get_consent(conn)
        if fb["note"] and consent and not consent["exclude_notes"]:
            parts.append(f"메모 \"{fb['note']}\"")
    return "[대화 대상 활동] " + " · ".join(parts)
