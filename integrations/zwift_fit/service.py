from __future__ import annotations

from datetime import timezone

import duckdb

from .identity import ZwiftFitSourceIdentity
from .models import ArtifactFailure, CanonicalActivityCandidate, ZwiftFitSyncResult


class ZwiftFitSyncService:
    def __init__(self, discovery, ingestion, synchronization, repository, identity_factory=None):
        self.discovery = discovery
        self.ingestion = ingestion
        self.synchronization = synchronization
        self.repository = repository
        self.identity_factory = identity_factory or ZwiftFitSourceIdentity()

    def sync(self, *, started_at, completed_at=None):
        snapshot = self.discovery.discover(started_at)
        ingested = duplicate = malformed = failed = 0
        candidates, failures = [], []
        for artifact in snapshot.ready:
            identity = self.identity_factory.create(artifact)
            if self.repository.contains(identity.external_id):
                duplicate += 1
                continue
            record_key = f"zwift-{identity.external_id.removeprefix('sha256:')}.fit"
            try:
                self.ingestion.ingest(artifact, storage_key=record_key)
                self.synchronization.synchronize(
                    artifact, record_key=record_key, identity=identity,
                )
                record = self.synchronization.persisted_record(record_key)
                candidate = self._candidate(record, identity, artifact.name, started_at)
                self.repository.save(identity.external_id, artifact.name, artifact.stat(),
                                     started_at, record_key, candidate)
                candidates.append(candidate)
                ingested += 1
            except duckdb.Error:
                failed += 1
                failures.append(ArtifactFailure(artifact.name, "persistence_failure"))
            except Exception:
                malformed += 1
                failures.append(ArtifactFailure(artifact.name, "malformed_fit"))
        finished = completed_at or started_at
        result = ZwiftFitSyncResult(
            len(snapshot.discovered), len(snapshot.ready), ingested, duplicate,
            len(snapshot.unstable), malformed, failed, started_at, finished,
            tuple(candidates), tuple(failures),
        )
        self.repository.audit(result)
        return result

    @staticmethod
    def _candidate(record, identity, reference, ingested_at):
        def utc(value):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value.astimezone(timezone.utc)
        return CanonicalActivityCandidate(
            "zwift_fit", identity.external_id, utc(record.start_time), utc(record.end_time),
            record.duration, record.sport, record.distance, record.normalized_power,
            record.intensity_factor, record.tss, identity.external_id, reference,
            ingested_at.astimezone(timezone.utc),
        )
