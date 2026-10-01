"""Small synthetic fixtures test engineering contracts; they are not public data."""
import duckdb
import pandas as pd
import pytest
from pipelines import ingest_csv
from pipelines.adapters import PBS

META = dict(source='PBS fixture',source_url='https://www.pbs.gov.pk/fixture',retrieval_date='2026-10-01',original_file='fixture.csv',dataset_version='fixture-v1',geographic_level='national',time_period='2020',ingestion_status='retrieved')

def write(path,values):
    pd.DataFrame([dict(dataset='test',indicator='cpi',geography='Pakistan',period=date,value=value,unit='index',frequency='monthly',source_url=META['source_url']) for date,value in values]).to_csv(path,index=False)

def test_chunk_quality_duplicates_and_revisions(tmp_path):
    source = tmp_path/'source.csv'
    write(source,[('2020-01-01','100'),('2020-01-01','100'),('2020-02-01','bad'),('2020-03-01','103')])
    result = ingest_csv(source,META,tmp_path/'data',chunk_size=1)
    assert result['raw_rows']==4
    assert result['processed_rows']==2
    assert result['duplicates']==1
    assert result['rejected_rows']==1
    assert ingest_csv(source,META,tmp_path/'data')['idempotent']
    write(source,[('2020-01-01','101')])
    result=ingest_csv(source,{**META,'dataset_version':'fixture-v2'},tmp_path/'data')
    assert result['revisions']==1
    con=duckdb.connect(str(tmp_path/'data/warehouse.duckdb'))
    assert con.execute('SELECT count(*) FROM fact_observation').fetchone()[0]==2
    assert con.execute('SELECT old_value,new_value FROM observation_revision').fetchone()==(100,101)
    con.close()

def test_schema_failure_rolls_back(tmp_path):
    source=tmp_path/'bad.csv'
    source.write_text('value\n1\n')
    with pytest.raises(ValueError,match='Missing canonical'):
        ingest_csv(source,META,tmp_path/'data')
    con=duckdb.connect(str(tmp_path/'data/warehouse.duckdb'))
    assert con.execute('SELECT count(*) FROM fact_observation').fetchone()[0]==0
    con.close()

def test_adapter_rejects_unofficial_url():
    with pytest.raises(ValueError):
        PBS().validate_url('https://example.com/pbs.csv')
    with pytest.raises(ValueError):
        PBS().validate_url('https://pbs.gov.pk.evil.example/source.csv')


def test_explicit_unit_geography_normalization():
    from pipelines.normalize import normalize_chunk
    frame = pd.DataFrame({'geography':[' KPK '], 'value':['2'], 'unit':['thousand persons']})
    result = normalize_chunk(frame, geography_aliases={'KPK':'Khyber Pakhtunkhwa'}, units={'thousand persons':('persons',1000)})
    assert result.iloc[0].geography == 'Khyber Pakhtunkhwa'
    assert result.iloc[0].value == 2000
    assert result.iloc[0].unit == 'persons'


def test_invalid_values_and_source_provenance(tmp_path):
    path=tmp_path/'invalid.csv'
    write(path,[('not-a-date','1'),('2020-01-01','inf'),('2020-02-01','4')])
    result=ingest_csv(path,META,tmp_path/'data',chunk_size=2)
    assert result['rejected_rows']==2
    assert result['processed_rows']==1
    assert result['database_size']>0
