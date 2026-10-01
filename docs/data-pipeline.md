# Pipeline

Download only identified official artifacts. Reviewed adapters produce canonical long CSV; original files remain under raw/. Ingestion hashes canonical inputs, copies Bronze originals, validates types/dates/finite values, normalizes explicit aliases, rejects invalid rows, deduplicates across chunks with DuckDB, writes typed Silver Parquet and year-partitioned Gold. A transaction updates facts and revision history; failed loads roll back.

Manifests track accepted/rejected/duplicate/missing records, file and database sizes, duration, quality and source/version. A score describes implemented checks, not proof of source truth. Raw_rows in the ingestion manifest means canonical input observations; source Excel physical rows are a different quantity. Publisher original artifacts are referenced by metadata and downloaded separately.

Incremental key upserts require source-defined stable identifiers and reviewed revisions. Jobs run explicitly through CLI; a distributed scheduler/retry queue is not implemented.
