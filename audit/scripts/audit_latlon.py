import sqlite3, json
conn = sqlite3.connect("running.db")

# 1. Garmin activity summary에 lat/lon?
print("=== Garmin summary payload ===")
cur = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE entity_type=? AND source=? LIMIT 1",
    ("activity_summary", "garmin")
)
row = cur.fetchone()
if row:
    p = json.loads(row[0])
    for k in p.keys():
        kl = k.lower()
        if any(x in kl for x in ["lat", "lon", "location", "start", "coord", "position"]):
            print(f"  {k}: {p[k]}")

# 2. Strava summary payload에 lat/lon?
print("\n=== Strava summary payload ===")
cur2 = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE entity_type=? AND source=? LIMIT 1",
    ("activity_summary", "strava")
)
row2 = cur2.fetchone()
if row2:
    p2 = json.loads(row2[0])
    for k in p2.keys():
        kl = k.lower()
        if any(x in kl for x in ["lat", "lon", "location", "start", "coord", "position", "latlng"]):
            print(f"  {k}: {p2[k]}")

# 3. Intervals activity payload에 lat/lon?
print("\n=== Intervals activity payload ===")
cur3 = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE entity_type=? AND source=? LIMIT 1",
    ("activity_summary", "intervals")
)
row3 = cur3.fetchone()
if row3:
    p3 = json.loads(row3[0])
    for k in p3.keys():
        kl = k.lower()
        if any(x in kl for x in ["lat", "lon", "location", "start", "coord", "position"]):
            print(f"  {k}: {p3[k]}")

# 4. Garmin detail payload에서 vo2max 관련
print("\n=== Garmin detail - VO2max ===")
cur4 = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE entity_type=? AND source=? LIMIT 1",
    ("activity_detail", "garmin")
)
row4 = cur4.fetchone()
if row4:
    p4 = json.loads(row4[0])
    summary = p4.get("summaryDTO", {})
    for k in list(p4.keys()) + list(summary.keys()):
        kl = k.lower()
        if any(x in kl for x in ["vo2", "vdot", "lat", "lon"]):
            val = p4.get(k, summary.get(k))
            print(f"  {k}: {val}")

# 5. Garmin wellness에서 vo2max
print("\n=== Garmin wellness payload 전체 키 ===")
cur5 = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE entity_type=? AND source=? LIMIT 1",
    ("wellness", "garmin")
)
row5 = cur5.fetchone()
if row5:
    p5 = json.loads(row5[0])
    print(f"  keys: {list(p5.keys())}")
    for k in p5.keys():
        kl = k.lower()
        if any(x in kl for x in ["vo2", "vdot", "fitness"]):
            print(f"  {k}: {p5[k]}")

# 6. Intervals wellness/fitness에서 vdot
print("\n=== Intervals fitness data ===")
cur6 = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE source=? AND entity_type LIKE ? LIMIT 3",
    ("intervals", "%")
)
for row6 in cur6.fetchall():
    p6 = json.loads(row6[0])
    if isinstance(p6, dict):
        for k in p6.keys():
            kl = k.lower()
            if any(x in kl for x in ["vo2", "vdot", "eftp", "ftp"]):
                print(f"  {k}: {p6[k]}")

conn.close()
