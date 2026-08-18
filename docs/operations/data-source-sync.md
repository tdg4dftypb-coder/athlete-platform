# Production Data Source Synchronization (v1)

This document describes the automated synchronization and operational scheduling of production data sources in Athlete Platform.

---

## 1. Canonical Backend Startup Command

To run the Athlete Platform production backend with the integrated operational scheduler:

```bash
.venv/bin/python scripts/run_production_server.py --host 0.0.0.0 --port 8000
```

---

## 2. Synchronization Frequencies & Policies

| Data Source | Cadence | Trigger Policy | Semantics |
|---|---|---|---|
| **Zwift FIT** | Every **10 minutes** (600s) | Automated + Startup Catch-Up | SHA-256 deduplicated, completed cycling activities owner. |
| **Intervals.icu** | Every **4 hours** (14,400s) | Automated + Startup Catch-Up | Incremental 7-day overlap sync, restricted stub skipping. |
| **Apple Health (HealthKit)** | Event-Driven (Push) | Client-Initiated (iPhone) | Push from iOS app to `POST /api/v1/ingestion/healthkit`. No backend polling. |

---

## 3. Observability & Health Inspection

To check live status, freshness, and last success timestamps for all data sources:

```bash
curl -s http://127.0.0.1:8000/api/v1/data-sources/status
```

Expected JSON response:
```json
{
  "contract_version": "1.0",
  "providers": [
    {"provider": "healthkit", "operational_status": "READY", "freshness_status": "FRESH", ...},
    {"provider": "intervals_icu", "operational_status": "READY", "freshness_status": "FRESH", ...},
    {"provider": "zwift_fit", "operational_status": "READY", "freshness_status": "FRESH", ...}
  ]
}
```

---

## 4. Resilience & Concurrency Guarantees

* **Non-blocking Locks:** Concurrent or overlapping sync jobs for the same provider are safely skipped without blocking worker threads.
* **Failure Isolation:** An individual provider sync error is safely caught and logged, never halting the scheduler loop or crashing the HTTP server.
* **Graceful Shutdown:** The scheduler thread joins cleanly upon process termination (`SIGINT` / `Ctrl+C`).
