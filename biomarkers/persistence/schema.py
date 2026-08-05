"""
DuckDB Schema DDL Statements for Biomarkers Domain.
Uses TIMESTAMP for native DuckDB datetime compatibility without pytz dependency.
"""

CREATE_SCHEMA_VERSION_TABLE = """
CREATE TABLE IF NOT EXISTS schema_version (
    version INTEGER PRIMARY KEY,
    applied_at TIMESTAMP NOT NULL
);
"""

CREATE_LABORATORY_REPORTS_TABLE = """
CREATE TABLE IF NOT EXISTS laboratory_reports (
    report_id VARCHAR PRIMARY KEY,
    collected_at TIMESTAMP NOT NULL,
    reported_at TIMESTAMP,
    laboratory_name VARCHAR,
    source_type VARCHAR NOT NULL,
    source_document_hash VARCHAR NOT NULL,
    created_at TIMESTAMP NOT NULL
);
"""

CREATE_LABORATORY_IMPORT_RUNS_TABLE = """
CREATE TABLE IF NOT EXISTS laboratory_import_runs (
    import_run_id VARCHAR PRIMARY KEY,
    report_id VARCHAR NOT NULL,
    parser_version VARCHAR NOT NULL,
    extractor_version VARCHAR NOT NULL,
    registry_version VARCHAR NOT NULL,
    unit_rules_version VARCHAR NOT NULL,
    started_at TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    status VARCHAR NOT NULL,
    active BOOLEAN NOT NULL DEFAULT FALSE,
    warnings_json VARCHAR NOT NULL DEFAULT '[]'
);
"""

CREATE_LABORATORY_OBSERVATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS laboratory_observations (
    observation_id VARCHAR PRIMARY KEY,
    import_run_id VARCHAR NOT NULL,
    report_id VARCHAR NOT NULL,
    report_row_index INTEGER NOT NULL,
    observation_source_fingerprint VARCHAR NOT NULL,
    raw_name VARCHAR NOT NULL,
    raw_value VARCHAR NOT NULL,
    raw_unit VARCHAR NOT NULL,
    canonical_code VARCHAR,
    normalization_status VARCHAR NOT NULL,
    requires_review BOOLEAN NOT NULL,
    alias_match_confidence DOUBLE,
    value_type VARCHAR NOT NULL,
    numeric_value DOUBLE,
    text_value VARCHAR,
    qualitative_value VARCHAR,
    inequality_operator VARCHAR,
    range_low DOUBLE,
    range_high DOUBLE,
    normalized_value DOUBLE,
    normalized_unit VARCHAR,
    ref_low DOUBLE,
    ref_high DOUBLE,
    ref_text VARCHAR,
    ref_unit VARCHAR,
    ref_lab_provided BOOLEAN,
    laboratory_flag VARCHAR,
    laboratory_provided_critical_flag VARCHAR,
    collected_at TIMESTAMP NOT NULL,
    reported_at TIMESTAMP,
    laboratory_name VARCHAR,
    source_type VARCHAR NOT NULL,
    source_document_hash VARCHAR,
    name_confidence DOUBLE NOT NULL,
    value_confidence DOUBLE NOT NULL,
    unit_confidence DOUBLE NOT NULL,
    reference_confidence DOUBLE NOT NULL,
    extraction_confidence DOUBLE NOT NULL,
    overall_confidence DOUBLE NOT NULL,
    verification_status VARCHAR NOT NULL,
    trend_status VARCHAR,
    training_context_signal VARCHAR,
    platform_message_level VARCHAR NOT NULL,
    is_possible_duplicate BOOLEAN NOT NULL DEFAULT FALSE,
    metadata_json VARCHAR NOT NULL DEFAULT '{}'
);
"""

CREATE_LABORATORY_TOMBSTONES_TABLE = """
CREATE TABLE IF NOT EXISTS laboratory_tombstones (
    tombstone_id VARCHAR PRIMARY KEY,
    source_document_hash VARCHAR NOT NULL,
    deleted_at TIMESTAMP NOT NULL
);
"""
