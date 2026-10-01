# Architecture decisions

The canonical fact has dataset, indicator, geography, period, value, unit, frequency, source URL, version and ingestion ID. One observation is one source-defined measurement, never an inferred district estimate. Source-domain fact tables in PostgreSQL mirror semantic domains; runtime DuckDB uses a single bounded analytical observation table.

Immutable source hashes and per-run manifests support lineage. Revisions are recorded before key-based replacement. Gold partitions are ingestion-specific: readers must use the warehouse's resolved facts, not concatenate every historical partition and double-count revisions.

Local development runs an API against a read-only snapshot and a separate ingestion command. Do not write snapshots while API readers hold connections: generate offline and restart/swap at a controlled boundary. PostgreSQL mirror and optional Redis are separate components. Full scale should use isolated ingestion compute and verified indexes; no scale certification exists yet.
