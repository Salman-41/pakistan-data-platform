from pathlib import Path
from urllib.parse import urlparse, urljoin
import hashlib
import socket
import ipaddress
import pandas as pd
import requests

class OfficialSource:
    hosts: tuple[str, ...] = ()

    def validate_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or parsed.port not in (None,443) or not any(parsed.hostname == h or parsed.hostname.endswith('.'+h) for h in self.hosts):
            raise ValueError('Only HTTPS URLs on this official source host are allowed')
        for address in socket.getaddrinfo(parsed.hostname,443,type=socket.SOCK_STREAM):
            if not ipaddress.ip_address(address[4][0]).is_global:
                raise ValueError('Non-public source destination rejected')

    def download(self, url, destination, max_bytes=100_000_000):
        """Bounded streaming download; explicit validated redirects, timeout, atomic rename."""
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        current = url
        for _ in range(5):
            self.validate_url(current)
            response = requests.get(current, stream=True, timeout=(15,60), allow_redirects=False)
            if response.is_redirect:
                current = urljoin(current,response.headers['Location'])
                response.close()
                continue
            response.raise_for_status()
            break
        else:
            raise ValueError('Too many source redirects')
        temporary = destination.with_suffix(destination.suffix+'.partial')
        size = 0
        sha = hashlib.sha256()
        try:
            with temporary.open('wb') as output:
                for block in response.iter_content(1024*1024):
                    size += len(block)
                    if size > max_bytes:
                        raise ValueError('Source exceeds configured download byte limit')
                    sha.update(block)
                    output.write(block)
            temporary.replace(destination)
        finally:
            response.close()
            temporary.unlink(missing_ok=True)
        return {'source_url':url,'resolved_url':current,'file_size':size,'sha256':sha.hexdigest()}

class PBS(OfficialSource):
    hosts = ('pbs.gov.pk',)

class SBP(OfficialSource):
    hosts = ('sbp.org.pk',)

class NEPRA(OfficialSource):
    hosts = ('nepra.org.pk',)

class Agriculture(OfficialSource):
    hosts = ('data.gov.pk','pbs.gov.pk','mnfsr.gov.pk','agripunjab.gov.pk','agriculture.kp.gov.pk')


def convert_table(path, output, *, format, column_map, sheet=0, table_index=0, max_rows=100_000, skiprows=0):
    """Explicit Excel/HTML table mapping into canonical fields; bounded small reports.

    CSV large sources should use ingest_csv directly. PDF has no universal table
    shape: extract_pdf_text provides auditable raw text, followed by a reviewed
    source-specific parser. It never claims text extraction is structured data.
    """
    if Path(path).stat().st_size > 50_000_000:
        raise ValueError('Report exceeds bounded conversion file size; use chunked CSV')
    if format == 'excel':
        table = pd.read_excel(path,sheet_name=sheet,skiprows=skiprows,nrows=max_rows+1)
    elif format == 'html':
        tables = pd.read_html(Path(path).read_text())
        table = tables[table_index]
    elif format == 'json':
        import json
        with Path(path).open() as handle:
            records = json.load(handle)
        if not isinstance(records, list):
            raise ValueError('JSON conversion requires an explicit top-level record list')
        table = pd.DataFrame.from_records(records)
    else:
        raise ValueError('Supported structured conversions are excel, html and json')
    if len(table)>max_rows:
        raise ValueError('Report exceeds configured row limit; use chunked CSV source')
    absent = set(column_map)-set(table.columns)
    if absent:
        raise ValueError(f'Explicit source columns missing: {absent}')
    table = table[list(column_map)].rename(columns=column_map)
    table.to_csv(output,index=False)
    return len(table)


def extract_pdf_text(path, output, max_pages=500):
    from pypdf import PdfReader
    reader = PdfReader(path)
    if len(reader.pages)>max_pages:
        raise ValueError('PDF exceeds extraction page limit')
    with Path(output).open('w') as handle:
        for number,page in enumerate(reader.pages):
            handle.write(f'\n--- PAGE {number+1} ---\n')
            handle.write(page.extract_text() or '')
    return {'pages':len(reader.pages),'status':'text_only_requires_reviewed_parser'}
