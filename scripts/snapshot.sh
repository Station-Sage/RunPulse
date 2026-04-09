#!/usr/bin/env bash
# RunPulse DB 스냅샷 — VACUUM 후 gzip 백업.
#
# 사용법:
#   ./scripts/snapshot.sh
#   ./scripts/snapshot.sh --db-path /path/to/custom.db
#
# 출력: data/backups/runpulse_initial_YYYYMMDD.db.gz

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

DB_PATH=""
BACKUP_DIR="$PROJECT_ROOT/data/backups"

# 인자 파싱
while [[ $# -gt 0 ]]; do
  case "$1" in
    --db-path)
      DB_PATH="$2"
      shift 2
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 1
      ;;
  esac
done

# 기본 DB 경로 결정
if [[ -z "$DB_PATH" ]]; then
  DB_PATH="$PROJECT_ROOT/data/users/default/running.db"
fi

if [[ ! -f "$DB_PATH" ]]; then
  echo "ERROR: DB not found: $DB_PATH" >&2
  exit 1
fi

# 백업 디렉토리 생성
mkdir -p "$BACKUP_DIR"

DATE_STR=$(date +%Y%m%d)
BACKUP_FILE="$BACKUP_DIR/runpulse_initial_${DATE_STR}.db.gz"

echo "Snapshot: $DB_PATH → $BACKUP_FILE"

# 임시 파일에 VACUUM 후 복사
TMP_DB=$(mktemp)
trap 'rm -f "$TMP_DB"' EXIT

echo "  VACUUM..."
sqlite3 "$DB_PATH" "VACUUM INTO '$TMP_DB';"

echo "  Compressing..."
gzip -c "$TMP_DB" > "$BACKUP_FILE"

SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
echo "  Done: $BACKUP_FILE ($SIZE)"
