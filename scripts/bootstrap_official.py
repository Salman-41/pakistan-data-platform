"""Reviewed PBS Census Table 1 adapter. Run from repository root; never synthesizes rows."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, json, urllib.request
import pandas as pd
from pipelines.ingest import ingest_csv

BASE='https://www.pbs.gov.pk/wp-content/uploads/2020/07/'
FIELDS={2:('population','persons'),3:('population_male','persons'),4:('population_female','persons'),5:('population_transgender','persons'),7:('population_density','persons_per_sq_km'),8:('urban_population_share','percent'),9:('household_size','persons_per_household'),11:('population_growth_annual','percent')}

def parse_table(path, url):
    frame=pd.read_excel(path,header=None)
    rows=[]
    for record in frame.itertuples(index=False,name=None):
        name=str(record[0]).strip()
        if not name.endswith(' DISTRICT'): continue
        geography=name.removesuffix(' DISTRICT').title()
        for col,(indicator,unit) in FIELDS.items():
            value=pd.to_numeric(record[col],errors='coerce')
            if pd.notna(value): rows.append(dict(dataset='pbs_census_2023_kp',indicator=indicator,geography=geography,period='2023-01-01',value=float(value),unit=unit,frequency='annual',source_url=url))
        value=pd.to_numeric(record[10],errors='coerce')
        if pd.notna(value): rows.append(dict(dataset='pbs_census_2023_kp',indicator='population',geography=geography,period='2017-01-01',value=float(value),unit='persons',frequency='annual',source_url=url))
        total=pd.to_numeric(record[2],errors='coerce')
        components=sum(pd.to_numeric(record[i],errors='coerce') for i in [3,4,5])
        if pd.notna(total) and components != total: raise ValueError(f'Sex totals mismatch: {geography}')
    if not rows: raise ValueError('No district records found; publisher format changed')
    return pd.DataFrame(rows)

def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--data-dir',default='data'); args=parser.parse_args()
    root=Path(args.data_dir); raw=root/'raw'; raw.mkdir(parents=True,exist_ok=True)
    url=BASE+'table_1_kp_districts.xlsx'; path=raw/'table_1_kp_districts.xlsx'
    if not path.exists(): urllib.request.urlretrieve(url,path)
    frame=parse_table(path,url); target=raw/'kp_census_canonical.csv'; frame.to_csv(target,index=False)
    metadata=dict(source='Pakistan Bureau of Statistics',source_url=url,retrieval_date=datetime.now(timezone.utc).isoformat(),original_file=str(path),dataset_version='2023-table1',geographic_level='district',time_period='2017;2023',ingestion_status='retrieved',license='Publisher rights unspecified; no redistribution permission inferred')
    (raw/'kp_census_metadata.json').write_text(json.dumps(metadata,indent=2))
    manifest=ingest_csv(target,metadata,root,50000); print(json.dumps(manifest,indent=2))

if __name__=='__main__': main()
