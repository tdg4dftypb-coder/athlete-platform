from __future__ import annotations

from datetime import timezone


def naive(value):
    return value.astimezone(timezone.utc).replace(tzinfo=None)


class ActivityIdentitySchema:
    @staticmethod
    def create(connection):
        connection.execute("""
          CREATE TABLE IF NOT EXISTS canonical_activity_identities (
            canonical_activity_id VARCHAR PRIMARY KEY, canonical_provider VARCHAR NOT NULL,
            canonical_external_id VARCHAR NOT NULL, reconciled_at TIMESTAMP NOT NULL,
            UNIQUE(canonical_provider, canonical_external_id))
        """)
        connection.execute("""
          CREATE TABLE IF NOT EXISTS canonical_activity_aliases (
            provider VARCHAR NOT NULL, external_id VARCHAR NOT NULL,
            canonical_activity_id VARCHAR NOT NULL, match_method VARCHAR NOT NULL,
            evidence VARCHAR NOT NULL, reconciled_at TIMESTAMP NOT NULL,
            PRIMARY KEY(provider, external_id))
        """)
        connection.execute("""
          CREATE TABLE IF NOT EXISTS activity_reconciliation_audit (
            provider VARCHAR NOT NULL, external_id VARCHAR NOT NULL, status VARCHAR NOT NULL,
            canonical_activity_id VARCHAR, match_method VARCHAR, evidence VARCHAR NOT NULL,
            reconciled_at TIMESTAMP NOT NULL)
        """)
        connection.execute("""
          CREATE TABLE IF NOT EXISTS data_provider_freshness (
            provider VARCHAR PRIMARY KEY, last_attempt_at TIMESTAMP, last_success_at TIMESTAMP,
            watermark VARCHAR, operational_status VARCHAR NOT NULL, last_error_code VARCHAR)
        """)


class ActivityIdentityRepository:
    def __init__(self, connection): self.connection = connection

    def alias_target(self, provider, external_id):
        row = self.connection.execute(
            "SELECT canonical_activity_id FROM canonical_activity_aliases WHERE provider=? AND external_id=?",
            [provider, external_id]).fetchone()
        return None if row is None else row[0]

    def persist(self, canonical_rows, results, reconciled_at):
        c = self.connection
        c.execute("BEGIN TRANSACTION")
        try:
            for cid, provider, external_id in canonical_rows:
                c.execute("INSERT INTO canonical_activity_identities VALUES (?,?,?,?) "
                          "ON CONFLICT(canonical_activity_id) DO UPDATE SET reconciled_at=excluded.reconciled_at",
                          [cid, provider, external_id, naive(reconciled_at)])
                c.execute("INSERT INTO canonical_activity_aliases VALUES (?,?,?,?,?,?) "
                          "ON CONFLICT(provider,external_id) DO NOTHING",
                          [provider, external_id, cid, "CANONICAL", "canonical_source", naive(reconciled_at)])
            for result in results:
                if result.canonical_activity_id and result.status.value in {"MATCHED", "ALREADY_MATCHED"}:
                    c.execute("INSERT INTO canonical_activity_aliases VALUES (?,?,?,?,?,?) "
                              "ON CONFLICT(provider,external_id) DO NOTHING",
                              [result.provider, result.external_id, result.canonical_activity_id,
                               result.match_method.value, result.evidence, naive(reconciled_at)])
                c.execute("INSERT INTO activity_reconciliation_audit VALUES (?,?,?,?,?,?,?)",
                          [result.provider, result.external_id, result.status.value,
                           result.canonical_activity_id,
                           None if result.match_method is None else result.match_method.value,
                           result.evidence, naive(reconciled_at)])
            c.execute("COMMIT")
        except Exception:
            c.execute("ROLLBACK")
            raise

    def groups(self):
        rows = self.connection.execute(
            "SELECT canonical_activity_id, canonical_provider, canonical_external_id, reconciled_at "
            "FROM canonical_activity_identities ORDER BY canonical_activity_id").fetchall()
        result = []
        from .models import ActivityAlias, CanonicalActivityGroup, MatchMethod
        for row in rows:
            aliases = self.connection.execute(
                "SELECT provider,external_id,match_method,evidence FROM canonical_activity_aliases "
                "WHERE canonical_activity_id=? AND provider<>? ORDER BY provider,external_id",
                [row[0], row[1]]).fetchall()
            result.append(CanonicalActivityGroup(row[0], row[1], row[2],
                tuple(ActivityAlias(a,b,MatchMethod(c),d) for a,b,c,d in aliases),
                row[3].replace(tzinfo=timezone.utc)))
        return tuple(result)
