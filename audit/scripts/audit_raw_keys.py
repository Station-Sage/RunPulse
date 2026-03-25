import sqlite3, json, sys

conn = sqlite3.connect("running.db")

print("=" * 80)
print("RunPulse 원시 데이터 전체 필드 감사")
print("=" * 80)

# === 1. raw_source_payloads에서 소스+타입별 전체 키 추출 ===
print("\n[1] raw_source_payloads 소스/타입별 전체 키")
print("-" * 60)

rows = conn.execute("""
    SELECT source, entity_type, payload_json 
    FROM raw_source_payloads 
    WHERE payload_json IS NOT NULL
    ORDER BY source, entity_type
""").fetchall()

# 소스+타입별로 키 수집
from collections import defaultdict
key_map = defaultdict(set)
counts = defaultdict(int)

for source, etype, pj in rows:
    k = f"{source}|{etype}"
    counts[k] += 1
    try:
        p = json.loads(pj)
        if isinstance(p, list) and p:
            p = p[0]
        if isinstance(p, dict):
            key_map[k].update(p.keys())
    except:
        pass

for k in sorted(key_map.keys()):
    source, etype = k.split("|")
    keys = sorted(key_map[k])
    print(f"\n  [{source}] {etype} ({counts[k]}건, {len(keys)}키)")
    # 카테고리별 분류
    loc = [x for x in keys if any(w in x.lower() for w in ['lat','lon','latlng','location','coord','gps'])]
    time_ = [x for x in keys if any(w in x.lower() for w in ['time','date','duration','elapsed','start_d','timezone'])]
    dist = [x for x in keys if any(w in x.lower() for w in ['distance','speed','pace','gap'])]
    hr = [x for x in keys if any(w in x.lower() for w in ['heart','hr','heartrate'])]
    power = [x for x in keys if any(w in x.lower() for w in ['power','watt','ftp','joule','npower','normalize'])]
    cad = [x for x in keys if any(w in x.lower() for w in ['cadence','stride','step','run_cad'])]
    elev = [x for x in keys if any(w in x.lower() for w in ['elev','altitude','grade','climb','hill','ascent','descent','gain'])]
    weather = [x for x in keys if any(w in x.lower() for w in ['temp','weather','wind','humid','cloud','uv','feel'])]
    load = [x for x in keys if any(w in x.lower() for w in ['load','trimp','tss','stress','intensity','strain','hrss','effect'])]
    vo2 = [x for x in keys if any(w in x.lower() for w in ['vo2','vdot','fitness','max_met'])]
    zone = [x for x in keys if any(w in x.lower() for w in ['zone'])]
    lap = [x for x in keys if any(w in x.lower() for w in ['lap','split','interval','segment'])]
    best = [x for x in keys if any(w in x.lower() for w in ['best','effort','record','pr_','achievement'])]
    
    used = set(loc+time_+dist+hr+power+cad+elev+weather+load+vo2+zone+lap+best)
    other = [x for x in keys if x not in used]
    
    if loc: print(f"    위치: {loc}")
    if time_: print(f"    시간: {time_}")
    if dist: print(f"    거리/속도: {dist}")
    if hr: print(f"    심박: {hr}")
    if power: print(f"    파워: {power}")
    if cad: print(f"    케이던스: {cad}")
    if elev: print(f"    고도: {elev}")
    if weather: print(f"    날씨: {weather}")
    if load: print(f"    부하: {load}")
    if vo2: print(f"    VO2/FTP: {vo2}")
    if zone: print(f"    존: {zone}")
    if lap: print(f"    랩/인터벌: {lap}")
    if best: print(f"    베스트: {best}")
    if other: print(f"    기타: {other[:30]}{'...' if len(other)>30 else ''}")

# === 2. activity_summaries 현재 컬럼 vs 실제 가용 필드 대비 ===
print("\n\n[2] activity_summaries 현재 DB 컬럼")
print("-" * 60)
cols = [r[1] for r in conn.execute("PRAGMA table_info(activity_summaries)")]
print(f"  컬럼({len(cols)}): {cols}")

# === 3. activity_detail_metrics 현재 저장된 메트릭 종류 ===
print("\n\n[3] activity_detail_metrics 메트릭 종류 (소스별)")
print("-" * 60)
for source in ['garmin','strava','intervals']:
    metrics = conn.execute(
        "SELECT DISTINCT metric_name FROM activity_detail_metrics WHERE source=? ORDER BY metric_name",
        (source,)
    ).fetchall()
    print(f"  [{source}] {len(metrics)}종: {[m[0] for m in metrics]}")

# === 4. 저장 안 되는 주요 필드 식별 ===
print("\n\n[4] GAP 분석: API가 주지만 DB에 없는 주요 필드")
print("-" * 60)

# Garmin activity payload 키
garmin_act_keys = key_map.get("garmin|activity_summary", set()) | key_map.get("garmin|activity", set())
# 현재 DB 컬럼에 매핑된 Garmin 필드
garmin_mapped = {
    'activityId','activityType','startTimeLocal','distance','duration',
    'averageHR','maxHR','averageRunningCadenceInStepsPerMinute',
    'elevationGain','calories','activityName','startLatitude','startLongitude'
}
garmin_unmapped = garmin_act_keys - garmin_mapped
important_garmin = [k for k in garmin_unmapped if any(w in k.lower() for w in 
    ['speed','power','vo2','lap','split','weather','temp','end_lat','endlat',
     'endlon','end_lon','device','gear','train','cadence','stride','gct',
     'vertical','normaliz','moving','elapsed'])]
print(f"  [Garmin] 미매핑 중 주요: {sorted(important_garmin)[:20]}")

# Strava 
strava_keys = key_map.get("strava|activity_summary", set())
strava_mapped = {
    'id','type','start_date_local','distance','elapsed_time',
    'average_heartrate','max_heartrate','average_cadence',
    'total_elevation_gain','calories','name','start_latlng'
}
strava_unmapped = strava_keys - strava_mapped
important_strava = [k for k in strava_unmapped if any(w in k.lower() for w in 
    ['speed','watts','power','kilojoule','gear','laps','splits','best',
     'segment','weather','temp','end_latlng','device','suffer','workout_type',
     'weighted','moving_time','elev_high','elev_low','map','polyline'])]
print(f"  [Strava] 미매핑 중 주요: {sorted(important_strava)[:20]}")

# Intervals
int_keys = key_map.get("intervals|activity", set())
int_mapped_detail = set()
for r in conn.execute("SELECT DISTINCT metric_name FROM activity_detail_metrics WHERE source='intervals'"):
    int_mapped_detail.add(r[0])
important_int = [k for k in int_keys if any(w in k.lower() for w in 
    ['ftp','vo2','threshold','weather','temp','wind','gap','decoupling',
     'polariz','variabil','power_hr','efficiency','normalized',
     'training_stress','race','calories'])]
int_stored = [k for k in important_int if k in int_mapped_detail]
int_missing = [k for k in important_int if k not in int_mapped_detail]
print(f"  [Intervals] 중요 필드 중 저장됨: {sorted(int_stored)}")
print(f"  [Intervals] 중요 필드 중 미저장: {sorted(int_missing)}")

# === 5. Strava detail payload (laps, best_efforts 등) ===
print("\n\n[5] Strava detail 원시 데이터 하위 구조")
print("-" * 60)
row = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE source='strava' AND entity_type='activity_detail' LIMIT 1"
).fetchone()
if row:
    p = json.loads(row[0])
    for k in ['laps','splits_metric','splits_standard','best_efforts','segment_efforts']:
        v = p.get(k)
        if isinstance(v, list) and v:
            sample_keys = list(v[0].keys()) if isinstance(v[0], dict) else []
            print(f"  {k}: {len(v)}건, 키: {sample_keys}")
        elif v is not None:
            print(f"  {k}: type={type(v).__name__}")
        else:
            print(f"  {k}: 없음")
else:
    print("  Strava detail payload 없음")

# === 6. Garmin detail payload 하위 구조 ===
print("\n\n[6] Garmin detail 원시 데이터 하위 구조")
print("-" * 60)
row = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE source='garmin' AND entity_type='activity_detail' LIMIT 1"
).fetchone()
if row:
    p = json.loads(row[0])
    top_keys = list(p.keys())
    print(f"  최상위 키: {top_keys}")
    for k in top_keys:
        v = p[k]
        if isinstance(v, list) and v:
            if isinstance(v[0], dict):
                print(f"  {k}: {len(v)}건, 샘플키: {list(v[0].keys())[:15]}")
            else:
                print(f"  {k}: {len(v)}건, 타입: {type(v[0]).__name__}")
        elif isinstance(v, dict):
            print(f"  {k}: dict, 키: {list(v.keys())[:15]}")
else:
    print("  Garmin detail payload 없음")

conn.close()
print("\n\n감사 완료.")
