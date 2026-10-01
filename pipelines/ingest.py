from __future__ import annotations

import hashlib
import json
import shutil
import time
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import polars as pl
import pyarrow as pa
import pyarrow.parquet as pq

COLUMNS = ['dataset', 'indicator', 'geography', 'period', 'value', 'unit', 'frequency', 'source_url']
KEY = ['dataset', 'indicator', 'geography', 'period', 'unit', 'frequency']


@dataclass(frozen=True)
class Metadata:
    source: str
    source_url: str
    retrieval_date: str
    original_file: str
    dataset_version: str
    geographic_level: str
    time_period: str
    ingestion_status: str = 'retrieved'
    license: str = 'Usage terms require source-specific review'

    def __post_init__(self):
        for key, value in asdict(self).items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f'Metadata {key} must be a nonempty string')
        datetime.fromisoformat(self.retrieval_date.replace('Z', '+00:00'))
        if not self.source_url.startswith('https://'):
            raise ValueError('Provenance source_url must use HTTPS')


def digest(path: Path) -> str:
    result = hashlib.sha256()
    with path.open('rb') as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b''):
            result.update(block)
    return result.hexdigest()


def initialize(connection):
    connection.execute('''CREATE TABLE IF NOT EXISTS fact_observation (
        dataset VARCHAR NOT NULL, indicator VARCHAR NOT NULL, geography VARCHAR NOT NULL,
        period DATE NOT NULL, value DOUBLE NOT NULL, unit VARCHAR NOT NULL,
        frequency VARCHAR NOT NULL, source_url VARCHAR NOT NULL,
        dataset_version VARCHAR NOT NULL, ingestion_id VARCHAR NOT NULL,
        PRIMARY KEY(dataset,indicator,geography,period,unit,frequency))''')
    connection.execute('''CREATE TABLE IF NOT EXISTS ingestion_log (
        ingestion_id VARCHAR PRIMARY KEY, source_hash VARCHAR, source_url VARCHAR,
        dataset_version VARCHAR, manifest_path VARCHAR, completed_at TIMESTAMP)''')
    connection.execute('''CREATE TABLE IF NOT EXISTS observation_revision (
        dataset VARCHAR, indicator VARCHAR, geography VARCHAR, period DATE,
        unit VARCHAR, frequency VARCHAR, old_value DOUBLE, new_value DOUBLE,
        previous_ingestion_id VARCHAR, ingestion_id VARCHAR, changed_at TIMESTAMP)''')


def ingest_csv(path, metadata, data_dir, chunk_size=50000):
    """Ingest an explicitly normalized long CSV; no heuristic source layout guesses.

    Incremental keys are dataset/indicator/geography/date/unit/frequency. Same-file
    duplicates keep the first occurrence. Changed values on later ingestion are
    recorded in observation_revision before replacement. Raw files are immutable.
    """
    if isinstance(metadata, dict):
        metadata = Metadata(**metadata)
    if chunk_size < 1:
        raise ValueError('chunk_size must be positive')
    path, root = Path(path), Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    source_hash = digest(path)
    ingestion_id = uuid.uuid4().hex
    start = time.perf_counter()
    connection = duckdb.connect(str(root / 'warehouse.duckdb'))
    connection.execute("SET memory_limit='512MB'")
    connection.execute('SET threads=2')
    initialize(connection)
    existing = connection.execute('SELECT manifest_path FROM ingestion_log WHERE source_hash=? AND source_url=? AND dataset_version=?', [source_hash, metadata.source_url, metadata.dataset_version]).fetchone()
    if existing:
        connection.close()
        manifest = json.loads(Path(existing[0]).read_text())
        return {**manifest, 'idempotent': True, 'ingestion_status': 'already_ingested'}
    bronze = root / 'bronze' / source_hash
    bronze.mkdir(parents=True, exist_ok=True)
    raw_copy = bronze / 'source.csv'
    if not raw_copy.exists():
        shutil.copyfile(path, raw_copy)
    (bronze / f'provenance-{ingestion_id}.json').write_text(json.dumps(asdict(metadata), indent=2))
    silver = root / 'silver' / ingestion_id
    silver.mkdir(parents=True, exist_ok=True)
    counts = dict(raw_rows=0, processed_rows=0, rejected_rows=0, duplicates=0, missing_values=0, revisions=0, inserted_rows=0)
    files = []
    transaction_active = False
    try:
        connection.execute('BEGIN')
        transaction_active = True
        connection.execute('CREATE TEMP TABLE seen AS SELECT * FROM fact_observation WHERE false')
        for number, frame in enumerate(pd.read_csv(path, chunksize=chunk_size, dtype=str, keep_default_na=False)):
            missing_columns = set(COLUMNS) - set(frame.columns)
            if missing_columns:
                raise ValueError(f'Missing canonical columns: {sorted(missing_columns)}')
            frame = frame[COLUMNS].copy()
            counts['raw_rows'] += len(frame)
            for column in COLUMNS:
                frame[column] = frame[column].str.strip()
            counts['missing_values'] += int(frame.eq('').sum().sum())
            frame['value'] = pd.to_numeric(frame['value'], errors='coerce')
            frame['period'] = pd.to_datetime(frame['period'], errors='coerce', format='ISO8601', utc=True).dt.date
            valid = frame[['dataset','indicator','geography','unit','frequency']].ne('').all(axis=1) & frame.period.notna() & np.isfinite(frame.value) & frame.source_url.eq(metadata.source_url)
            valid &= frame.frequency.isin(['daily', 'weekly', 'monthly', 'quarterly', 'annual', 'census', 'irregular'])
            counts['rejected_rows'] += int((~valid).sum())
            frame = frame.loc[valid].copy()
            frame['dataset_version'], frame['ingestion_id'] = metadata.dataset_version, ingestion_id
            arrow_schema = pa.schema([(name, pa.date32() if name == 'period' else pa.float64() if name == 'value' else pa.string()) for name in frame.columns])
            connection.register('incoming', pa.Table.from_pandas(frame, schema=arrow_schema, preserve_index=False))
            join = ' AND '.join(f'i.{k}=s.{k}' for k in KEY)
            connection.execute(f'''CREATE OR REPLACE TEMP TABLE accepted AS
              SELECT i.* FROM incoming i WHERE NOT EXISTS (SELECT 1 FROM seen s WHERE {join})
              QUALIFY row_number() OVER(PARTITION BY {','.join(KEY)} ORDER BY ingestion_id)=1''')
            accepted_count = connection.execute('SELECT count(*) FROM accepted').fetchone()[0]
            counts['duplicates'] += len(frame) - accepted_count
            counts['processed_rows'] += accepted_count
            connection.execute('INSERT INTO seen SELECT * FROM accepted')
            old_join = ' AND '.join(f'a.{k}=f.{k}' for k in KEY)
            revisions = connection.execute(f'SELECT count(*) FROM accepted a JOIN fact_observation f ON {old_join} WHERE a.value<>f.value').fetchone()[0]
            counts['revisions'] += revisions
            counts['inserted_rows'] += connection.execute(f'SELECT count(*) FROM accepted a WHERE NOT EXISTS (SELECT 1 FROM fact_observation f WHERE {old_join})').fetchone()[0]
            connection.execute(f'''INSERT INTO observation_revision SELECT a.dataset,a.indicator,a.geography,a.period,a.unit,a.frequency,f.value,a.value,f.ingestion_id,a.ingestion_id,current_timestamp FROM accepted a JOIN fact_observation f ON {old_join} WHERE a.value<>f.value''')
            connection.execute('INSERT OR REPLACE INTO fact_observation SELECT * FROM accepted')
            # Arrow exports one bounded chunk; lazy Polars provides chunk quality summary.
            arrow = connection.execute('SELECT * FROM accepted').fetch_arrow_table()
            parquet = silver / f'part-{number:06d}.parquet'
            pq.write_table(arrow, parquet, compression='zstd', row_group_size=min(chunk_size, 50000))
            files.append(str(parquet))
        gold = root / 'gold'
        gold.mkdir(exist_ok=True)
        # Export partitioned aggregate facts directly from DuckDB, without Python RAM.
        target = gold / ingestion_id
        escaped_target = str(target).replace("'", "''")
        connection.execute(f"COPY (SELECT *,year(period) AS partition_year FROM seen) TO '{escaped_target}' (FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY(partition_year))")
        for dimension, query in {
            'dim_dataset': 'SELECT DISTINCT dataset,source_url,dataset_version FROM fact_observation',
            'dim_indicator': 'SELECT DISTINCT indicator,unit,frequency FROM fact_observation',
            'dim_geography': 'SELECT DISTINCT geography FROM fact_observation',
            'dim_date': 'SELECT DISTINCT period,year(period) AS year,month(period) AS month FROM fact_observation'
        }.items():
            connection.execute(f'CREATE OR REPLACE VIEW {dimension} AS {query}')
        quality = {'min_value': None, 'max_value': None, 'extreme_values': 0}
        if files and counts['processed_rows']:
            stats = pl.scan_parquet(files).select(pl.col('value').min().alias('min_value'), pl.col('value').max().alias('max_value'), (pl.col('value').abs() > 1e15).sum().alias('extreme_values')).collect(engine='streaming').to_dicts()[0]
            quality.update(stats)
        manifest = {**asdict(metadata), **counts, 'ingestion_status': 'completed', 'ingestion_id': ingestion_id, 'source_hash': source_hash, 'file_size': path.stat().st_size, 'ingestion_duration': time.perf_counter()-start, 'quality': quality, 'missing_data_percentage': round(100*counts['missing_values']/(counts['raw_rows']*len(COLUMNS)), 4) if counts['raw_rows'] else 0, 'columns': COLUMNS, 'quality_score': round(100 * counts['processed_rows']/counts['raw_rows'], 2) if counts['raw_rows'] else 0, 'silver_files': files, 'gold_file': str(target), 'completed_at': datetime.now(timezone.utc).isoformat(), 'idempotent': False}
        manifests = root / 'manifests'
        manifests.mkdir(exist_ok=True)
        manifest_path = manifests / f'{ingestion_id}.json'
        manifest['manifest_path'] = str(manifest_path.resolve())
        connection.execute('INSERT INTO ingestion_log VALUES (?,?,?,?,?,current_timestamp)', [ingestion_id, source_hash, metadata.source_url, metadata.dataset_version, str(manifest_path.resolve())])
        connection.execute('COMMIT')
        transaction_active = False
        connection.execute('CHECKPOINT')
        manifest['database_size'] = (root / 'warehouse.duckdb').stat().st_size
        manifest_path.write_text(json.dumps(manifest, indent=2))
        return manifest
    except Exception:
        if transaction_active:
            connection.execute('ROLLBACK')
        (silver / 'FAILED.json').write_text(json.dumps({'status':'failed', 'ingestion_id':ingestion_id, **counts}))
        raise
    finally:
        connection.close()
