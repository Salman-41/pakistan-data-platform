# Measured benchmarks

See benchmark-results.json: genuine 738-row snapshot, DuckDB count and yearly aggregation, measured process RSS. The elapsed query measurement includes both queries after connection initialization, excludes network latency, and was one run without a statistical confidence interval.

No million-row benchmark, API load test, PostgreSQL benchmark, or Pandas-versus-Polars comparison has been completed. Those require authentic larger sources and controlled repeated measurements. Ingestion manifests retain actual per-run duration and accepted counts. Run scripts/benchmark.py to reproduce the snapshot query measurement on your hardware.
