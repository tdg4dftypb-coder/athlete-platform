"""Deterministic bounded incremental activity synchronization."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from hashlib import sha256

from .errors import IntervalsError, PaginationFailure
from .models import IntervalsSyncResult


class IntervalsSyncService:
    BOOTSTRAP_DAYS = 90
    OVERLAP_DAYS = 7
    PAGE_DAYS = 31

    def __init__(self, client, repository):
        self.client = client
        self.repository = repository

    def sync(self, *, started_at: datetime, completed_at: datetime | None = None) -> IntervalsSyncResult:
        if started_at.tzinfo is None:
            raise ValueError("started_at must be timezone-aware")
        now = started_at.astimezone(timezone.utc)
        watermark_before = self.repository.watermark()
        start = ((watermark_before - timedelta(days=self.OVERLAP_DAYS)) if watermark_before
                 else now - timedelta(days=self.BOOTSTRAP_DAYS)).date()
        end = now.date()
        records = []
        cursor = start
        try:
            while cursor <= end:
                page_end = min(cursor + timedelta(days=self.PAGE_DAYS - 1), end)
                records.extend(self.client.list_activities(cursor, page_end))
                cursor = page_end + timedelta(days=1)
        except IntervalsError as error:
            self.repository.record_failed_attempt(now, error.code)
            if records:
                raise PaginationFailure("Intervals.icu time-page failed; watermark retained") from error
            raise
        unique = {}
        for record in records:
            current = unique.get(record.external_id)
            if current is None or record.updated_at > current.updated_at:
                unique[record.external_id] = record
        ordered = tuple(sorted(unique.values(), key=lambda item: (item.updated_at, item.external_id)))
        finished = (completed_at or started_at).astimezone(timezone.utc)
        # The official list endpoint is bounded by activity date, not provider
        # update timestamp. The watermark is therefore the successful scan time;
        # provider updated_at remains record-level update evidence.
        watermark_after = now
        sync_id = "intervals:" + sha256(
            f"{now.isoformat()}|{start}|{end}|{watermark_before}".encode()
        ).hexdigest()[:24]
        inserted, updated, unchanged, archived = self.repository.persist_slice(
            ordered, started_at=now, completed_at=finished, watermark_before=watermark_before,
            watermark_after=watermark_after, sync_id=sync_id,
        )
        return IntervalsSyncResult(
            len(records), inserted, updated, unchanged, archived, 0,
            watermark_before, watermark_after, now, finished, "SUCCESS",
        )
