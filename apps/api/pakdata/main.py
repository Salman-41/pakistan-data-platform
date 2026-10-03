"""Bounded, read-only analytical API. All query identifiers are application-owned."""
from __future__ import annotations
import json
import hashlib
import logging
import os
import time
from datetime import date, datetime
from collections import defaultdict, deque
from pathlib import Path
from typing import Literal
import duckdb
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from scipy.stats import pearsonr, spearmanr

logger = logging.getLogger('pakdata')
DATA_DIR = Path(os.getenv('PAKDATA_DATA_DIR', 'data'))
app = FastAPI(title='Pakistan Data Platform', version='0.1.0', description='Source-traceable public statistical observations; unavailable domains remain empty.')
app.add_middleware(CORSMiddleware, allow_origins=os.getenv('PAKDATA_CORS_ORIGINS', 'http://localhost:3000').split(','), allow_methods=['GET', 'POST'], allow_headers=['Content-Type'])
_requests: dict[str, deque] = defaultdict(deque)

@app.middleware('http')
async def throttle(request: Request, call_next):
    key = request.client.host if request.client else 'unknown'
    now = time.monotonic()
    queue = _requests[key]
    while queue and queue[0] < now - 60:
        queue.popleft()
    if len(queue) >= 120:
        return JSONResponse(status_code=429, content={'error': {'code': 'rate_limit', 'message': '120 requests per minute allowed'}}, headers={'Retry-After':'60'})
    queue.append(now)
    return await call_next(request)

@app.exception_handler(HTTPException)
async def structured_error(request, exc):
    return JSONResponse(status_code=exc.status_code, content={'error': {'code': str(exc.status_code), 'message': exc.detail}})

def query(sql: str, params=()):
    path = DATA_DIR / 'warehouse.duckdb'
    if not path.exists():
        return []
    cache = None
    cache_key = 'pakdata:' + hashlib.sha256((str(path.stat().st_mtime_ns)+sql+json.dumps(params)).encode()).hexdigest()
    if os.getenv('PAKDATA_REDIS_URL'):
        try:
            import redis
            cache = redis.Redis.from_url(os.environ['PAKDATA_REDIS_URL'], socket_connect_timeout=0.2, socket_timeout=0.2)
            cached = cache.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as exc:
            logger.warning('redis_unavailable', extra={'error_type': type(exc).__name__})
            cache = None
    with duckdb.connect(str(path), read_only=True) as con:
        con.execute("SET memory_limit='512MB'")
        con.execute('SET threads=2')
        cursor = con.execute(sql, params)
        names = [d[0] for d in cursor.description]
        rows = [{k: v.isoformat() if isinstance(v, (date, datetime)) else v for k,v in zip(names,row)} for row in cursor.fetchall()]
    if cache is not None:
        try:
            cache.setex(cache_key, 60, json.dumps(rows, default=str))
        except Exception:
            logger.warning('redis_write_unavailable')
    return rows

def artifact(name: str):
    path = DATA_DIR / name
    return json.loads(path.read_text()) if path.exists() else []

def available(rows):
    return {'status': 'available' if rows else 'unavailable', 'data': rows, 'note': None if rows else 'No ingested observations support this request.'}

@app.get('/health')
def health():
    return {'status':'ok', 'warehouse_available': (DATA_DIR / 'warehouse.duckdb').exists()}

@app.get('/api/v1/economy/indicators')
def indicators():
    return available(query('SELECT dataset,indicator,unit,frequency,geography,MIN(period) AS start,MAX(period) AS end,COUNT(*) AS observations FROM fact_observation GROUP BY ALL ORDER BY indicator,geography'))

@app.get('/api/v1/workspace')
def workspace():
    """Bounded analytical snapshot with indicator definitions and explicit coverage."""
    rows = query('SELECT dataset,indicator,geography,period,value,unit,frequency,source_url FROM fact_observation ORDER BY period,indicator,geography LIMIT 20001')
    if len(rows) > 20000:
        raise HTTPException(422, 'Workspace snapshot exceeds 20,000 rows; use the paginated domain endpoints.')
    metadata = artifact('indicator_metadata.json') or {}
    for row in rows:
        key = row['indicator']
        if key not in metadata:
            metadata[key] = {'title': key.replace('_', ' ').title(), 'domain': 'inflation' if key.startswith('cpi_') or key == 'wpi' else 'population', 'source': 'Pakistan Bureau of Statistics', 'unit': row['unit'], 'source_url': row['source_url'], 'definition': 'Published source observations. Census annual dates represent census-year labels; census boundaries may differ between years.' if 'census' in row['dataset'] else 'Published price index, base 2015–16 = 100; index levels are distinct from percentage inflation rates.'}
    dates = [r['period'] for r in rows]
    return {**available(rows), 'metadata': metadata, 'coverage': {
        'observations': len(rows), 'indicators': len({r['indicator'] for r in rows}),
        'datasets': len({r['dataset'] for r in rows}), 'geographies': len({r['geography'] for r in rows}),
        'start': min(dates) if dates else None, 'end': max(dates) if dates else None,
        'national_observations': sum(r['geography'] == 'Pakistan' for r in rows),
    }}

@app.get('/api/v1/economy/timeseries')
def timeseries(indicator: str = Query(..., max_length=160), geography: str = Query('Pakistan', max_length=160), dataset: str | None = Query(None, max_length=160), start: str | None = Query(None, pattern=r'^\d{4}(-\d{2})?(-\d{2})?$'), end: str | None = Query(None, pattern=r'^\d{4}(-\d{2})?(-\d{2})?$'), frequency: str | None = Query(None, max_length=32), transform: Literal['raw','pct_change','rolling_mean','index'] = 'raw', window: int = Query(3, ge=2, le=120), limit: int = Query(500, ge=1, le=5000), offset: int = Query(0, ge=0)):
    clauses=['indicator=?','geography=?']
    args=[indicator,geography]
    for column, value in [('dataset',dataset),('frequency',frequency)]:
        if value is not None:
            clauses.append(f'{column}=?'); args.append(value)
    if start:
        clauses.append('CAST(period AS VARCHAR)>=?'); args.append(start)
    if end:
        clauses.append('CAST(period AS VARCHAR)<=?'); args.append(end+'-31' if len(end)==7 else end+'-12-31' if len(end)==4 else end)
    # Transform before pagination so page boundaries do not reset rolling/pct values.
    rows=query('SELECT dataset,indicator,geography,period,value,unit,frequency,source_url FROM fact_observation WHERE '+' AND '.join(clauses)+' ORDER BY dataset,frequency,period LIMIT 20001', args)
    if len(rows)>20000:
        raise HTTPException(422,'Narrow the date range; transformations accept at most 20,000 observations.')
    if transform != 'raw' and rows:
        frame=pd.DataFrame(rows)
        def calculate(series):
            if transform=='pct_change': return series.pct_change(fill_method=None).replace([np.inf,-np.inf],np.nan)*100
            if transform=='rolling_mean': return series.rolling(window,min_periods=window).mean()
            first=series.dropna().iloc[0] if series.notna().any() else np.nan
            return series/first*100 if first != 0 else series*np.nan
        frame['value']=frame.groupby(['dataset','frequency'],sort=False)['value'].transform(calculate)
        rows=json.loads(frame.to_json(orient='records'))
    return {**available(rows[offset:offset+limit]),'total':len(rows),'limit':limit,'offset':offset,'transform':transform,'interpretation':'Percentage changes use adjacent source periods; no missing periods are interpolated.'}

@app.get('/api/v1/geography')
def geography():
    return available(query('SELECT geography,COUNT(*) AS observations FROM fact_observation GROUP BY geography ORDER BY geography'))

@app.get('/api/v1/catalog')
def catalog():
    # Present the latest ingestion for each publication; quality retains the audit history.
    publications = {}
    for path in sorted((DATA_DIR/'manifests').glob('*.json')):
        record = json.loads(path.read_text())
        key = record['source_url']
        if key not in publications or record.get('completed_at', '') > publications[key].get('completed_at', ''):
            filename = Path(record.get('original_file', '')).stem
            record['title'] = ('World Development Indicators · ' + filename.title()) if record['source'].startswith('World Bank') else ('Census 2023 · ' + filename.removeprefix('table_1_').replace('_', ' ').title()) if filename.startswith('table_1_') else 'Monthly consumer and wholesale price indices'
            publications[key] = record
    return available(sorted(publications.values(), key=lambda r: (r['source'], r.get('title', ''))))

@app.get('/api/v1/quality')
def quality():
    return available([json.loads(p.read_text()) for p in sorted((DATA_DIR/'manifests').glob('*.json'))])

@app.get('/api/v1/compare')
def compare(indicator_a: str, indicator_b: str, geography: str='Pakistan', start: str | None=None, end: str | None=None):
    a=timeseries(indicator_a,geography,None,start,end,None,'raw',3,5000,0)['data']
    b=timeseries(indicator_b,geography,None,start,end,None,'raw',3,5000,0)['data']
    if not a or not b: return available([])
    if len({(r['dataset'],r['frequency']) for r in a})!=1 or len({(r['dataset'],r['frequency']) for r in b})!=1:
        raise HTTPException(422,'Comparison requires one source/frequency per indicator.')
    if a[0]['frequency']!=b[0]['frequency']: raise HTTPException(422,'Compare indicators with identical frequency.')
    frame=pd.DataFrame(a)[['period','value']].merge(pd.DataFrame(b)[['period','value']],on='period',suffixes=('_a','_b')).dropna()
    correlations=None
    if len(frame)>=3 and frame.value_a.nunique()>1 and frame.value_b.nunique()>1:
        p=pearsonr(frame.value_a,frame.value_b); s=spearmanr(frame.value_a,frame.value_b)
        correlations={'pearson':float(p.statistic),'pearson_p':float(p.pvalue),'spearman':float(s.statistic),'spearman_p':float(s.pvalue),'n':len(frame)}
    return {**available(json.loads(frame.to_json(orient='records'))),'correlation':correlations,'caveat':'Associations are not causation. Serial dependence can invalidate ordinary correlation p-values; matched observed periods only.'}

DOMAINS={'trade':('trade','export','import'), 'population':('population','census'), 'agriculture':('agriculture','crop','yield'), 'labour':('labour','employment','unemployment'), 'energy':('energy','electricity','generation'), 'health':('worldbank_health',), 'education':('worldbank_education',), 'environment':('worldbank_environment',), 'digital':('worldbank_digital',)}
def domain_data(domain: str, limit: int, offset: int):
    terms=DOMAINS[domain]
    clauses=' OR '.join(['(lower(dataset) LIKE ? OR lower(indicator) LIKE ?)']*len(terms))
    args=[x for term in terms for x in ('%'+term+'%','%'+term+'%')]
    return available(query('SELECT * FROM fact_observation WHERE '+clauses+' ORDER BY period DESC LIMIT ? OFFSET ?', args+[limit,offset]))
def domain_endpoint(domain):
    def endpoint(limit: int=Query(100,ge=1,le=5000),offset: int=Query(0,ge=0)):
        return domain_data(domain,limit,offset)
    return endpoint
for domain in DOMAINS:
    app.add_api_route('/api/v1/'+domain,domain_endpoint(domain),methods=['GET'],name=domain)

@app.get('/api/v1/forecast')
def forecast():
    return available([json.loads(p.read_text()) for p in sorted((DATA_DIR/'models').glob('*-forecast.json'))])

@app.get('/api/v1/anomalies')
def anomalies():
    return available([json.loads(p.read_text()) for p in sorted((DATA_DIR/'models').glob('*-anomalies.json'))])

class AnalyticalRequest(BaseModel):
    operation: Literal['timeseries','compare','domain']
    indicator: str | None=Field(None,max_length=160)
    indicator_b: str | None=Field(None,max_length=160)
    geography: str=Field('Pakistan',max_length=160)
    domain: Literal['trade','population','agriculture','labour','energy'] | None=None

@app.post('/api/v1/controlled-query')
def controlled_query(body: AnalyticalRequest):
    if body.operation=='domain' and body.domain: return domain_data(body.domain,100,0)
    if body.operation=='timeseries' and body.indicator: return timeseries(body.indicator,body.geography,None,None,None,None,'raw',3,500,0)
    if body.operation=='compare' and body.indicator and body.indicator_b: return compare(body.indicator,body.indicator_b,body.geography)
    raise HTTPException(422,'Required fields are missing for the selected allowlisted operation.')
