import duckdb
import pytest
from fastapi.testclient import TestClient
from pakdata import main

@pytest.fixture()
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(main,'DATA_DIR',tmp_path)
    main._requests.clear()
    with duckdb.connect(str(tmp_path/'warehouse.duckdb')) as con:
        con.execute('CREATE TABLE fact_observation(dataset VARCHAR,indicator VARCHAR,geography VARCHAR,period VARCHAR,value DOUBLE,unit VARCHAR,frequency VARCHAR,source_url VARCHAR)')
        con.executemany('INSERT INTO fact_observation VALUES (?,?,?,?,?,?,?,?)', [('test','CPI','Pakistan',f'2024-0{i}',float(v),'index','monthly','https://www.pbs.gov.pk/') for i,v in enumerate([100,110,121],1)])
    return TestClient(main.app)

def test_series_and_pagination(client):
    result=client.get('/api/v1/economy/timeseries',params={'indicator':'CPI','transform':'pct_change','offset':1,'limit':1}).json()
    assert result['total']==3
    assert result['data'][0]['value']==pytest.approx(10)

def test_no_invented_district_values(client):
    result=client.get('/api/v1/economy/timeseries',params={'indicator':'CPI','geography':'Swat'}).json()
    assert result['status']=='unavailable'
    assert result['data']==[]

def test_sql_is_literal_parameter(client):
    result=client.get('/api/v1/economy/timeseries',params={'indicator':"CPI'; DROP TABLE fact_observation; --"})
    assert result.status_code==200
    assert result.json()['data']==[]
    assert len(client.get('/api/v1/economy/indicators').json()['data'])==1

def test_allowlisted_query(client):
    assert client.post('/api/v1/controlled-query',json={'operation':'sql','query':'select 1'}).status_code==422
    assert client.get('/api/v1/population').json()['status']=='unavailable'

def test_transform_zero_and_window(client):
    result=client.get('/api/v1/economy/timeseries',params={'indicator':'CPI','transform':'rolling_mean','window':2}).json()
    assert result['data'][0]['value'] is None
    assert result['data'][1]['value']==105
    assert client.get('/api/v1/economy/timeseries',params={'indicator':'CPI','limit':999999}).status_code==422
