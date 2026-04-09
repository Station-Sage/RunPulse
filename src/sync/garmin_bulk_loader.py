"""Garmin Bulk Export ZIP 로더.

Garmin 계정 설정에서 다운로드한 Bulk Export ZIP(JSON 파일)을 파싱하여
기존 파이프라인(source_payloads → garmin_extractor → _helpers.save_*)에 투입합니다.

설계 판단:
  - ZIP 내 JSON 파일만 처리. FIT/GPX 파싱은 Phase 6 범위 외.
  - payload_hash로 중복 방지 — 이미 존재하는 payload는 skip.
  - reprocess.py의 _reprocess_activity_summaries 패턴 참고.

ZIP 내 파일명 패턴 (Garmin Export 기준):
  - {activityId}_summarizedActivities.json  → entity_type='activity_summary'
  - {activityId}_details.json               → entity_type='activity_detail'
  - wellness/YYYY-MM-DD_wellness.json        → entity_type='wellness'  (향후 확장용, 현재 skip)

사용법:
    loader = GarminBulkLoader(conn)
    result = loader.load("/path/to/export.zip")
    print(result.synced_count, result.skipped_count, result.error_count)
"""

from __future__ import annotations

import json
import logging
import sqlite3
import zipfile
from pathlib import Path
from typing import IO

from src.sync.extractors import get_extractor
from src.sync.raw_store import upsert_raw_payload, update_raw_activity_id
from src.sync.sync_result import SyncResult
from src.sync._helpers import (
    save_activity_core,
    save_metrics,
    save_laps,
    resolve_primaries,
)

log = logging.getLogger(__name__)

# 파일명 패턴 → entity_type 매핑
_SUMMARY_SUFFIX = "_summarizedActivities.json"
_DETAIL_SUFFIX = "_details.json"


class GarminBulkLoader:
    """Garmin Bulk Export ZIP → source_payloads → Layer 1/2 적재.

    Args:
        conn: SQLite connection
    """

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self.extractor = get_extractor("garmin")

    def load(self, zip_path: str | Path) -> SyncResult:
        """ZIP 파일을 파싱해 전체 파이프라인에 투입.

        Returns:
            SyncResult — synced_count(new), skipped_count(duplicate), error_count
        """
        result = SyncResult(source="garmin", job_type="bulk_load")
        zip_path = Path(zip_path)

        if not zip_path.exists():
            result.status = "failed"
            result.last_error = f"ZIP not found: {zip_path}"
            log.error("GarminBulkLoader: %s", result.last_error)
            return result

        try:
            with zipfile.ZipFile(zip_path, "r") as zf:
                self._process_zip(zf, result)
        except zipfile.BadZipFile as e:
            result.status = "failed"
            result.last_error = f"Invalid ZIP: {e}"
            log.error("GarminBulkLoader: %s", result.last_error)
            return result

        if result.error_count == 0:
            result.status = "success"
        elif result.synced_count > 0:
            result.status = "partial"
        else:
            result.status = "failed"

        log.info(
            "GarminBulkLoader complete: total=%d loaded=%d skipped=%d errors=%d",
            result.total_items, result.synced_count, result.skipped_count, result.error_count,
        )
        return result

    # ─────────────────────────────────────────────────────────────────────────
    # Internal
    # ─────────────────────────────────────────────────────────────────────────

    def _process_zip(self, zf: zipfile.ZipFile, result: SyncResult):
        """ZIP 내 JSON 파일을 분류 후 처리."""
        names = zf.namelist()
        # summary 파일 먼저 처리 (activity_id 생성), detail은 나중에
        summaries: list[tuple[str, str]] = []   # (entity_id, filename)
        details: list[tuple[str, str]] = []

        for name in names:
            fname = Path(name).name
            if not fname.endswith(".json"):
                continue
            if fname.endswith(_SUMMARY_SUFFIX):
                eid = fname[: -len(_SUMMARY_SUFFIX)]
                summaries.append((eid, name))
            elif fname.endswith(_DETAIL_SUFFIX):
                eid = fname[: -len(_DETAIL_SUFFIX)]
                details.append((eid, name))
            # 기타 JSON(wellness 등)은 현재 skip

        result.total_items = len(summaries) + len(details)
        log.info(
            "GarminBulkLoader: summaries=%d details=%d in ZIP",
            len(summaries), len(details),
        )

        # summary → source_payloads → activity_summaries
        activity_id_map: dict[str, int] = {}
        for eid, fname in summaries:
            self._process_summary(zf, eid, fname, activity_id_map, result)

        self.conn.commit()

        # detail → metrics, laps
        for eid, fname in details:
            self._process_detail(zf, eid, fname, activity_id_map, result)

        self.conn.commit()

    def _process_summary(
        self,
        zf: zipfile.ZipFile,
        entity_id: str,
        fname: str,
        activity_id_map: dict[str, int],
        result: SyncResult,
    ):
        raw = self._read_json(zf, fname)
        if raw is None:
            result.error_count += 1
            return

        # Garmin summarizedActivities JSON은 리스트일 수도 있음
        if isinstance(raw, list):
            items = raw
        else:
            items = [raw]

        for item in items:
            # entity_id를 activityId에서 추출 (없으면 파일명 기준)
            eid = str(item.get("activityId", entity_id))
            is_new = upsert_raw_payload(
                self.conn, "garmin", "activity_summary", eid, item,
                endpoint="bulk_export",
            )
            if not is_new:
                result.skipped_count += 1
                continue

            try:
                core = self.extractor.extract_activity_core(item)
                activity_id = save_activity_core(self.conn, core)
                update_raw_activity_id(self.conn, "garmin", "activity_summary", eid, activity_id)
                activity_id_map[eid] = activity_id
                result.synced_count += 1
            except Exception as e:
                log.error("BulkLoader summary %s: %s", eid, e)
                result.error_count += 1
                result.errors.append((eid, str(e)))
                result.last_error = str(e)

    def _process_detail(
        self,
        zf: zipfile.ZipFile,
        entity_id: str,
        fname: str,
        activity_id_map: dict[str, int],
        result: SyncResult,
    ):
        raw = self._read_json(zf, fname)
        if raw is None:
            result.error_count += 1
            return

        eid = str(raw.get("activityId", entity_id))
        is_new = upsert_raw_payload(
            self.conn, "garmin", "activity_detail", eid, raw,
            endpoint="bulk_export_detail",
        )
        if not is_new:
            result.skipped_count += 1
            return

        activity_id = activity_id_map.get(eid)
        if not activity_id:
            # summary가 없으면 DB에서 조회
            row = self.conn.execute(
                "SELECT activity_id FROM source_payloads "
                "WHERE source='garmin' AND entity_type='activity_summary' AND entity_id=?",
                (eid,),
            ).fetchone()
            if row:
                activity_id = row[0]

        if not activity_id:
            log.warning("BulkLoader detail %s: no matching activity_summary. Skip metrics.", eid)
            result.skipped_count += 1
            return

        # summary raw 로드 (metrics 추출에 필요)
        summary_row = self.conn.execute(
            "SELECT payload FROM source_payloads "
            "WHERE source='garmin' AND entity_type='activity_summary' AND entity_id=?",
            (eid,),
        ).fetchone()
        summary_raw = json.loads(summary_row[0]) if summary_row else {}

        try:
            metrics = self.extractor.extract_activity_metrics(summary_raw, raw)
            if metrics:
                save_metrics(self.conn, "activity", str(activity_id), "garmin", metrics)

            laps = self.extractor.extract_activity_laps(raw)
            if laps:
                save_laps(self.conn, activity_id, laps)

            resolve_primaries(self.conn, "activity", str(activity_id))
            result.synced_count += 1
        except Exception as e:
            log.error("BulkLoader detail %s: %s", eid, e)
            result.error_count += 1
            result.errors.append((eid, str(e)))
            result.last_error = str(e)

    def _read_json(self, zf: zipfile.ZipFile, fname: str) -> dict | list | None:
        """ZIP 내 JSON 파일 읽기. 실패 시 None 반환."""
        try:
            with zf.open(fname) as f:
                return json.loads(f.read().decode("utf-8"))
        except (json.JSONDecodeError, KeyError, UnicodeDecodeError) as e:
            log.error("BulkLoader: failed to read %s: %s", fname, e)
            return None
