"""Sync 작업 결과 데이터 구조."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class SyncResult:
    """하나의 sync 작업 결과."""

    source: str
    job_type: str                          # 'activity' | 'wellness'
    status: str = "success"                # 'success' | 'partial' | 'failed' | 'skipped'

    total_items: int = 0
    synced_count: int = 0
    skipped_count: int = 0
    error_count: int = 0

    api_calls: int = 0

    errors: list = field(default_factory=list)   # [(entity_id, error_msg), ...]

    last_error: Optional[str] = None
    retry_after: Optional[str] = None            # ISO datetime

    def is_rate_limited(self) -> bool:
        return self.retry_after is not None

    def merge(self, other: SyncResult) -> SyncResult:
        """두 결과를 합침."""
        self.total_items += other.total_items
        self.synced_count += other.synced_count
        self.skipped_count += other.skipped_count
        self.error_count += other.error_count
        self.api_calls += other.api_calls
        self.errors.extend(other.errors)
        if other.last_error:
            self.last_error = other.last_error
        if other.retry_after:
            self.retry_after = other.retry_after
        if other.status == "failed" and self.synced_count > 0:
            self.status = "partial"
        return self

    def to_sync_job_dict(
        self, from_date: str = None, to_date: str = None
    ) -> dict:
        """sync_jobs 테이블 INSERT용 dict."""
        return {
            "id": str(uuid.uuid4()),
            "source": self.source,
            "job_type": self.job_type,
            "from_date": from_date,
            "to_date": to_date,
            "status": self.status,
            "total_items": self.total_items,
            "completed_items": self.synced_count,
            "error_count": self.error_count,
            "last_error": self.last_error,
            "retry_after": self.retry_after,
        }
