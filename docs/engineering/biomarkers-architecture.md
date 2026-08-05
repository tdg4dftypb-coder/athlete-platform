# Biomarkers & Laboratory Intelligence — Architecture Specification (Draft)

## 1. Domain Architecture Overview

The Biomarkers module is designed as an independent domain boundary following Clean Architecture principles. It decouples document extraction (PDF/OCR) from biomarker alias matching (`BiomarkerRegistry`), unit conversion (`UnitNormalizer`), and decision engine integration (`AI Coach`).

```
                              [ Incoming Lab Report (PDF / Manual) ]
                                                │
                                                ▼
                                   [ SHA-256 Identity Check ]
                                                │
                                                ▼
                                  [ LaboratoryImportRun Created ]
                                                │
                                                ▼
                                  [ Document Extractor Port ]
                                                │
                                                ▼
                                      ( Raw Key-Value Rows )
                                                │
                                                ▼
                                   [ BiomarkerRegistry Port ]
                                                │
                        ┌───────────────────────┴───────────────────────┐
                        ▼                                               ▼
              ( Canonical Biomarker )                         ( Unresolved Biomarker )
                        │                                               │
                        ▼                                               ▼
             [ UnitNormalizer Port ]                         [ canonical_code = None ]
                        │                                    [ normalization_status = "unresolved" ]
                        ▼                                    [ requires_review = True ]
            ( Normalized Value & Unit )                                 │
                        │                                               ▼
                        └───────────────────────┬───────────────────────┘
                                                │
                                                ▼
                                    [ Confidence & Provenance ]
                                                │
                                                ▼
                                    [ LaboratoryRepository ]
                                                │
                                                ▼
                                 [ BiomarkersDashboardPayloadV1 ]
```

---

## 2. Updated Domain Data Models

```python
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional, Tuple, Dict, Any


class BiomarkerCategory(Enum):
    MORPHOLOGY = "morphology"
    IRON_PANEL = "iron_panel"
    HORMONES = "hormones"
    LIPIDS = "lipids"
    VITAMINS = "vitamins"
    ELECTROLYTES = "electrolytes"
    INFLAMMATORY_MARKERS = "inflammatory_markers"
    URINALYSIS = "urinalysis"
    OTHER = "other"


class BiomarkerValueType(Enum):
    NUMERIC = "numeric"
    QUALITATIVE = "qualitative"
    BOUNDED_INEQUALITY = "bounded_inequality"
    RANGE = "range"
    TEXT = "text"


class NormalizationStatus(Enum):
    RESOLVED = "resolved"
    UNRESOLVED = "unresolved"
    MANUALLY_OVERRIDDEN = "manually_overridden"


class VerificationStatus(Enum):
    UNVERIFIED = "unverified"
    USER_VERIFIED = "user_verified"
    REJECTED = "rejected"


class ImportRunStatus(Enum):
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    PARTIAL = "partial"
    FAILED = "failed"


class PlatformMessageLevel(Enum):
    INFORMATIONAL = "informational"
    ATTENTION = "attention"
    CONSULT_CLINICIAN = "consult_clinician"
    # URGENT_REVIEW is marked as Future Medical Policy


@dataclass(frozen=True)
class BiomarkerDefinition:
    canonical_code: str
    canonical_name: str
    category: BiomarkerCategory
    default_unit: str
    accepted_aliases: Tuple[str, ...]
    accepted_units: Tuple[str, ...]
    value_type: BiomarkerValueType
    interpretation_policy: str = "standard"
    active: bool = True


@dataclass(frozen=True)
class LaboratoryReferenceRange:
    reference_low: Optional[float] = None
    reference_high: Optional[float] = None
    reference_text: Optional[str] = None
    demographic_context: Optional[str] = None


@dataclass(frozen=True)
class LaboratoryObservation:
    observation_id: str
    report_id: str
    import_run_id: str
    report_row_index: int
    raw_name: str
    raw_value: str
    raw_unit: str
    collected_at: datetime
    
    # Biomarker Matching (Unresolved handling)
    canonical_code: Optional[str] = None  # None when unresolved!
    normalization_status: NormalizationStatus = NormalizationStatus.UNRESOLVED
    requires_review: bool = False
    alias_match_confidence: Optional[float] = None
    
    # Values & Units
    numeric_value: Optional[float] = None
    text_value: Optional[str] = None
    qualitative_value: Optional[str] = None
    inequality_operator: Optional[str] = None
    normalized_value: Optional[float] = None
    normalized_unit: Optional[str] = None
    
    # Reference Range & Laboratory Flags
    laboratory_reference_range: Optional[LaboratoryReferenceRange] = None
    laboratory_flag: Optional[str] = None  # e.g., "H", "L", "*" from lab
    laboratory_provided_critical_flag: Optional[str] = None  # Lab's own panic mark
    fasting_status: Optional[str] = None  # "fasting", "non_fasting", "unknown"
    
    # Platform Athletic Context & Signals (Separated from lab range)
    trend_status: Optional[str] = None  # "stable", "increasing", "decreasing", "insufficient_data"
    training_context_signal: Optional[str] = None
    platform_message_level: PlatformMessageLevel = PlatformMessageLevel.INFORMATIONAL
    
    # Separate Confidence Components (Draft / Future Policy)
    name_confidence: float = 1.0
    value_confidence: float = 1.0
    unit_confidence: float = 1.0
    reference_confidence: float = 1.0
    extraction_confidence: float = 1.0
    overall_confidence: float = 1.0
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    
    # Deduplication Fingerprint
    observation_source_fingerprint: str = ""
    is_possible_duplicate: bool = False
    
    reported_at: Optional[datetime] = None
    laboratory_name: Optional[str] = None
    source_type: str = "pdf_text"
    source_document_hash: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class LaboratoryImportRun:
    """Explicit run model for full ingestion provenance without data overwrites."""
    import_run_id: str
    report_id: str
    parser_version: str
    extractor_version: str
    registry_version: str
    unit_rules_version: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: ImportRunStatus = ImportRunStatus.IN_PROGRESS
    active: bool = True
    warnings: Tuple[str, ...] = ()
    observations: Tuple[LaboratoryObservation, ...] = ()


@dataclass(frozen=True)
class LaboratoryReport:
    report_id: str
    collected_at: datetime
    source_type: str
    source_document_hash: str
    import_runs: Tuple[LaboratoryImportRun, ...]
    reported_at: Optional[datetime] = None
    laboratory_name: Optional[str] = None
```

---

## 3. Unrecognized Biomarker Handling

When a raw lab name cannot be mapped to any `BiomarkerDefinition` in `BiomarkerRegistry`:
1. `canonical_code` is set strictly to `None` (never `"unknown_<slug>"`).
2. `normalization_status` is set to `NormalizationStatus.UNRESOLVED`.
3. `requires_review` is set to `True`.
4. The raw name, raw value, raw unit, and extracted numbers are preserved in full.
5. **Impact Constraint**: Unresolved observations are **excluded from trends, aggregate calculations, and AI Coach decision inputs**.

---

## 4. Value Parsing, Unit Conversion Engine & Confidence Assessment

### 4.1 Value Parser Contract (`ParsedLaboratoryValue`)
The value parser parses raw strings into structured types without medical interpretation or OCR dependency:
- Supports numeric (`14.2`), bounded inequalities (`< 0.01`, `>1000`), ranges (`12-16`), qualitative (`POSITIVE`, `NEGATIVE`, `Obecne`), and text (`Przejrzysty`).
- Preserves `raw_value` intact.

### 4.2 Unit Conversion Engine Contract (`UnitNormalizer` & `UnitAliasRegistry`)
- `UnitAliasRegistry`: Standardizes whitespace, Greek symbols (`μg/L`, `ug/L` → `µg/L`), and typographic capitalization variants (`mmol/l` → `mmol/L`).
- `UnitNormalizer`: Converts values using exact match `(biomarker_code, source_unit, target_unit)` with formula:
  $$\text{normalized} = \text{raw} \cdot \text{factor} + \text{offset}$$
- `UnitNormalizationResult`: Explicitly returns `converted: bool`, `normalized_value`, `normalized_unit`, `reason`. If no rule exists, retains raw source unit without guessing.

### 4.3 Confidence Components & Eligibility Policy (`ConfidenceComponents`)
Individual component scores (`name_confidence`, `value_confidence`, `unit_confidence`, `reference_confidence`, `extraction_confidence`, `verification_status`) are stored separately without hardcoded weight formulas or arbitrary cutoffs (e.g. 0.70/0.90).

#### Conservative Eligibility Rules (`evaluate_confidence_eligibility`):
- **`eligible_for_trends`**:
  - `normalization_status == RESOLVED`
  - Valid parsed value (numeric, inequality, qualitative, or text)
  - `verification_status != REJECTED`
- **`eligible_for_ai_coach`**:
  - Meets all `eligible_for_trends` criteria
  - `verification_status == VERIFIED` by user
  - `is_possible_duplicate == False`
  - No automated medical diagnosis conclusions

---

## 5. Medical Safety & Athletic Signals

Platform interpretations are strictly decoupled from official laboratory reference ranges:
- `laboratory_flag`: Raw flag provided by the testing laboratory (`"H"`, `"L"`, `"*"`).
- `laboratory_reference_range`: Official range provided on the lab report.
- `training_context_signal`: Athletic recovery or endurance signal.
- `platform_message_level`: Restricted in MVP to `INFORMATIONAL`, `ATTENTION`, and `CONSULT_CLINICIAN`.
- Results formally within the laboratory reference range receive only neutral trend information, never clinical diagnoses or custom "athletic normal ranges" without authoritative medical sources.

---

## 6. Ingestion Pipeline & Repository Ports

### 6.1 Ingestion Service (`LaboratoryIngestionService`)
The ingestion pipeline orchestrates document identity, extraction, row parsing, alias matching, unit normalization, duplicate detection, and repository persistence:
1. Calculates SHA-256 document hash (`SourceDocumentIdentity`). Rejects empty content.
2. Checks repository for duplicate document hash. If match found, returns `duplicate_document = True` without re-creating reports or observations.
3. Extractor port (`LaboratoryDocumentExtractor`) & Parser port (`LaboratoryResultParser`) extract raw rows (`RawLaboratoryRow`).
4. Processes each row into `LaboratoryObservation` using `BiomarkerRegistry` & `UnitNormalizer`.
5. Atomic Persistence: Saves `LaboratoryReport` & `LaboratoryImportRun` to `LaboratoryRepository` and activates run.

### 6.2 Reprocessing Use Case (`reprocess_report`)
- Reprocesses an existing `LaboratoryReport` using updated parser/registry versions.
- Creates a NEW `LaboratoryImportRun` attached to the same `report_id`.
- **Atomic Repository Invariant**: For any single `report_id`, there can exist at most **one** active `LaboratoryImportRun` (`active == True`). Activating a new run is executed as an atomic repository transaction:
  1. Deactivate all existing runs for `report_id` (`active = False`);
  2. Activate the new run (`active = True`);
  3. Commit in a single transaction.
- If reprocessing fails, the previous active run remains active and untouched.

---

## 7. Fingerprinting & Cross-Report Deduplication

- **Observation Fingerprint**:
  $$\text{Fingerprint} = \text{SHA256}(\text{source\_document\_hash} \parallel \text{report\_id} \parallel \text{import\_run\_id} \parallel \text{report\_row\_index} \parallel \text{raw\_name} \parallel \text{raw\_value} \parallel \text{raw\_unit} \parallel \text{collected\_at})$$
- **Cross-Report Duplicate Heuristic**:
  A new observation is flagged as `is_possible_duplicate = True` only if an active observation in another report matches `canonical_code`, `collected_at`, value (`numeric_value` / `normalized_value`), and unit.
- Yields warning count in `LaboratoryIngestionResult`; NO automatic merging or deletion occurs.

---

## 8. Data Deletion Semantics & Document Store

### 8.1 Deletion Modes (`DeletionMode`)
1. **`DELETE_DATA_KEEP_TOMBSTONE`**: Deletes source file from `SourceDocumentStore`, removes `LaboratoryReport`, all `LaboratoryImportRun` records, and all `LaboratoryObservation` instances. Retains minimal `TombstoneRecord` (`source_document_hash`, `deleted_at`, `is_tombstone = True`).
2. **`DELETE_EVERYTHING`**: Purges document file, reports, runs, observations, AND document hash tombstone.

### 8.2 Privacy-Safe Error & Logging Policy
- All domain exceptions (`EmptySourceDocumentError`, `LaboratoryIngestionError`, `ReportNotFoundError`, `LaboratoryDeletionError`) MUST NOT contain raw test values, test names, full file paths, or document health contents in exception messages.
- Raw health data is excluded from application debug logs.

---

## 9. Read Model Strategy & Public Serialization Contract (`BiomarkersDashboardPayloadV1`)

### 9.1 Read Model Architecture (`BiomarkersDashboard` & `BiomarkersDashboardBuilder`)
- Dedicated Read Model contract: **`BiomarkersDashboardPayloadV1`** (`contract_version = "1.0"`).
- Dedicated API endpoint: **`GET /api/v1/biomarkers`** served by `server/app.py`.
- `AthleteDashboardPayloadV1` remains strictly unchanged in Stage 13.
- Builder uses **ONLY active `LaboratoryImportRun` observations**. Inactive historical runs are excluded from current presentation.

### 9.2 Read Model Status Policy (`BiomarkersDashboardStatus`)
- **`UNAVAILABLE`**: 0 active reports OR 0 usable active observations.
- **`PARTIAL`**: Usable active observations exist, but limitations exist (unresolved items, unverified items, or possible duplicates).
- **`READY`**: Usable active observations exist with 0 unresolved, 0 unverified, 0 possible duplicates.
- Backend status is NOT based on whether a biomarker is "in range" or "out of range".

### 9.3 Technical Trend Computation Policy
- Evaluated only when $\ge 2$ non-rejected active observations exist for the same `canonical_code` with numeric values, compatible units, and distinct timestamps.
- Deterministic stability threshold:
  - $|\text{diff}| < 1e-4$: `"stable"`
  - $\text{diff} > 1e-4$: `"increasing"`
  - $\text{diff} < -1e-4$: `"decreasing"`
- Trend direction carries NO medical diagnostic interpretation or rating.

### 9.4 Completeness Semantics (`completeness_score`)
- Simple deterministic ratio of usable resolved active observations to all active observations (range `0.0` - `1.0`).
- Does NOT measure medical panel completeness or athletic norm compliance.

### 9.5 Public Serialization Contract (`BiomarkersDashboardSerializer`)
- Serializes `BiomarkersDashboard` into a JSON-native dictionary with ISO 8601 UTC strings.
- **Strict Privacy & Safety Boundary**:
  - `contract_version`: strictly `"1.0"`.
  - Excludes binary content, file names, and `source_document_hash`.
  - Excludes `raw_value` in public `unresolved_items` summary.
  - Excludes `NaN` and `Infinity`.
  - Presents `laboratory_flag` strictly as raw source string without AI diagnoses or treatment recommendations.

### 9.6 HTTP Boundary & Development Application Context (`server/app.py` & `biomarkers/composition.py`)
- Endpoint: **`GET /api/v1/biomarkers`**
- Composition Root: **`BiomarkersApplicationContext`** holding singletons for `repository`, `registry`, `unit_normalizer`, `ingestion_service`, and `clock`.
- Process-Wide Lifecycle: The development HTTP server process maintains one shared `BiomarkersApplicationContext` instance across requests, allowing ingestion services and read model endpoints to interact over the same repository state without resetting data between HTTP requests.
- Dependency Injection: `create_dashboard_wsgi_app(biomarkers_context=...)` factory enables clean context injection for integration tests without global monkeypatching.
- **CORS Policy & Hardening**:
  - Wildcard `Access-Control-Allow-Origin: *` is explicitly removed from `/api/v1/biomarkers`.
  - Client web application routes requests via Vite same-origin proxy (`/api` $\rightarrow$ `http://127.0.0.1:8000`).
- **Controlled Error Contract**:
  - Internal processing failures return HTTP `500 Internal Server Error` with `{"error": "Internal server error generating biomarkers payload"}`.
  - Zero stack traces, zero health metric leakage, zero document hashes in error payloads.

---

## 10. DuckDB Persistence Subsystem (Sprint 7A)

### 10.1 Database Selection & Rationale
The persistent DuckDB adapter uses a dedicated database file:
$$\text{Path: } \text{data/database/biomarkers.duckdb}$$

**Rationale for Dedicated Database**:
1. **Safety & Domain Isolation**: Decouples sensitive laboratory intelligence from core athlete metrics in `health.duckdb`, preventing accidental schema corruption or data loss during lab module iterations.
2. **Granular Privacy & Purge Control**: Enables independent backup, encryption, or full deletion (`DELETE_EVERYTHING`) without impacting core morning briefing metrics.
3. **Environment & Testing Safety**: `biomarkers.duckdb` is ignored by `.gitignore` (`*.duckdb`). Unit and integration tests run strictly against isolated temporary DuckDB files (`tmp_path`) or `:memory:`, ensuring zero mutation of production or local health databases.

### 10.2 Database Schema & Migration Strategy (`schema_version = 1`)
Managed by `biomarkers/persistence/schema.py` and `biomarkers/persistence/migrations.py`:
- `schema_version`: `version` (INTEGER PRIMARY KEY), `applied_at` (TIMESTAMP).
- `laboratory_reports`: `report_id`, `collected_at`, `reported_at`, `laboratory_name`, `source_type`, `source_document_hash`, `created_at`.
- `laboratory_import_runs`: `import_run_id`, `report_id`, `parser_version`, `extractor_version`, `registry_version`, `unit_rules_version`, `started_at`, `completed_at`, `status`, `active`, `warnings_json`.
- `laboratory_observations`: 45 domain columns mapping all `LaboratoryObservation` fields (`observation_id`, `import_run_id`, `report_id`, `report_row_index`, `raw_name`, `raw_value`, `raw_unit`, `canonical_code`, `normalization_status`, `requires_review`, `value_type`, `numeric_value`, `text_value`, `normalized_value`, `normalized_unit`, reference range, flags, confidence scores, verification status, metadata_json).
- `laboratory_tombstones`: `tombstone_id`, `source_document_hash`, `deleted_at`.

### 10.3 Idempotency, Tombstone Audit & Transactional Invariants
- `is_source_tombstoned(source_hash)`: Explicit contract method on `LaboratoryRepository`. Ingestion service checks `is_source_tombstoned()` BEFORE checking for existing report. Automatic re-ingestion of tombstoned document bytes returns controlled `status = FAILED`, `duplicate_document = True`, `report = None`, with zero reports/observations created.
- `save_report_with_import_run`: Atomically inserts/updates report header, import run header, and observations in a single DuckDB transaction (`BEGIN TRANSACTION` ... `COMMIT`). Any constraint or type failure triggers `ROLLBACK`.
- `activate_import_run`: Enforces ADR-012 invariant (at most 1 active run per `report_id`). If target run is invalid, transaction rolls back and previous active run remains active.
- `find_report_by_source_hash`: Checks `laboratory_tombstones` first. If tombstone exists, returns `None` to prevent accidental auto-resurrection.
- `delete_report`: Atomic single-transaction deletion supporting `DELETE_DATA_KEEP_TOMBSTONE` and `DELETE_EVERYTHING`.

### 10.4 Datetime Storage & UTC Round-Trip Policy
- Schema uses DuckDB `TIMESTAMP` types mapped via `to_naive_utc` (converts aware UTC datetimes to naive UTC for DuckDB) and `from_naive_utc` (attaches `timezone.utc` upon read).
- Eliminates external `pytz` module runtime dependencies.
- Guarantees 100% loss-free round-trip with `tzinfo == timezone.utc`, `utcoffset() == timedelta(0)`, and ISO 8601 string formatting retaining `+00:00`.

### 10.5 Schema Compatibility & Future Version Protection
- Migration runner checks `schema_version`.
- Re-running migrations on an existing database is idempotent.
- Higher unknown `schema_version` (e.g. `version > 1`) raises a controlled `ValueError` to prevent schema corruption or unintentional downgrade.

### 10.6 Composition & Environment Configuration
- `BIOMARKERS_REPOSITORY`: Configurable via `build_repository_from_env()`.
  - `"in_memory"` (default for fast unit testing and lightweight mock runtime)
  - `"duckdb"` (persistent runtime using `BIOMARKERS_DB_PATH` or `data/database/biomarkers.duckdb`).

---

## 11. Text PDF Extraction & Import Subsystem (Sprint 7B)

### 11.1 Document Extractor Adapter (`PdfTextLaboratoryDocumentExtractor`)
- Lightweight pure-Python dependency: `pypdf>=5.0.0`.
- Extractor Port: `PdfTextLaboratoryDocumentExtractor` implements `LaboratoryDocumentExtractor`.
- Accepts binary content bytes (`content: bytes`).
- Rejects empty documents (`InvalidPdfDocumentError`) and non-PDF files without `%PDF` magic header.
- Detects PDFs without text layer (scanned images) and raises `PdfTextLayerUnavailableError`. OCR is explicitly disabled.

### 11.2 Text Report Parser (`TextLaboratoryReportParser`)
- Deterministic parser for digital Polish / European laboratory PDF reports (Synevo, Diagnostyka, ALAB).
- Extract Header: Automatically detects `collected_at` (Data pobrania), `reported_at`, and `laboratory_name`. Print dates are NOT treated as collection dates.
- Extract Rows:
  - Table rows separated by `|` or regex column patterns.
  - Handles integer and decimal values with commas (`14,2`) or dots (`14.2`).
  - Handles bounded inequalities (`< 0.01`, `> 1000`) and ranges (`12–16`).
  - Handles qualitative values (`Dodatni`, `Ujemny`, `Obecne`).
  - Preserves laboratory flags (`"H"`, `"L"`, `"*"`).
  - Handles wrapped biomarker names across multiple lines.
  - Skips page headers, footers, page numbers (`Strona 1 z 2`), and lab signatures.

### 11.3 Use Case Orchestration & Dry-Run Mode (`ImportLaboratoryPdfUseCase`)
- Orchestrates PDF Extraction $\rightarrow$ Report Parsing $\rightarrow$ Ingestion Pipeline $\rightarrow$ DuckDB Persistence.
- `--dry-run` Mode: Executes extraction, parsing, alias matching, and unit normalization against a transient in-memory repository without writing to DuckDB database or creating persistent records.

### 11.4 CLI Utility (`scripts/import_laboratory_pdf.py`)
- Command line interface for importing digital PDF laboratory reports.
- Privacy & Safety Policy:
  - ZERO health values (`raw_value`), test names, or patient data printed to `stdout` / `stderr`.
  - ZERO full extracted text printed or saved to disk.
  - Controlled privacy-safe error messages with non-zero exit codes.

---

## 12. ALAB Report Parser & Biomarker Registry Hardening (Sprint 7C)

### 12.1 Specialized ALAB Parser (`AlabTextLaboratoryReportParser`)
- Format Auto-Detection: `can_parse()` detects ALAB laboratoria headers and section text.
- Parser Selection Boundary (`get_report_parser_for_document`): Automatically dispatches to `AlabTextLaboratoryReportParser` when ALAB signature is present, preserving `TextLaboratoryReportParser` as generic fallback.
- Header Date Parsing: Extracts `data i godz. pobrania:` across document sections. Sets `collected_at` if exactly one unique collection date is present. Does not substitute execution date or print date.
- Multiline Result Rows: Correctly associates wrapped biomarker names on line $N-1$ with numeric results on line $N$ without prepending section titles (`Morfologia krwi`, `Układ krzepnięcia`).
- Qualitative & One-Sided Bounds: Supports qualitative values (`nieobecny`, `obecny`), single-sided reference bounds (`< 500`, `< 0,04`), and distinct numeric vs qualitative marker pairs (`HBsAg`).

### 12.2 BiomarkerRegistry & Unit Registry Expansion
- Comprehensive Polish ALAB Aliases: Added explicit aliases for complete CBC morphology, white blood cell differential (`WBC`, `NEU#`, `NEU%`, `LYMPH#`, `LYMPH%`, `MON#`, `MON%`, `EOS#`, `EOS%`, `BASO#`, `BASO%`, `IG#`, `IG%`), coagulation (`APTT`, `PT`, `INR`, `D-dimer`), and immunochemistry (`HBsAg`).
- Distinct Canonical Codes: Strictly separates `rdw_cv` (percentage `%`) from `rdw_sd` (femtoliters `fL`), `hbs_antigen_numeric` from `hbs_antigen_qualitative`.
- Unit Normalization Aliases: Maps ALAB representations (`10^3/µl`, `10^6/µl`, `fL`, `pg`, `sek`, `ng/mL FEU`, `S/CO`).

---

## 13. ALAB Import Accounting & Completeness Audit (Sprint 7C.1)

### 13.1 Strict Accounting Invariants
- Enforces strict line and observation accounting across parser, ingestion, and CLI summary:
  $$\text{imported\_observations\_count} = \text{resolved\_observations\_count} + \text{unresolved\_observations\_count}$$
- Metrics defined:
  - `candidate_rows_count`: Total non-empty text lines examined.
  - `ignored_lines_count`: Lines identified as headers, footers, page numbers, clinical comments, or section/group titles.
  - `extracted_rows_count`: Valid result lines parsed into `RawLaboratoryRow`.
  - `failed_rows_count`: Lines attempting result match but failing syntax.
  - `imported_observations_count`: `LaboratoryObservation` records created.
  - `resolved_observations_count`: Observations matched to valid `canonical_code`.
  - `unresolved_observations_count`: Observations without canonical code match.
  - `accuracy_percentage`: $\frac{\text{resolved\_observations\_count}}{\text{imported\_observations\_count}} \times 100\%$. Ignored comments and headers are strictly excluded from denominator.

### 13.2 Format & Parser Hardening for Real ALAB PDF
- Trailing Method Notes: `result_line_pattern` accepts trailing method text (e.g. `Instrukcja Abbott`), capturing value `0,37` and unit `S/CO` cleanly.
- Lab Code Tag Stripping: `match_alias` strips trailing lab test code tags (e.g. `(G49)`, `(V39)`, `(G37)`, `(G11)`) before lookup.
- Spaced-Hyphen Aliases: Added spaced-hyphen alias support (`"czas kaolinowo - kefalinowy"` $\rightarrow$ `aptt`).
- HBsAg Contextual Resolution: Differentiates `hbs_antigen_numeric` (numeric value with `S/CO` unit) from `hbs_antigen_qualitative` (qualitative value `"nieobecny"`).
- RDW Contextual Resolution: Differentiates `rdw_cv` (`%` unit) from `rdw_sd` (`fL` unit).
- Group Header Filtering: Ignores group title lines (`Czas protrombinowy (PT), INR/`) without creating empty or duplicate observations.

---

## 14. Result Row Qualification and PII Filtering (Sprint 7C.2)

### 14.1 UNRESOLVED Observation Semantics & PII Boundary
- **Domain Definition**: An `UNRESOLVED` observation MUST represent a structurally valid laboratory test result (name + value + unit or qualitative result or known unitless marker) that lacks a matching `canonical_code` in `BiomarkerRegistry`.
- **Strict PII & Admin Exclusion**: `UNRESOLVED` MUST NEVER include patient metadata (name, PESEL, address, DOB, patient ID), clinician details (ordering doctor, diagnostician signature), lab administration (phone, email, address, footers), or technical metadata (method, analyzer, page numbers).

### 14.2 LaboratoryResultRowQualifier Engine
- **Row Qualification Criteria**: A document text line is qualified into a candidate result row ONLY if it satisfies at least one of 4 criteria:
  - Criteria A: Name + numeric value + unit (e.g. `Hemoglobina (HGB) 14.8 g/dL`).
  - Criteria B: Name + qualitative result (e.g. `HBsAg nieobecny`).
  - Criteria C: Name + numeric value for unitless marker (e.g. `INR 1,02`).
  - Criteria D: Multiline name buffer + numeric value/unit on next line (e.g. `APTT` line 1 $\rightarrow$ `28,6 sek` line 2).
- **PII & Admin Rejection**: Rejects lines matching `ADMIN_PII_PATTERNS` before result parsing without writing raw PII to logs, warnings, or DuckDB storage.

### 14.3 Strict Accounting Invariants
- Enforces unambiguous accounting metrics:
  $$\text{candidate\_lines} = \text{ignored\_non\_result\_lines} + \text{malformed\_result\_rows} + \text{parsed\_result\_rows}$$
  $$\text{parsed\_result\_rows} = \text{imported\_observations}$$
  $$\text{imported\_observations} = \text{resolved\_observations} + \text{unresolved\_observations}$$
- `accuracy_percentage`: $\frac{\text{resolved\_observations}}{\text{imported\_observations}} \times 100\%$. 100% accuracy achieved on real ALAB report with zero false administrative unresolved items.
