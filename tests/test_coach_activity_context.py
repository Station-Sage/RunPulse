"""tests/test_coach_activity_context.py — Coach 활동 컨텍스트(근거 카드·추천 질문·프롬프트 요약)."""
from src.ai.chat_engine import _with_activity_context
from src.services import coach_activity_context as cac


def _seed(c, pace=335.0):
    c.execute("INSERT INTO activity_summaries (id, source, source_id, name, activity_type, start_time,"
              " distance_m, avg_pace_sec_km) VALUES (7,'garmin','g7','롱런','running','2026-10-01T06:30:00',"
              "21100,?)", (pace,))
    c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, text_value,"
              " is_primary) VALUES ('activity','7','workout_type_classified','classification',"
              "'runpulse:auto','long',1)")
    c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value,"
              " is_primary) VALUES ('activity','7','aerobic_decoupling_rp','efficiency','runpulse:auto',6.84,1)")
    c.execute("INSERT INTO metric_store (scope_type, scope_id, metric_name, category, provider, numeric_value,"
              " is_primary) VALUES ('daily','2026-10-01','tsb','load','runpulse:formula_v1',-8.26,1)")
    c.commit()


def test_suggested_questions_by_class():
    assert cac.suggested_questions("long")[0] == "후반 심박 상승이 걱정할 수준인가요?"
    assert cac.suggested_questions("interval")[0] == "목표 페이스를 지켰나요?"
    assert len(cac.suggested_questions(None)) == 3 and len(cac.suggested_questions("zzz")) == 3


def test_activity_context_card(db_conn):
    _seed(db_conn)
    ctx = cac.get_activity_context(db_conn, 7)
    assert ctx["distance_km"] == 21.1 and ctx["pace"] == "5:35/km" and ctx["date"] == "2026-10-01"
    assert ctx["decoupling_pct"] == 6.8 and ctx["tsb"] == -8.3
    assert ctx["workout_class_label"] == "장거리" and len(ctx["suggestions"]) == 3


def test_activity_context_missing(db_conn):
    assert cac.get_activity_context(db_conn, 999) is None
    assert cac.activity_prompt_summary(db_conn, 999) is None


def test_prompt_summary_and_thread_injection(db_conn):
    _seed(db_conn)
    s = cac.activity_prompt_summary(db_conn, 7)
    assert s.startswith("[대화 대상 활동]") and "21.1km" in s and "디커플링 6.8%" in s
    db_conn.execute("INSERT INTO chat_threads (id, title, context_kind, context_ref) VALUES (1,'t','activity','7')")
    db_conn.execute("INSERT INTO chat_threads (id, title) VALUES (2,'t2')")
    db_conn.commit()
    assert _with_activity_context(db_conn, 1, "CTX").endswith("\n\nCTX")
    assert _with_activity_context(db_conn, 1, "CTX").startswith("[대화 대상 활동]")
    assert _with_activity_context(db_conn, 2, "CTX") == "CTX"
    assert _with_activity_context(db_conn, None, "CTX") == "CTX"


def test_prompt_summary_includes_feedback_and_respects_note_consent(db_conn):
    from src.services.activity_feedback_service import put_feedback
    from src.services.coach_consent import save_consent
    _seed(db_conn)
    put_feedback(db_conn, 7, {"rpe": 8, "pain": "mild", "pain_sites": ["knee"], "note": "무릎 뻐근"})
    save_consent(db_conn, "claude", exclude_notes=False)
    s = cac.activity_prompt_summary(db_conn, 7)
    assert "RPE 8" in s and "통증 mild(knee)" in s and "무릎 뻐근" in s
    save_consent(db_conn, "claude", exclude_notes=True)
    s = cac.activity_prompt_summary(db_conn, 7)
    assert "RPE 8" in s and "무릎 뻐근" not in s


def test_list_rows_carry_rpe(db_conn):
    from src.services.activity_feedback_service import put_feedback
    from src.services.activity_list_rows import enrich_rows
    _seed(db_conn)
    put_feedback(db_conn, 7, {"rpe": 6})
    rows = [{"id": 7, "name": "롱런", "distance_m": 21100}]
    enrich_rows(db_conn, rows)
    assert rows[0]["rpe"] == 6
