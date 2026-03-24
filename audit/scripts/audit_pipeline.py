import sqlite3, json
conn = sqlite3.connect("running.db")

print("=" * 60)
print("RunPulse 데이터 파이프라인 전체 감사")
print("=" * 60)

# 1. activity_summaries 컬럼 vs 실제 채워진 비율
print("\n=== 1. activity_summaries 컬럼 채움률 ===")
cols = [r[1] for r in conn.execute("PRAGMA table_info(activity_summaries)").fetchall()]
for col in cols:
    total = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
    filled = conn.execute(f"SELECT COUNT(*) FROM activity_summaries WHERE [{col}] IS NOT NULL").fetchone()[0]
    pct = round(filled / total * 100, 1) if total else 0
    if pct < 100:
        print(f"  {col}: {filled}/{total} ({pct}%)")

# 2. 소스별 activity_summaries 컬럼 채움률
print("\n=== 2. 소스별 주요 컬럼 채움률 ===")
for source in ["garmin", "strava", "intervals"]:
    total = conn.execute("SELECT COUNT(*) FROM activity_summaries WHERE source=?", (source,)).fetchone()[0]
    print(f"\n  [{source}] 총 {total}건")
    for col in ["avg_hr", "max_hr", "avg_cadence", "elevation_gain", "calories", "avg_power", "start_lat", "start_lon", "workout_label"]:
        filled = conn.execute(f"SELECT COUNT(*) FROM activity_summaries WHERE source=? AND [{col}] IS NOT NULL", (source,)).fetchone()[0]
        pct = round(filled / total * 100, 1) if total else 0
        if pct < 100:
            print(f"    {col}: {filled}/{total} ({pct}%)")

# 3. activity_detail_metrics 소스별 메트릭 종류
print("\n=== 3. activity_detail_metrics 소스별 메트릭 ===")
for source in ["garmin", "strava", "intervals"]:
    cur = conn.execute(
        "SELECT metric_name, COUNT(*) FROM activity_detail_metrics WHERE source=? GROUP BY metric_name ORDER BY metric_name",
        (source,)
    )
    rows = cur.fetchall()
    total_acts = conn.execute("SELECT COUNT(*) FROM activity_summaries WHERE source=?", (source,)).fetchone()[0]
    print(f"\n  [{source}] {len(rows)}종 메트릭, 활동 {total_acts}건")
    for r in rows:
        pct = round(r[1] / total_acts * 100, 1) if total_acts else 0
        marker = " ⚠️" if pct < 10 else ""
        print(f"    {r[0]}: {r[1]}건 ({pct}%){marker}")

# 4. activity_laps 상태
print("\n=== 4. activity_laps ===")
lap_cnt = conn.execute("SELECT COUNT(*) FROM activity_laps").fetchone()[0]
lap_acts = conn.execute("SELECT COUNT(DISTINCT activity_id) FROM activity_laps").fetchone()[0]
print(f"  총 {lap_cnt}건, {lap_acts}개 활동")
for source in ["garmin", "strava", "intervals"]:
    cnt = conn.execute("SELECT COUNT(*) FROM activity_laps WHERE source=?", (source,)).fetchone()[0]
    print(f"  [{source}] {cnt}건")

# 5. daily_wellness 채움률
print("\n=== 5. daily_wellness ===")
well_cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_wellness)").fetchall()]
total_well = conn.execute("SELECT COUNT(*) FROM daily_wellness").fetchone()[0]
print(f"  총 {total_well}건")
for col in well_cols:
    if col in ("id", "date", "source"):
        continue
    filled = conn.execute(f"SELECT COUNT(*) FROM daily_wellness WHERE [{col}] IS NOT NULL").fetchone()[0]
    pct = round(filled / total_well * 100, 1) if total_well else 0
    print(f"  {col}: {filled}/{total_well} ({pct}%)")

# 6. daily_fitness 채움률
print("\n=== 6. daily_fitness ===")
fit_cols = [r[1] for r in conn.execute("PRAGMA table_info(daily_fitness)").fetchall()]
total_fit = conn.execute("SELECT COUNT(*) FROM daily_fitness").fetchone()[0]
print(f"  총 {total_fit}건")
for col in fit_cols:
    if col in ("id", "date", "source", "updated_at"):
        continue
    filled = conn.execute(f"SELECT COUNT(*) FROM daily_fitness WHERE [{col}] IS NOT NULL").fetchone()[0]
    pct = round(filled / total_fit * 100, 1) if total_fit else 0
    print(f"  {col}: {filled}/{total_fit} ({pct}%)")

# 7. raw_source_payloads에서 미추출 데이터 확인
print("\n=== 7. raw_source_payloads 미추출 데이터 ===")
# Strava detail에서 laps, splits, segments
cur7 = conn.execute(
    "SELECT COUNT(*) FROM raw_source_payloads WHERE entity_type=? AND source=?",
    ("activity_detail", "strava")
)
strava_details = cur7.fetchone()[0]
print(f"  Strava detail payloads: {strava_details}건 (활동 490개 중)")

# Garmin detail
cur7b = conn.execute(
    "SELECT COUNT(*) FROM raw_source_payloads WHERE entity_type=? AND source=?",
    ("activity_detail", "garmin")
)
garmin_details = cur7b.fetchone()[0]
print(f"  Garmin detail payloads: {garmin_details}건 (활동 496개 중)")

# FIT export 파일
fit_cnt = conn.execute(
    "SELECT COUNT(*) FROM raw_source_payloads WHERE entity_type=?", ("fit_export",)
).fetchone()[0]
print(f"  FIT export files: {fit_cnt}건")

# 8. computed_metrics vs 활동 수 비교
print("\n=== 8. computed_metrics 커버리지 ===")
total_acts_all = conn.execute("SELECT COUNT(*) FROM activity_summaries").fetchone()[0]
total_dates = conn.execute("SELECT COUNT(DISTINCT date(start_time)) FROM activity_summaries").fetchone()[0]
print(f"  총 활동: {total_acts_all}건, 총 날짜: {total_dates}일")
cur8 = conn.execute("SELECT metric_name, COUNT(*) FROM computed_metrics GROUP BY metric_name ORDER BY metric_name")
for r in cur8.fetchall():
    print(f"  {r[0]}: {r[1]}건")

conn.close()
