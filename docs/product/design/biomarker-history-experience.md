# Biomarker History Experience — Design & UX Specification (Sprint 7F)

## 1. Overview

The **Biomarker History Experience** is a focused screen presenting the complete measurement timeline for a single canonical biomarker. It is accessed by tapping any biomarker in the Biomarkers list.

No charts or trend analysis are displayed in this sprint. The goal is a clear, honest, readable history of all available measurements.

---

## 2. Navigation

### Entry point

From the **Biomarkers** screen (`?view=biomarkers`):

> Every biomarker row is tappable (keyboard and pointer accessible). Clicking navigates to:

```
?view=history&code={canonical_code}
```

Example: `?view=history&code=ferritin`

### Back navigation

The page header includes a back button (←) that returns the user to `?view=biomarkers`.

### URL scheme (developer)

| Parameter | Value |
|-----------|-------|
| `view` | `history` |
| `code` | Canonical biomarker slug, e.g. `ferritin`, `glucose`, `hbsag` |

---

## 3. Presentation States

The History view handles 4 states:

| State | Trigger | Display |
|-------|---------|---------|
| `loading` | HTTP fetch in progress | Skeleton cards with pulse animation |
| `ready` | Valid payload, ≥1 measurement | Hero card + full measurement list |
| `unavailable` | 404 from API, empty history | "Brak historii pomiarów." message |
| `failure` | Network error, parse error | Error title + message |

---

## 4. Screen Layout

### Header

```
┌────────────────────────────────┐
│ ←   Ferrytyna                  │  ← h1, display_name from payload
│      2 pomiary                 │  ← subtitle: count
└────────────────────────────────┘
```

### Hero Card (latest measurement)

```
┌────────────────────────────────┐
│  OSTATNI WYNIK                 │
│                                │
│  38,00 ng/mL                   │  ← bold, large
│  10 kwi 2026  •  Flaga lab: L  │  ← date, flag badge
│  Niezweryfikowane               │  ← verification label
└────────────────────────────────┘
```

### Measurement List

Full list — newest first (reverse chronological for intuitive reading):

```
┌────────────────────────────────┐
│  Historia pomiarów (2)         │  ← h2 with count
│                                │
│  ┌──────────────────────────┐  │
│  │ 10 kwi 2026        38 ng/mL │
│  │ Flaga laboratorium: L    │  │
│  │ Niezweryfikowane         │  │
│  └──────────────────────────┘  │
│                                │
│  ┌──────────────────────────┐  │
│  │ 15 sty 2026      42,5 ng/mL │
│  │ Zweryfikowano            │  │
│  └──────────────────────────┘  │
└────────────────────────────────┘
```

### Qualitative measurement (no unit)

```
│ 01 mar 2026       Nieobecny   │
│ Niezweryfikowane              │
```

### Empty history

```
│  Historia pomiarów (0)         │
│  Brak historii pomiarów.        │
```

---

## 5. Ordering

The backend delivers measurements **oldest → newest**. The view reverses this for display (newest first) to match standard lab report conventions. The underlying `HistoryPresentation.measurements` array retains original API order; reversal is applied only at render time.

---

## 6. Privacy Boundary

The History Experience **never displays**:

| Field | Reason |
|-------|--------|
| `observation_id` | Internal repository key |
| `report_id` | Internal repository key |
| `import_run_id` | Provenance metadata |
| `source_document_hash` | Document fingerprint |
| `filename` | Local filesystem path |
| `original_filename` | Local filesystem path |
| `raw_value` | Unprocessed lab string |

Privacy is enforced at **two levels**:
1. **Parser** (`history-payload-parser.ts`) rejects any payload containing forbidden fields before data reaches the UI.
2. **Presentation model** (`history-presentation.ts`) exposes only whitelisted display-ready fields.

---

## 7. Architecture

```
HTTP API  GET /api/v1/biomarkers/history/{canonical_code}
  │
  ↓
HistoryPayloadSource       history-payload-source.ts
  │  load(code) → Promise<unknown>
  │  Throws HistoryNotFoundError (404) / HistoryInvalidCodeError (400)
  ↓
HistoryPayloadParser        history-payload-parser.ts
  │  parseHistoryPayloadV1(unknown) → ParseResult<HistoryPayloadV1>
  │  Privacy guard + structural validation
  ↓
HistoryPresentation         history-presentation.ts
  │  mapHistoryPayloadToPresentation() → HistoryPresentation
  │  Locale-aware formatting, no backend types exposed
  ↓
HistoryExperienceView       history-experience-view.ts
  │  createHistoryExperienceApp(state, onBack) → HTMLElement
  │  4 states: loading | ready | failure | unavailable
```

**Files created:**
| File | Role |
|------|------|
| `src/biomarkers/history/history-payload-source.ts` | HTTP fetch |
| `src/biomarkers/history/history-payload-parser.ts` | Validation + privacy guard |
| `src/biomarkers/history/history-presentation.ts` | Presentation model + mapper |
| `src/biomarkers/history/history-experience-view.ts` | DOM renderer |
| `tests/history.test.ts` | 29 test scenarios |

**Files modified:**
| File | Change |
|------|--------|
| `src/app/view-routing.ts` | Added `"history"`, `resolveHistoryCode()`, `searchForHistory()` |
| `src/main.ts` | History preview + HTTP render branches, `openBiomarkers()` helper |
| `src/biomarkers/biomarkers-experience-view.ts` | Clickable biomarker items → history navigation |
