"""python -m ml.train --warehouse data/warehouse.duckdb --indicator CODE"""

import argparse
import json
from pathlib import Path
from datetime import datetime, timezone
import duckdb
import joblib
import pandas as pd
from ml.engine import forecast, anomalies


def load_series(path, indicator, geography, limit=2400, dataset=None):
    with duckdb.connect(str(path), read_only=True) as db:
        # Duplicate dataset versions must be resolved, never summed as economic values.
        rows = db.execute(
            "SELECT period, value, dataset, unit, frequency, source_url FROM fact_observation WHERE indicator = ? AND geography = ? AND (? IS NULL OR dataset = ?) ORDER BY period LIMIT ?",
            [indicator, geography, dataset, dataset, limit + 1],
        ).df()
    if len(rows) > limit:
        raise ValueError("Series exceeds bounded analysis limit; narrow coverage.")
    if rows.empty:
        raise ValueError("No matching real observations.")
    if rows.frequency.nunique() != 1 or str(rows.frequency.iloc[0]).lower() not in ("monthly", "m"):
        raise ValueError("Forecast adapter requires monthly frequency.")
    if rows.unit.nunique() != 1 or rows.dataset.nunique() != 1:
        raise ValueError("Choose one dataset/version and consistent unit before analysis.")
    dates = pd.to_datetime(rows.period).dt.to_period("M").dt.to_timestamp()
    if dates.duplicated().any():
        raise ValueError("Duplicate periods; resolve source/version explicitly.")
    return pd.Series(rows.value.to_numpy(dtype=float), index=pd.DatetimeIndex(dates)), rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--warehouse", required=True)
    parser.add_argument("--indicator", required=True)
    parser.add_argument("--geography", default="Pakistan")
    parser.add_argument("--dataset", help="Explicit source dataset/version when more than one exists")
    parser.add_argument("--task", choices=["forecast", "anomalies"], default="forecast")
    parser.add_argument("--output", default="data/models")
    args = parser.parse_args()
    if not args.indicator or any(
        c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in args.indicator
    ):
        parser.error("Indicator must be an identifier, not a path")
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    try:
        series, rows = load_series(args.warehouse, args.indicator, args.geography, dataset=args.dataset)
        result = (forecast if args.task == "forecast" else anomalies)(series)
        if isinstance(result, tuple):
            report, artifact = result
            joblib.dump(artifact, out / f"{args.indicator}-{args.task}.joblib")
        else:
            report = result
        report["provenance"] = {
            "warehouse": str(args.warehouse),
            "dataset": str(rows.dataset.iloc[0]),
            "indicator": args.indicator,
            "geography": args.geography,
            "unit": str(rows.unit.iloc[0]),
            "source_urls": sorted(rows.source_url.unique().tolist()),
            "period_start": str(series.index.min().date()),
            "period_end": str(series.index.max().date()),
            "observations": len(series),
        }
    except ValueError as error:
        report = {"status": "blocked", "reason": str(error)}
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    (out / f"{args.indicator}-{args.task}.json").write_text(json.dumps(report, indent=2, allow_nan=False))
    print(json.dumps(report, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
