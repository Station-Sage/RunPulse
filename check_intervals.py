import sqlite3, json
conn = sqlite3.connect("running.db")

cur = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE entity_type=? AND source=? LIMIT 1",
    ("activity", "intervals")
)
row = cur.fetchone()
if row:
    p = json.loads(row[0])
    if isinstance(p, list) and p:
        act = p[0]
    else:
        act = p
    # lat/lon 관련
    for k in sorted(act.keys()):
        kl = k.lower()
        if any(x in kl for x in ["lat", "lon", "location", "start_l", "coord", "ftp", "eftp", "vo2", "vdot"]):
            print(f"  {k}: {act[k]}")
    print(f"\n  전체 키 수: {len(act.keys())}")
    print(f"  전체 키: {sorted(act.keys())}")

conn.close()
