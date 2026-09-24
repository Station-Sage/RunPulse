"""합성 데이터 DB 생성 — UI 스모크용(개인 데이터 아님). 사용: python3 scripts/synth_smoke/seed_synth.py <out.db> [--empty]

지정한 경로에만 쓴다(기존 파일은 삭제 후 재생성). data/users/* 어느 계정 DB도 건드리지 않는다.
--empty: 스키마만 만들고 데이터는 넣지 않는다(첫 실행 "데이터 없음" 상태 확인용).
"""
from __future__ import annotations

import math
import random
import sqlite3
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.db_setup import create_tables, migrate_db  # noqa: E402


def seed(out: str | Path, empty: bool = False) -> dict:
    """합성 DB를 out에 만든다. 반환: {"activities": 활동 수}."""
    out = str(out)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    for suffix in ("", "-wal", "-shm"):
        Path(out + suffix).unlink(missing_ok=True)
    conn = sqlite3.connect(out)
    create_tables(conn)
    migrate_db(conn)
    if empty:
        conn.commit()
        conn.close()
        return {"activities": 0}
    random.seed(7)
    today = date.today()

    def cols(table):
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}

    def ins(table, **kw):
        c = cols(table)
        kw = {k: v for k, v in kw.items() if k in c}
        conn.execute(
            f"INSERT INTO {table} ({','.join(kw)}) VALUES ({','.join('?' * len(kw))})", list(kw.values())
        )
        return conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    def metric(scope, sid, name, val, cat, provider="runpulse", parent=None, text=None):
        return ins("metric_store", scope_type=scope, scope_id=str(sid), metric_name=name, category=cat,
                   provider=provider, numeric_value=val, text_value=text, is_primary=1,
                   parent_metric_id=parent, algorithm_version="formula_v1")

    # ── 일별 웰니스·메트릭 (30일) ──
    for i in range(30):
        d = (today - timedelta(days=29 - i)).isoformat()
        ins("daily_wellness", date=d, sleep_score=70 + random.randint(-12, 10), hrv_last_night=55 + random.randint(-8, 8), hrv_weekly_avg=60,
            resting_hr=50 + random.randint(-2, 3), body_battery_high=70 + random.randint(-15, 15),
            avg_stress=30 + random.randint(-8, 12))
        ctl = 55 + i * 0.5 + random.uniform(-1, 1)
        atl = ctl + random.uniform(-8, 10)
        metric("daily", d, "ctl", round(ctl, 1), "load")
        metric("daily", d, "atl", round(atl, 1), "load")
        metric("daily", d, "tsb", round(ctl - atl, 1), "load")
        metric("daily", d, "acwr", round(1.0 + random.uniform(-0.15, 0.2), 2), "load")
        utrs = metric("daily", d, "utrs", 68 + random.randint(-10, 10), "readiness")
        metric("daily", d, "utrs_sleep", 70 + random.randint(-10, 10), "readiness", parent=utrs)
        metric("daily", d, "utrs_hrv", 66 + random.randint(-10, 10), "readiness", parent=utrs)
        metric("daily", d, "cirs", 35 + random.randint(-10, 15), "readiness")

    # ── 활동 (25일간 러닝 14회) ──
    act_ids = []
    aid = 100
    for k in range(14):
        d = today - timedelta(days=k * 2 if k else 1)
        dist = random.choice([6000, 8000, 10000, 12000, 16000]) + random.randint(-400, 400)
        pace = random.randint(310, 350)
        dur = int(dist / 1000 * pace)
        aid_k = aid + k
        ins("activity_summaries", id=aid_k, source="garmin", source_id=str(aid_k),
            name=random.choice(["Easy Run", "Tempo Run", "Long Run", "Recovery Run"]),
            activity_type="running", start_time=f"{d.isoformat()}T06:30:00", distance_m=dist, duration_sec=dur,
            avg_hr=138 + random.randint(-6, 12), avg_pace_sec_km=pace, elevation_gain=random.randint(20, 140))
        act_ids.append(aid_k)

    # 최신 활동(100)에 풍부한 데이터
    A = 100
    conn.execute("UPDATE activity_summaries SET name='Interval 6x800', distance_m=9200, duration_sec=3100, avg_pace_sec_km=337 WHERE id=?", (A,))
    for name, val, cat, prov in [
        ("max_hr", 178, "hr", "garmin"), ("avg_cadence", 174, "running_dynamics", "garmin"),
        ("training_load", 118, "load", "garmin"), ("training_effect_aerobic", 3.6, "load", "garmin"),
        ("efficiency_factor", 1.42, "efficiency", "runpulse"), ("aerobic_decoupling", 3.1, "efficiency", "runpulse"),
        ("vo2max_activity", 51.2, "capacity", "garmin"), ("avg_ground_contact_time_ms", 241, "running_dynamics", "garmin"),
        ("hr_zone_1_sec", 240, "hr", "garmin"), ("hr_zone_2_sec", 1200, "hr", "garmin"), ("hr_zone_3_sec", 900, "hr", "garmin"),
        ("hr_zone_4_sec", 600, "hr", "garmin"), ("hr_zone_5_sec", 160, "hr", "garmin"),
        ("weather_temp_c", 18.4, "weather", "garmin"), ("weather_humidity_pct", 62, "weather", "garmin"),
        ("weather_wind_speed_ms", 3.2, "weather", "garmin"), ("avg_stride_length_cm", 112.0, "running_dynamics", "garmin"),
    ]:
        metric("activity", A, name, val, cat, provider=prov)
    metric("activity", A, "weather_condition", None, "weather", provider="garmin", text="맑음")
    # 랩: 워밍업 + 6x800 인터벌 + 쿨다운
    laps = [(1600, 560, 350)] + [(800, 232 if j % 2 == 0 else 300, 290 if j % 2 == 0 else 375) for j in range(6)] + [(1000, 380, 380)]
    for i, (dm, dur, pace) in enumerate(laps):
        ins("activity_laps", activity_id=A, source="garmin", lap_index=i, duration_sec=dur, distance_m=dm,
            avg_hr=150 + i * 2, max_hr=160 + i * 2, avg_pace_sec_km=pace, avg_cadence=172 + (i % 3), elevation_gain=3 + i)
    # 스트림 300점
    for t in range(300):
        ins("activity_streams", activity_id=A, source="garmin", elapsed_sec=t * 10,
            distance_m=t * 30.0, heart_rate=int(140 + 25 * math.sin(t / 25)), cadence=172, altitude_m=20 + 5 * math.sin(t / 40),
            speed_ms=2.9 + 0.5 * math.sin(t / 25))

    # ── 동기화 기록(Provider 현황의 "마지막 동기화") ──
    synced = (datetime.now(timezone.utc) - timedelta(hours=2)).strftime("%Y-%m-%d %H:%M:%S")
    ins("source_payloads", source="garmin", entity_type="activity", entity_id="synth-sync", payload="{}", fetched_at=synced)

    # ── 마일스톤 ──
    ins("milestones", type="distance_threshold", date=(today - timedelta(days=12)).isoformat(), title="누적 500km 돌파", detail=None)
    ins("milestones", type="pb", date=(today - timedelta(days=5)).isoformat(), title="10K PB 47:12",
        detail="10k PB 47:12 (페이스 4:43/km)", activity_id=A + 3)
    ins("milestones", type="metric_recompute", date=(today - timedelta(days=3)).isoformat(), title="RunPulse 재계산",
        detail="formula_v2 적용 — CTL 66→68", metric_name="ctl", old_value=66, new_value=68)

    # ── 목표·플랜 (이번 주 + 다음 주) ──
    gid = ins("goals", name="춘천 하프마라톤 준비", race_date=(today + timedelta(days=70)).isoformat(), distance_km=21.1,
              target_time_sec=6300, status="active", distance_label="하프", weekly_km_target=45, plan_weeks=12)
    ws = today - timedelta(days=today.weekday())
    types = ["easy", "interval", "rest", "tempo", "easy", "long", "rest"]
    for w in range(2):
        for i, tp in enumerate(types):
            dd = ws + timedelta(days=w * 7 + i)
            ins("planned_workouts", date=dd.isoformat(), workout_type=tp, distance_km=None if tp == "rest" else 8 + i,
                description=f"{tp} 세션", completed=1 if dd < today and tp != "rest" and i % 2 == 0 else 0, source="manual")

    # ── Coach 스레드 ──
    t1 = ins("chat_threads", title="레이스 페이스 전략")
    ins("chat_messages", role="user", content="춘천 하프에서 서브 1:45 가능해?", thread_id=t1)
    ins("chat_messages", role="assistant", content="현재 데이터 기반으로는 1:46~1:48 범위가 현실적입니다.", thread_id=t1)
    t2 = ins("chat_threads", title="피로 관리 질문")
    ins("chat_messages", role="user", content="요즘 피곤한데 쉬어야 할까?", thread_id=t2)
    ins("chat_messages", role="assistant", content="HRV가 기준선 아래라 하루 회복을 권합니다.", thread_id=t2)

    conn.commit()
    conn.close()
    return {"activities": len(act_ids)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit("사용: seed_synth.py <out.db> [--empty]")
    result = seed(sys.argv[1], empty="--empty" in sys.argv[2:])
    print("seeded", sys.argv[1], "activities:", result["activities"])
