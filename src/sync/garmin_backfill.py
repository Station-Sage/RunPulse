"""Garmin ZIP export → activity_summaries backfill (v2)"""
import json, sqlite3, os, sys, glob
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from src.sync.garmin_v2_mappings import extract_summary_fields_from_zip
except ImportError:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
    from src.sync.garmin_v2_mappings import extract_summary_fields_from_zip

KST = timedelta(hours=9)

def _load_activities_from_zip_dir(export_dir: str) -> list:
    """summarizedActivities JSON 로드 (nested 구조 지원)"""
    patterns = ["*summarizedActivities*", "*SummarizedActivities*"]
    files = []
    for p in patterns:
        files.extend(glob.glob(os.path.join(export_dir, "**", p), recursive=True))
    if not files:
        print(f"[backfill] summarizedActivities 파일 없음: {export_dir}")
        return []
    
    all_activities = []
    for f in files:
        with open(f, "r", encoding="utf-8") as fp:
            data = json.load(fp)
        # 구조 감지: [{"summarizedActivitiesExport": [...]}] 또는 [...] 
        if isinstance(data, list) and data and isinstance(data[0], dict):
            if "summarizedActivitiesExport" in data[0]:
                acts = data[0]["summarizedActivitiesExport"]
            elif "activityId" in data[0]:
                acts = data
            else:
                acts = data
        elif isinstance(data, dict) and "summarizedActivitiesExport" in data:
            acts = data["summarizedActivitiesExport"]
        else:
            acts = data if isinstance(data, list) else []
        
        print(f"✅ {len(acts)}개 활동 로드: {f}")
        all_activities.extend(acts)
    return all_activities

def _zip_time_to_iso(epoch_ms) -> str:
    """epoch ms → ISO local time (KST)"""
    if not epoch_ms:
        return ""
    dt = datetime.fromtimestamp(epoch_ms / 1000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S")

def backfill_from_zip(export_dir: str, db_path: str = "running.db",
                      dry_run: bool = False, insert_new: bool = False):
    """ZIP export로 activity_summaries 백필"""
    activities = _load_activities_from_zip_dir(export_dir)
    if not activities:
        return
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    
    # DB에서 garmin 활동 조회 — source_id 매칭용 + start_time 매칭용
    rows = conn.execute(
        "SELECT source_id, start_time FROM activity_summaries WHERE source='garmin'"
    ).fetchall()
    
    by_source_id = {}
    by_start_time = {}
    for r in rows:
        by_source_id[r["source_id"]] = r["source_id"]
        if r["start_time"]:
            by_start_time[r["start_time"]] = r["source_id"]
    
    print(f"  DB garmin 활동: {len(rows)}건 (숫자ID: {sum(1 for r in rows if not r['source_id'].startswith('exp_'))}, exp_: {sum(1 for r in rows if r['source_id'].startswith('exp_'))})")
    
    matched = 0
    updated = 0
    skipped = 0
    not_found = 0
    inserted = 0
    id_upgraded = 0
    
    for act in activities:
        aid = str(act.get("activityId", ""))
        start_local = _zip_time_to_iso(act.get("startTimeLocal"))
        
        # 1순위: source_id로 직접 매칭
        rowid = by_source_id.get(aid)
        old_source_id = None
        
        # 2순위: start_time으로 매칭 (exp_ ID)
        if rowid is None and start_local and start_local in by_start_time:
            old_source_id = by_start_time[start_local]; rowid = old_source_id
        
        if rowid is None:
            if insert_new:
                fields = extract_summary_fields_from_zip(act)
                fields["source"] = "garmin"
                fields["source_id"] = aid
                if not dry_run:
                    cols = ", ".join(fields.keys())
                    placeholders = ", ".join(["?"] * len(fields))
                    try:
                        conn.execute(
                            f"INSERT INTO activity_summaries ({cols}) VALUES ({placeholders})",
                            list(fields.values())
                        )
                        inserted += 1
                    except sqlite3.Error as e:
                        print(f"  [INSERT 실패] {aid}: {e}")
                else:
                    print(f"  [DRY-INSERT] {aid}: {len(fields)} 컬럼")
                    inserted += 1
            else:
                not_found += 1
            continue
        
        matched += 1
        fields = extract_summary_fields_from_zip(act)
        
        # exp_ → 실제 garmin ID로 업그레이드
        if old_source_id and old_source_id.startswith("exp_"):
            fields["source_id"] = aid
            id_upgraded += 1
        
        if not fields:
            skipped += 1
            continue
        
        if dry_run:
            print(f"  [DRY] {aid}: {len(fields)} 컬럼 업데이트 예정" + 
                  (f" (ID 업그레이드: {old_source_id} → {aid})" if old_source_id else ""))
            updated += 1
            continue
        
        set_clause = ", ".join(f"{k}=?" for k in fields.keys())
        try:
            conn.execute(
                f"UPDATE activity_summaries SET {set_clause} WHERE source='garmin' AND source_id=?",
                list(fields.values()) + [old_source_id if old_source_id else aid]
            )
            updated += 1
        except sqlite3.Error as e:
            print(f"  [UPDATE 실패] {aid}: {e}")
    
    if not dry_run:
        conn.commit()
    
    print(f"\n  backfill 결과:")
    print(f"    매칭: {matched}/{len(activities)}")
    print(f"    업데이트: {updated}")
    print(f"    ID 업그레이드 (exp_→숫자): {id_upgraded}")
    print(f"    스킵(변경없음): {skipped}")
    print(f"    신규 삽입: {inserted}")
    print(f"    DB에 없음: {not_found}")
    
    conn.close()

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-dir", required=True)
    parser.add_argument("--db", default="running.db")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--insert-new", action="store_true")
    args = parser.parse_args()
    backfill_from_zip(args.export_dir, args.db, args.dry_run, args.insert_new)
