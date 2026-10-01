# Warehouse design

The locally queryable DuckDB warehouse stores canonical `fact_observation`
records. Dataset, indicator, geography, period, unit and frequency uniquely
identify an observation. Corrections replace the current value; ingestion
retains source metadata and revision lineage. Dimension views are derived from
observed values rather than invented geographical allocations.

PostgreSQL migration `warehouse/versions/0001_observations.py` creates constrained
`dim_dataset`, `dim_indicator`, `dim_geography`, `ingestion_run` and
`fact_observation` tables. Geographic parents are self-referencing; district
hierarchies require an authoritative correspondence, not automatic assumptions
from names. `indicator_coverage` is a materialized view with a unique key for
future concurrent refreshes. Indexes cover indicator/geography/date lookup and
dataset/date lookup. Source documentation is retained as JSONB metadata.

The fact table remains in long observation form because heterogeneous national
statistics do not share customer/product-style entities. Population, inflation,
trade and agriculture are indicator families, not artificially populated empty
fact tables. Additional domain-specific grains should be introduced only when
real source dimensions support them.

Set `PAKDATA_DATABASE_URL=postgresql+psycopg://...`, then:

```sh
alembic upgrade head
python -m warehouse.load
```

The loading command streams DuckDB into 10,000-row SQLAlchemy batches in a
transaction, inserts observed dimensions, requires provenance manifests and
upserts source corrections. It refreshes coverage after a successful load.
The current mirror excludes ingestion foreign keys instead of inventing
operational ingestion-run records; complete provenance is in dataset metadata
and the DuckDB ingestion log. Deployment verification against a real PostgreSQL
service is necessary before treating the mirror as production tested.

Migration SQL can be reviewed without a live server:

```sh
PAKDATA_DATABASE_URL=postgresql+psycopg://review@localhost/review alembic upgrade head --sql
```

Use a read-only DuckDB serving snapshot. A pipeline writer and independently
running API reader must not share an active writable file across processes.
