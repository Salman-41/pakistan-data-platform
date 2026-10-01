# Analytical API

Start with `uvicorn pakdata.main:app --host 0.0.0.0 --port 8000`; set
`PAKDATA_DATA_DIR` to the ingestion output directory. OpenAPI is at `/docs`.
The public read-only API does not expose ingestion, SQL submission or writes.

| Route | Purpose |
| --- | --- |
| `/health` | Service and warehouse availability |
| `/api/v1/economy/indicators` | Actual ingested source/indicator/geography/frequency coverage |
| `/api/v1/economy/timeseries` | Parameterized series selection and transforms |
| `/api/v1/compare` | Matched-frequency pair comparison and correlations |
| `/api/v1/geography` | Geographic values present in the warehouse |
| `/api/v1/catalog` | Source manifests, usage terms, observed processing counts |
| `/api/v1/quality` | Validation, duplicates, missingness and timings from manifests |
| `/api/v1/trade`, `/population`, `/agriculture`, `/labour`, `/energy` | Domain-filtered source observations |
| `/api/v1/forecast`, `/anomalies` | Saved model reports; no model is trained during requests |
| `/api/v1/controlled-query` | Allowlisted operation dispatch through a Pydantic schema |

Timeseries parameters: `indicator` (required), `geography` (default Pakistan),
`dataset`, `frequency`, `start`, `end`, `limit` (1–5000), `offset`, `transform`
(`raw`, `pct_change`, `rolling_mean`, `index`) and `window` (2–120).
Transformed reads are capped at 20,000 observations and occur before pagination.
Rolling windows require all window observations. Percentage changes use adjacent
observed source periods, do not impute gaps, and return missing for zero
previous values. Indexing uses the first observed value as 100; a zero base is
undefined. Inputs from different source series are transformed independently.

The standard response is `{status, data, note}`. Empty requests explicitly return
`status: unavailable`. National observations are never broadcast to districts.
Domain matching currently uses controlled keyword filters over dataset and
indicator names; it is not a curated topic taxonomy. The geography endpoint
lists observed names; the separate GIS assets define available boundaries.

The comparison endpoint requires a single dataset/frequency per indicator and
identical frequency. Pearson/Spearman statistics use exactly matched observed
periods. Correlation does not establish causality; serial dependence can make
ordinary correlation p-values unreliable. This is displayed in the response.

DuckDB reads run with two threads and a 512 MB memory limit. Optional Redis
caches parameterized query results for 60 seconds, invalidated by warehouse
modification time. Redis failure falls back to normal queries. Per-process
request limiting allows 120 requests/client/minute. A multi-replica production
deployment should apply a shared gateway/Redis rate limiter; the local limiter
is not a global quota. CORS origins are an explicit environment allowlist.

PostgreSQL is a separately migrated mirror: `alembic upgrade head`, then
`python -m warehouse.load`. The loader requires manifests, streams 10,000-row
batches, upserts corrected observations and refreshes coverage. API analytics
currently read DuckDB, so PostgreSQL migration/loading must not be represented
as a verified PostgreSQL API implementation. Deploy a snapshot warehouse to
avoid simultaneous reader/writer DuckDB lock contention. Update the serving
snapshot after successful ingestion.
