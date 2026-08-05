# Biomarkers Experience Product Design & Implementation

## 1. Executive Summary & Purpose
The **Biomarkers Experience** in AthleteWeb provides a clear, data-honest presentation of laboratory results and blood test history.

The interface is built around the UX philosophy **"Insights before Metrics"**, answering four primary user questions in the first 5 seconds:
1. **Do my results require attention?**
2. **What changed since the last lab test?**
3. **What data is available?**
4. **Which items require manual review?**

---

## 2. Screen Structure & Layout Hierarchy

The screen follows a strict top-down visual hierarchy aligned with AthleteWeb design tokens:

```
┌─────────────────────────────────────────────────────────┐
│ 1. Header (Title: "Wyniki badań", Date & Back nav)      │
├─────────────────────────────────────────────────────────┤
│ 2. Hero Summary (Status message & Stat pills)           │
│    - Status: "Twoje wyniki są uporządkowane..."         │
│    - Pills: Total Reports, Biomarkers, Unresolved, Date │
│    - Data Import Quality: "Jakość importu danych: XX%"  │
├─────────────────────────────────────────────────────────┤
│ 3. Data Quality & Limitations (Source limitations only) │
├─────────────────────────────────────────────────────────┤
│ 4. Biomarker Categories (Collapsible Accordions)        │
│    - Morfologia, Gospodarka żelazowa, Witaminy, etc.    │
│    - Biomarker rows: Name, Value, Unit, Lab Flag, Trend │
├─────────────────────────────────────────────────────────┤
│ 5. Unresolved Items ("Do weryfikacji")                  │
│    - Raw Name, Raw Unit, Collection Date, Reason        │
│    - Privacy assertion: ZERO raw_value displayed        │
├─────────────────────────────────────────────────────────┤
│ 6. Data Quality Summary (Import breakdown footer)       │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Presentation States

1. **`READY`**:
   - Hero message: *"Twoje wyniki są uporządkowane i gotowe do przeglądu."*
   - Displays all categories, trend directions, and summary pills.
2. **`PARTIAL`**:
   - Hero message: *"Część wyników wymaga uzupełnienia lub weryfikacji."*
   - Displays accessible categories alongside the *"Do weryfikacji"* section.
3. **`UNAVAILABLE`**:
   - Hero message: *"Nie masz jeszcze dodanych wyników badań."*
   - Description: *"Po dodaniu raportu zobaczysz historię i zmiany biomarkerów."*
   - Visual action placeholder: *"Dodaj wyniki"* (non-functional visual placeholder).
4. **`STALE`**:
   - Retains the last valid presentation.
   - Notice: *"Widok danych nie był ostatnio odświeżany."* (Indicates HTTP payload freshness age, NOT medical invalidity).
5. **`LOADING`**:
   - Layout-preserving skeleton loader with `aria-busy="true"`.
6. **`FAILURE`**:
   - Neutral message: *"Nie udało się pobrać wyników badań."*
   - Retry action button without technical stack traces.

---

## 4. Medical Safety & Data Honesty Rules

- **Neutral Trend Direction**: Trends are labeled neutrally as *"Rośnie"*, *"Maleje"*, *"Bez wyraźnej zmiany"*, or *"Brak trendu"*. Increasing or decreasing trends are never automatically rated as "good" or "bad".
- **Raw Laboratory Flags**: Laboratory flags (e.g. `H`, `L`) are displayed strictly as source information (*"Flaga laboratorium: H"*).
- **No Clinical Diagnoses or Custom Norms**: No automated medical diagnoses (e.g. "anemia", "deficiency") or custom "athletic normal ranges" are invented or presented.
- **Import Quality Score**: `completeness_score` is labeled *"Jakość importu danych"* to prevent users from mistaking it for a medical health rating.

---

## 5. Navigation & Dev Routing

- **Dev View Route**: `?view=biomarkers`
- **State Overrides**: `?view=biomarkers&state=ready|partial|unavailable|stale|loading|failure`
- **HTTP Source Mode**: `?view=biomarkers&source=http`
- **More View Integration**: Accessible via the *"Wyniki badań (Biomarkers)"* card in the **More** view.
- **Bottom Navigation**: The bottom navigation tab **"Więcej" ("more") remains ACTIVE** while viewing `?view=biomarkers`.

---

## 6. Excluded Scope (Prior to Future Stages)
- PDF file upload & drag-and-drop ingestion UI;
- OCR document parsing;
- Manual result entry forms;
- DuckDB persistent client database;
- AI Coach narrative recommendations.
