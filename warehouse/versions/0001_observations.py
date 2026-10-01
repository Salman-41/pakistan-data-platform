"""Normalized public statistics warehouse with provenance, constraints and indexes."""
from alembic import op
revision='0001'
down_revision=None
branch_labels=None
depends_on=None

def upgrade():
    op.execute('''CREATE TABLE dim_dataset (dataset TEXT PRIMARY KEY, source_url TEXT NOT NULL, license TEXT, metadata JSONB NOT NULL DEFAULT '{}')''')
    op.execute('CREATE TABLE dim_indicator (indicator TEXT PRIMARY KEY, description TEXT)')
    op.execute("CREATE TABLE dim_geography (geography TEXT PRIMARY KEY, parent TEXT REFERENCES dim_geography(geography), geographic_level TEXT NOT NULL DEFAULT 'national')")
    op.execute('CREATE TABLE ingestion_run (id UUID PRIMARY KEY, dataset TEXT REFERENCES dim_dataset(dataset), started_at TIMESTAMPTZ NOT NULL, completed_at TIMESTAMPTZ, status TEXT NOT NULL CHECK(status IN (\'running\',\'completed\',\'failed\')), metrics JSONB NOT NULL DEFAULT \'{}\')')
    op.execute('''CREATE TABLE fact_observation (dataset TEXT REFERENCES dim_dataset(dataset), indicator TEXT REFERENCES dim_indicator(indicator), geography TEXT REFERENCES dim_geography(geography), period TEXT NOT NULL CHECK(period ~ '^\\d{4}(-\\d{2})?(-\\d{2})?$'), value DOUBLE PRECISION, unit TEXT NOT NULL, frequency TEXT NOT NULL, source_url TEXT NOT NULL, dataset_version TEXT NOT NULL, ingestion_id UUID REFERENCES ingestion_run(id), PRIMARY KEY(dataset,indicator,geography,period,unit,frequency))''')
    op.execute('CREATE INDEX ix_observation_series ON fact_observation(indicator, geography, period) INCLUDE(value,unit,frequency)')
    op.execute('CREATE INDEX ix_observation_dataset ON fact_observation(dataset,period)')
    op.execute('CREATE MATERIALIZED VIEW indicator_coverage AS SELECT dataset,indicator,geography,frequency,MIN(period) AS first_period,MAX(period) AS last_period,COUNT(*) AS observations FROM fact_observation GROUP BY dataset,indicator,geography,frequency')
    op.execute('CREATE UNIQUE INDEX ix_coverage_unique ON indicator_coverage(dataset,indicator,geography,frequency)')

def downgrade():
    for name in ['indicator_coverage','fact_observation','ingestion_run','dim_geography','dim_indicator','dim_dataset']:
        op.execute(('DROP MATERIALIZED VIEW ' if name=='indicator_coverage' else 'DROP TABLE ')+name)
