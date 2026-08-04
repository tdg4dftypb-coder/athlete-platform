# Dashboard HTTP Transport Boundary Architecture

This document describes the thin, decoupled HTTP transport boundary for `AthleteDashboard` payload v1.0, connecting frontend experience views to backend decision engines.

---

## 1. Port and Adapters Pattern

### Port Interface (`DashboardPayloadSource`)
Defined in [`web/AthleteWeb/src/app/dashboard-payload-source.ts`](file:///Users/marsm0wa/Documents/athlete-platform/web/AthleteWeb/src/app/dashboard-payload-source.ts):

```typescript
export interface DashboardPayloadSource {
  load(): Promise<unknown>;
}
```

The port knows nothing about UI components, presentation states, or mapping logic. It simply returns raw `unknown` data asynchronously.

### Adapters

1. **`StaticJsonDashboardPayloadSource`**
   - Loads static JSON files (e.g. `/data/athlete-dashboard-v1.json`).
   - Enabled via query parameter `?source=live-file`.

2. **`HttpDashboardPayloadSource`**
   - Fetches JSON payload over HTTP GET.
   - Configurable via `import.meta.env.VITE_DASHBOARD_API_URL` (default: `http://127.0.0.1:8000/api/v1/dashboard`).
   - Enabled via query parameter `?source=http`.

---

## 2. Backend Endpoint (`GET /api/v1/dashboard`)

Implemented in [`server/app.py`](file:///Users/marsm0wa/Documents/athlete-platform/server/app.py) using a zero-dependency WSGI application:

- **Method**: `GET`
- **Path**: `/api/v1/dashboard`
- **Response**: `200 OK` with `Content-Type: application/json; charset=utf-8`
- **Payload**: Canonical `AthleteDashboard` payload v1.0 serialized via `DashboardSerializer`
- **Error Handling**: `500 Internal Server Error` with controlled error message (no leaked stack traces)

---

## 3. State Lifecycle

```
[User Navigate] 
     │
     ▼
[Render Loading State] (skeletons / spinners)
     │
     ▼
[Source.load()] (StaticJson / HTTP GET)
     │
     ├─────────► [Success 2xx] ──► [Runtime Parser] ──► [Mapper] ──► [Ready / Stale / Partial State]
     │
     └─────────► [Failure / Non-2xx] ───────────────► [Failure Presentation State]
```

- **Data Isolation**: On transport or parsing failure, the application renders an explicit `failure` state for the active view. It **never** falls back to Preview Data or alternative sources.

---

## 4. Privacy Boundaries & Security Rules

1. **Ignored Assets**:
   - `web/AthleteWeb/public/data/` (local exported payload containing health metrics)
   - `web/AthleteWeb/public/screenshots/live-file-*.png`
   - `web/AthleteWeb/public/screenshots/http-*.png`
2. **Version Control**:
   - Only synthetic, anonymized test fixtures (e.g., in `tests/`) are committed to Git.
   - No real user health data or live database files are ever committed.

---

## 5. Excluded Scope

The following features remain explicitly out of scope for Sprint 2:
- User Authentication / Authorization (OAuth, JWT, API keys)
- Client-side or Server-side Caching (HTTP Cache-Control, Redis)
- Background Sync / WebSockets / Cyclic polling
- Production CORS / Deployment infrastructure
- Domain / Contract v1.0 modifications
