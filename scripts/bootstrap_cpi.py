"""Strict reviewed four-column new-base PBS monthly indices PDF adapter."""
from pathlib import Path
from datetime import datetime, timezone
import re, subprocess, urllib.request, json
import pandas as pd
from pipelines.ingest import ingest_csv
URL='https://www.pbs.gov.pk/wp-content/uploads/2020/07/indices_and_growth_rates_historical-1.pdf'

def parse(text):
    rows=[]
    pattern=r'^\s*(20\d{2})\s+(\d{1,2})\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s|$)'
    for line in text.split('Historical Inflation Rate')[0].splitlines():
        match=re.match(pattern,line)
        if not match: continue
        year,month=map(int,match.group(1,2))
        if not 1<=month<=12: raise ValueError('Invalid month')
        for indicator,value in zip(['cpi_national','cpi_urban','cpi_rural','wpi'],match.group(3,4,5,6)):
            rows.append(dict(dataset='pbs_price_indices',indicator=indicator,geography='Pakistan',period=f'{year}-{month:02d}-01',value=float(value),unit='index_2015_16_100',frequency='monthly',source_url=URL))
    frame=pd.DataFrame(rows)
    if frame.empty or frame.duplicated(['indicator','period']).any(): raise ValueError('Empty/duplicate PDF extraction')
    dates=pd.to_datetime(frame[frame.indicator=='cpi_national'].period)
    if len(dates)!=len(pd.date_range(dates.min(),dates.max(),freq='MS')): raise ValueError('Missing monthly PDF records')
    return frame

def main():
    raw=Path('data/raw'); raw.mkdir(parents=True,exist_ok=True); path=raw/'pbs_indices.pdf'
    if not path.exists(): urllib.request.urlretrieve(URL,path)
    subprocess.run(['pdftotext','-layout',str(path),str(raw/'pbs_indices.txt')],check=True)
    frame=parse((raw/'pbs_indices.txt').read_text()); target=raw/'cpi_canonical.csv'; frame.to_csv(target,index=False)
    metadata=dict(source='Pakistan Bureau of Statistics',source_url=URL,retrieval_date=datetime.now(timezone.utc).isoformat(),original_file=str(path),dataset_version='downloaded-2026-10',geographic_level='national',time_period=f'{frame.period.min()}/{frame.period.max()}',ingestion_status='retrieved',license='Publisher rights unspecified; no redistribution permission inferred')
    print(json.dumps(ingest_csv(target,metadata,'data'),indent=2))
if __name__=='__main__': main()
