"""Measured snapshot benchmark; no generated scale rows."""
import json,time,resource
from pathlib import Path
import duckdb
p=Path('data/warehouse.duckdb')
with duckdb.connect(str(p),read_only=True) as db:
    db.execute("SET memory_limit='512MB'")
    start=time.perf_counter()
    count=db.execute('SELECT count(*) FROM fact_observation').fetchone()[0]
    db.execute('SELECT indicator,year(period),avg(value) FROM fact_observation GROUP BY 1,2').fetchall()
    elapsed=time.perf_counter()-start
result={'rows':count,'database_bytes':p.stat().st_size,'aggregate_seconds':elapsed,'peak_process_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'scope':'local real PBS sample; not representative of million-row performance'}
Path('docs/benchmark-results.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
