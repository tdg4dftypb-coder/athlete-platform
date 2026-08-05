# Biomarkers Experience Contract & Frontend Boundary

## 1. Scope & Overview
This document defines the frontend contract, runtime payload parser, presentation model, and state mapping rules for the **Biomarkers & Laboratory Intelligence** feature layer in AthleteWeb.

- **Payload Contract**: `BiomarkersDashboardPayloadV1` (`contract_version = "1.0"`)
- **Transport Endpoint**: `GET /api/v1/biomarkers` (routed via Vite same-origin proxy `/api` $\rightarrow$ `http://127.0.0.1:8000`)
- **Developer Preview Views**: `?view=biomarkers` and `?view=biomarkers&source=http`

---

## 2. Payload Parser & Strict Validation (`biomarkers-payload-parser.ts`)
The frontend runtime parser enforces strict contract validation:
- Requires `contract_version === "1.0"`.
- Requires `metadata.status` in (`"ready"`, `"partial"`, `"unavailable"`).
- Requires `completeness_score` in range `[0.0, 1.0]`.
- Enforces ISO 8601 aware timestamps.
- **Strict Privacy & Safety Boundary**:
  - Rejects payloads containing `source_document_hash`, `filename`, or `original_filename`.
  - Rejects payloads containing `raw_value` inside `unresolved_items`.
  - Rejects `NaN` or `Infinity` numeric values.
- Malformed payloads yield an immediate `failure` state without partial degradation or fallback to preview data.

---

## 3. Presentation States (`biomarkers-presentation-state.ts`)
The presentation layer manages 6 explicit presentation state kinds matching AthleteWeb conventions:

1. **`ready`**: Valid, fully verified biomarker payload available.
2. **`partial`**: Valid payload available, but quality limitations exist (e.g. unresolved items requiring review, unverified items, or possible duplicates).
3. **`unavailable`**: No active laboratory reports or usable observations in the athlete profile.
4. **`stale`**: Payload response freshness age (`as_of` timestamp) exceeds the `staleAfterMs` threshold (e.g. 7 days).
5. **`loading`**: Transport data fetch in progress.
6. **`failure`**: Transport error, HTTP non-2xx status, or runtime payload validation failure.

---

## 4. Mapper Rules, Temporal Semantics & Medical Safety (`biomarkers-mapper.ts`)
- **Temporal Semantics (Payload Freshness vs. Laboratory Data Age)**:
  - **`as_of` (Payload Freshness)**: Evaluates backend response freshness. If `as_of` age exceeds `context.staleAfterMs`, the UI enters the `stale` state.
  - **`data_as_of` / `collected_at` (Laboratory Data Age)**: Indicates when the laboratory sample was drawn. Older laboratory collection dates (e.g. 30–60 days old) are standard for periodic blood tests and **do NOT trigger a `stale` state if the payload `as_of` timestamp is fresh**.
  - **Null Dates**: A null `data_as_of` or `latest_collection_date` displays `"Brak daty pobrania"` without throwing runtime errors or fabricating dates.
- **Source Presentation**: `laboratory_flag` is presented strictly as a raw laboratory source indicator (e.g. `"H"`, `"L"`).
- **Trend Neutrality**: Trend direction (`increasing`, `decreasing`, `stable`, `unavailable`) is presented as a neutral technical direction without medical rating or judgment (e.g. increasing trend is never automatically labeled "good" or "bad").
- **No Fabricated Data**: No artificial values, custom "athletic normal ranges", or automated clinical diagnoses are added by the frontend mapper.
- **Privacy in Unresolved Items**: Unresolved items present raw names and units for user review, but **never display raw values (`raw_value`) in summary lists**.

---

## 5. Excluded Scope (Prior to Sprint 6B)
The following capabilities are explicitly excluded from Sprint 6A and reserved for future stages:
- Final Biomarkers Experience UI design system layout in bottom navigation;
- PDF file upload UI & drag-and-drop ingestion components;
- OCR document parsing;
- Manual result entry forms;
- DuckDB persistent client cache;
- AI Coach narrative integration.
