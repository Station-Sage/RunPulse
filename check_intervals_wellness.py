import sqlite3, json
conn = sqlite3.connect("running.db")

# Intervals wellness raw payload 확인
cur = conn.execute(
    "SELECT payload_json FROM raw_source_payloads WHERE source=? AND entity_type=? LIMIT 1",
    ("intervals", "wellness")
)
row = cur.fetchone()
if row:
    data = json.loads(row[0])
    if isinstance(data, list) and data:
        entry = data[0]
    else:
        entry = data
    # eFTP/FTP 관련 키 찾기
    for k in sorted(entry.keys()):
        kl = k.lower()
        if any(x in kl for x in ["ftp", "eftp", "vo2", "vdot", "threshold", "power"]):
            print(f"  {k}: {entry[k]}")
    print(f"\n  전체 키: {sorted(entry.keys())}")
else:
    print("intervals wellness payload 없음")

conn.close()
