"""Stream DuckDB observations into a migrated PostgreSQL warehouse.

Run python -m warehouse.load. Idempotent upserts permit source corrections;
no raw data is committed. Source manifests must accompany the warehouse.
"""
import json
import os
from pathlib import Path
import duckdb
from sqlalchemy import create_engine, text

def load():
    data=Path(os.getenv('PAKDATA_DATA_DIR','data'))
    engine=create_engine(os.environ['PAKDATA_DATABASE_URL'])
    manifests=[json.loads(p.read_text()) for p in (data/'manifests').glob('*.json')]
    with engine.begin() as connection:
        with duckdb.connect(str(data/'warehouse.duckdb'),read_only=True) as con:
            for dataset,url in con.execute('SELECT DISTINCT dataset,source_url FROM fact_observation').fetchall():
                matching=[m for m in manifests if m.get('source_url')==url]
                if not matching:
                    raise ValueError(f'No provenance manifest for {dataset}')
                connection.execute(text('INSERT INTO dim_dataset(dataset,source_url,license,metadata) VALUES(:dataset,:url,:license,CAST(:metadata AS jsonb)) ON CONFLICT(dataset) DO UPDATE SET metadata=EXCLUDED.metadata'),{'dataset':dataset,'url':url,'license':matching[-1].get('license'),'metadata':json.dumps(matching)})
            for name,column in [('dim_indicator','indicator'),('dim_geography','geography')]:
                values=con.execute(f'SELECT DISTINCT {column} FROM fact_observation').fetchall()
                connection.execute(text(f'INSERT INTO {name}({column}) VALUES(:value) ON CONFLICT DO NOTHING'),[{'value':v[0]} for v in values])
            # Manifest omissions are errors rather than provenance-free invented source rows.
            cursor=con.execute('SELECT dataset,indicator,geography,period,value,unit,frequency,source_url,dataset_version FROM fact_observation')
            cols=[c[0] for c in cursor.description]
            total=0
            while batch:=cursor.fetchmany(10000):
                records=[dict(zip(cols,row)) for row in batch]
                connection.execute(text('''INSERT INTO fact_observation(dataset,indicator,geography,period,value,unit,frequency,source_url,dataset_version) VALUES(:dataset,:indicator,:geography,:period,:value,:unit,:frequency,:source_url,:dataset_version) ON CONFLICT(dataset,indicator,geography,period,unit,frequency) DO UPDATE SET value=EXCLUDED.value,source_url=EXCLUDED.source_url,dataset_version=EXCLUDED.dataset_version'''),records)
                total+=len(records)
        connection.execute(text('REFRESH MATERIALIZED VIEW indicator_coverage'))
    return {'loaded_observations':total}

if __name__=='__main__':
    print(json.dumps(load()))
