# Biomarkers & Laboratory Intelligence — Product Brief (Draft)

## 1. Product Vision & Goals

The **Biomarkers & Laboratory Intelligence** module extends the Athlete Platform with long-term tracking of laboratory blood work, urinalysis, and biological markers. By integrating lab results alongside daily health metrics (sleep, HRV, resting HR), body composition, and training load, the platform empowers athletes to observe physiological adaptations, track trends over time, and make informed lifestyle and recovery choices.

### Key Goals:
- **Import Flexibility**: Support ingestion of lab reports from digital PDFs, manual review/correction, manual entry, scans/OCR, and future external health record integrations.
- **Data Preservation & Provenance**: Store full measurement history via explicit `LaboratoryImportRun` instances, original source document hashes (SHA-256), and raw lab values alongside normalized values.
- **Normalization Boundary**: Standardize biomarker names and units across different lab providers (ALAB, Diagnostyka, Synevo, etc.) using versioned registries (`BiomarkerRegistry` and `UnitNormalizer`).
- **Contextual Transparency**: Store laboratory-provided reference ranges and critical flags while presenting athletic-context signals without altering official laboratory thresholds or inventing fake "athletic normal ranges".
- **Cautious Insights**: Highlight physiological correlations (e.g. low ferritin affecting endurance adaptation) without diagnosing diseases or providing medical prescriptions.

---

## 2. Supported Biomarker Categories

The module covers a broad range of biological markers relevant to athletic performance, recovery, and general well-being:

| Category Code | Category Name (PL) | Example Biomarkers |
|---|---|---|
| `morphology` | Morfologia | RBC, WBC, Hemoglobin, Hematocrit, Platelets, MCV, MCH, MCHC |
| `iron_panel` | Gospodarka żelazowa | Ferritin, Iron (Fe), TIBC, Transferrin Saturation |
| `hormones` | Hormony | TSH, fT3, fT4, Cortisol, Testosterone, DHEA-S |
| `lipids` | Lipidy | Total Cholesterol, HDL, LDL, Triglycerides |
| `vitamins` | Witaminy | Vitamin D (25-OH), Vitamin B12, Folate |
| `electrolytes` | Elektrolity | Sodium, Potassium, Magnesium, Calcium |
| `inflammatory_markers` | Markery zapalne | hs-CRP, ESR (OB) |
| `urinalysis` | Badania moczu | Specific gravity, pH, Protein, Glucose, Ketones |
| `other` | Inne biomarkery | Glucose, HbA1c, ALT, AST, Creatinine, Urea, Uric Acid |

---

## 3. Medical Safety & Liability Boundaries

The platform strictly demarcates athletic analytics from medical diagnosis and clinical treatment:

### The Platform CAN:
- Display chronological trends and longitudinal graphs.
- Display official laboratory-provided reference ranges and laboratory flags.
- Suggest consulting a physician or sports dietitian when markers fall outside reference bounds.
- Highlight physiological correlations relevant to recovery, training adaptation, and fatigue.

### The Platform CANNOT:
- Diagnose clinical conditions (e.g. "You have anemia").
- Recommend pharmaceutical treatments or drug dosage adjustments.
- Self-calculate urgent critical states or alter medical reference boundaries.

### Presentation Notification Levels (MVP):
- **`INFORMATIONAL`**: Result within lab reference range, stable trend.
- **`ATTENTION`**: Result near boundary or showing adverse trend for an athlete.
- **`CONSULT_CLINICIAN`**: Result outside lab reference range — medical consultation advised.

> [!NOTE]
> **Future Medical Policy**: `URGENT_REVIEW` is designated as a Future Medical Policy requirement. In MVP, if a laboratory report explicitly contains a `laboratory_provided_critical_flag` (e.g. lab panic value), the platform displays this lab-provided flag transparently without reinterpreting or self-generating urgent states.

---

## 4. Privacy & Data Deletion Policy

Laboratory reports contain sensitive health data (GDPR Special Category Data). The following privacy controls are enforced:

1. **No Source Files in Repository**: Original PDF files and lab scans are stored locally; they are **never** committed to version control.
2. **Synthetic Test Data Only**: All automated tests, fixtures, and documentation examples use synthetic mock data.
3. **SHA-256 Anonymized File Keys**: Imported files are identified by their SHA-256 digest (`source_document_hash`) rather than filenames (which may contain personal identifiers).
4. **Log Sanitization**: Application logs exclude raw biomarker values and personal identifiers.
5. **Data Deletion Semantics**:
   - Deleting a report removes the source file, `LaboratoryReport`, all `LaboratoryImportRun` instances, all `LaboratoryObservation` records, derivative AI Coach insights, and triggers a Read Model rebuild.
   - **Tombstone Retention Policy (Future Privacy Decision)**: Depending on final privacy governance, an optional minimal tombstone may record `deleted_at` and `is_tombstone: true`. In strict full erasure mode, `source_document_hash` is also purged to ensure zero lingering trace. Zero health metrics or lab values remain in tombstones or logs.
