"""Reproducible Pakistan WDI ingestion. Raw API responses and metadata are retained.

Null source values are missing observations, never zeros or interpolated values.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import time
import requests
import pandas as pd
from pipelines.ingest import ingest_csv

CONFIG = Path(__file__).resolve().parents[1] / 'pipelines/adapters/worldbank_indicators.json'
API = 'https://api.worldbank.org/v2'
LICENSE = 'World Development Indicators: CC BY 4.0 with World Bank additional terms; retain indicator source attribution. https://datacatalog.worldbank.org/search/dataset/0037712/world-development-indicators'

def fetch(url):
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=(15, 90))
            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, list) or len(payload) != 2 or not isinstance(payload[0], dict) or not isinstance(payload[1], list):
                raise ValueError(f'Unexpected World Bank response: {str(payload)[:200]}')
            if int(payload[0].get('pages', 1)) != 1:
                raise ValueError('Response exceeds bounded single-page request; increase per_page or narrow period')
            return response.content, payload
        except (requests.RequestException, ValueError):
            if attempt == 2:
                raise
            time.sleep(1 + attempt)

def parse(payload, specs, url):
    by_code = {entry[0]: entry for entry in specs}
    rows = []
    keys = set()
    for record in payload[1]:
        code = record['indicator']['id']
        value = record.get('value')
        if value is None:
            continue
        if code not in by_code or record.get('countryiso3code') != 'PAK':
            raise ValueError('Unrequested indicator or country in API response')
        year = str(record['date'])
        if not year.isdigit() or len(year) != 4 or not math.isfinite(float(value)):
            raise ValueError('Invalid annual observation')
        if (code, year) in keys:
            raise ValueError('Duplicate indicator/year in API response')
        keys.add((code, year))
        _, indicator, _, unit = by_code[code]
        rows.append(dict(indicator=indicator, geography='Pakistan', period=f'{year}-01-01', value=float(value), unit=unit, frequency='annual', source_url=url))
    return rows

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-dir', default='data')
    parser.add_argument('--domains', nargs='*')
    parser.add_argument('--refresh', action='store_true')
    args = parser.parse_args()
    root = Path(args.data_dir)
    raw = root / 'raw/worldbank'
    raw.mkdir(parents=True, exist_ok=True)
    config = json.loads(CONFIG.read_text())
    summary, dictionary, failures = [], {}, []
    for domain, specs in config.items():
        if args.domains and domain not in args.domains:
            continue
        codes = ';'.join(s[0] for s in specs)
        end = datetime.now(timezone.utc).year
        url = f'{API}/country/PAK/indicator/{codes}?source=2&date=1960:{end}&format=json&per_page=20000&footnote=y'
        original = raw / f'{domain}.json'
        metadata_file = raw / 'wdi-metadata.json'
        try:
            if args.refresh or not original.exists():
                content, payload = fetch(url)
                original.write_bytes(content)
            else:
                payload = json.loads(original.read_text())
            meta_url = f'{API}/indicator?source=2&format=json&per_page=30000'
            if args.refresh or not metadata_file.exists():
                content, meta = fetch(meta_url)
                metadata_file.write_bytes(content)
            else:
                meta = json.loads(metadata_file.read_text())
            definitions = {r['id']: r for r in meta[1]}
            observations = parse(payload, specs, url)
            if not observations:
                raise ValueError('No non-null observations for this domain')
            for row in observations:
                row['dataset'] = f'worldbank_{domain}'
            frame = pd.DataFrame(observations)
            canonical = raw / f'{domain}.csv'
            frame.to_csv(canonical, index=False)
            for code, indicator, title, unit in specs:
                definition = definitions.get(code)
                if not definition:
                    raise ValueError(f'Missing metadata for {code}')
                dictionary[indicator] = dict(code=code, title=title, publisher_title=definition['name'], unit=unit, domain='economy' if indicator in ('industry_value_added_share', 'services_value_added_share') else domain, source='World Bank · World Development Indicators', source_organization=definition.get('sourceOrganization', ''), definition=definition.get('sourceNote', ''), source_url=f'https://data.worldbank.org/indicator/{code}?locations=PK', license=LICENSE)
            metadata = dict(source='World Bank · World Development Indicators', source_url=url, retrieval_date=datetime.fromtimestamp(original.stat().st_mtime, timezone.utc).isoformat(), original_file=str(original), dataset_version=f'WDI-{domain}-{payload[0].get("lastupdated", "snapshot")}', geographic_level='national', time_period=f'{frame.period.min()}/{frame.period.max()}', license=LICENSE)
            manifest = ingest_csv(canonical, metadata, root)
            summary.append(dict(domain=domain, rows=manifest['processed_rows'], indicators=frame.indicator.nunique(), missing_series=[s[1] for s in specs if s[1] not in set(frame.indicator)]))
            print(json.dumps(summary[-1]), flush=True)
        except Exception as exc:
            failures.append(dict(domain=domain, error=str(exc)))
            print(json.dumps(failures[-1]), flush=True)
    previous = root / 'indicator_metadata.json'
    existing = json.loads(previous.read_text()) if previous.exists() else {}
    previous.write_text(json.dumps({**existing, **dictionary}, indent=2))
    report = dict(retrieved_at=datetime.now(timezone.utc).isoformat(), domains=summary, failures=failures)
    (root / 'worldbank_ingestion_report.json').write_text(json.dumps(report, indent=2))
    if failures:
        raise SystemExit('Some domains failed; review data/worldbank_ingestion_report.json')

if __name__ == '__main__':
    main()
