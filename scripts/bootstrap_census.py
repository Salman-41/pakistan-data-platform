"""Reviewed PBS Table 1 nationwide adapter, preserving published geographic levels.

Table 1 names can wrap across lines. Normalize whitespace before selecting districts.
The national workbook carries national and provincial aggregates; never sum both.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse
import json
import re
import requests
import pandas as pd
from pipelines.ingest import ingest_csv

BASE='https://www.pbs.gov.pk/wp-content/uploads/2020/07/'
FIELDS={2:('population','persons'),3:('population_male','persons'),4:('population_female','persons'),5:('population_transgender','persons'),7:('population_density','persons_per_sq_km'),8:('urban_population_share','percent'),9:('household_size','persons_per_household'),11:('population_growth_annual','percent')}
PROVINCES={'PAKISTAN':'Pakistan','KHYBER PAKHTUNKHWA':'Khyber Pakhtunkhwa','PUNJAB':'Punjab','SINDH':'Sindh','BALOCHISTAN':'Balochistan','ISLAMABAD':'Islamabad','ISLAMABAD CAPITAL TERRITORY':'Islamabad'}
FILES=['table_1_national.xlsx','table_1_kp_districts.xlsx','table_1_punjab_districts.xlsx','table_1_sindh_districts.xlsx','table_1_balochistan_districts.xlsx','table_1_islamabad.xlsx']

def parse_table(path,url):
    frame=pd.read_excel(path,header=None)
    if frame.shape[1]!=12 or 'CENSUS-2023' not in str(frame.iloc[0,0]) or 'POPULATION' not in str(frame.iloc[1,2]):
        raise ValueError('Table 1 headers changed; review column mapping')
    national=path.name=='table_1_national.xlsx'
    region='national' if national else 'islamabad' if 'islamabad' in path.name else path.name.removeprefix('table_1_').removesuffix('_districts.xlsx')
    dataset='pbs_census_2023_kp' if region=='kp' else f'pbs_census_2023_{region}'+('' if national else '_districts')
    rows=[]
    for record in frame.itertuples(index=False,name=None):
        name=re.sub(r'\s+',' ',str(record[0])).strip().upper()
        if national:
            if name not in PROVINCES: continue
            geography=PROVINCES[name]
        else:
            if not name.endswith(' DISTRICT'): continue
            geography=name.removesuffix(' DISTRICT').title()
        total=pd.to_numeric(record[2],errors='coerce')
        components=sum(pd.to_numeric(record[i],errors='coerce') for i in (3,4,5))
        if pd.isna(total) or components!=total: raise ValueError(f'Sex components do not reconcile: {geography}')
        urban=pd.to_numeric(record[8],errors='coerce')
        if pd.notna(urban) and not 0<=urban<=100: raise ValueError('Invalid urban population percentage')
        for col,(indicator,unit) in FIELDS.items():
            value=pd.to_numeric(record[col],errors='coerce')
            if pd.notna(value): rows.append(dict(dataset=dataset,indicator=indicator,geography=geography,period='2023-01-01',value=float(value),unit=unit,frequency='annual',source_url=url))
        previous=pd.to_numeric(record[10],errors='coerce')
        if pd.notna(previous): rows.append(dict(dataset=dataset,indicator='population',geography=geography,period='2017-01-01',value=float(previous),unit='persons',frequency='annual',source_url=url))
    if not rows: raise ValueError('No reviewed geographic rows parsed')
    result=pd.DataFrame(rows)
    if result.duplicated(['indicator','geography','period']).any(): raise ValueError('Duplicate geography/indicator/year')
    return result

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--data-dir',default='data');args=parser.parse_args()
    root=Path(args.data_dir);raw=root/'raw/census';raw.mkdir(parents=True,exist_ok=True)
    frames=[]
    for filename in FILES:
        path=raw/filename;url=BASE+filename
        if not path.exists():
            response=requests.get(url,timeout=60);response.raise_for_status();path.write_bytes(response.content)
        frames.append((path,url,parse_table(path,url)))
    national=frames[0][2]
    sums={}
    for path,url,frame in frames[1:]:
        region='Khyber Pakhtunkhwa' if '_kp_' in path.name else 'Punjab' if '_punjab_' in path.name else 'Sindh' if '_sindh_' in path.name else 'Balochistan' if '_balochistan_' in path.name else 'Islamabad'
        count=frame[(frame.indicator=='population')&(frame.period=='2023-01-01')].value.sum()
        expected=national[(national.indicator=='population')&(national.geography==region)&(national.period=='2023-01-01')].value
        if len(expected)!=1 or count!=expected.iloc[0]: raise ValueError(f'District totals do not reconcile to {region}: {count}')
        sums[region]=int(count)
    pakistan=national[(national.indicator=='population')&(national.geography=='Pakistan')&(national.period=='2023-01-01')].value.iloc[0]
    if sum(sums.values())!=pakistan: raise ValueError('Province totals do not reconcile to published national census')
    summary=[]
    for path,url,frame in frames:
        canonical=path.with_suffix('.csv');frame.to_csv(canonical,index=False)
        metadata=dict(source='Pakistan Bureau of Statistics',source_url=url,retrieval_date=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc).isoformat(),original_file=str(path),dataset_version='2023-table1',geographic_level='national;province' if 'national' in path.name else 'district',time_period='2017;2023',license='Publisher rights unspecified; no redistribution permission inferred')
        manifest=ingest_csv(canonical,metadata,root)
        summary.append(dict(file=path.name,observations=manifest['processed_rows'],geographies=frame.geography.nunique(),inserted=manifest['inserted_rows']))
        print(json.dumps(summary[-1]),flush=True)
    (root/'census_ingestion_report.json').write_text(json.dumps(dict(sources=summary,reconciled_2023_population=int(pakistan),province_totals=sums,note='Published 2023 census geography; does not assert current boundaries or coverage of AJK/GB.'),indent=2))

if __name__=='__main__': main()
