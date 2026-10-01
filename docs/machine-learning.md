# Machine learning and statistical methodology

All models operate on bounded analytical extracts, not a warehouse-sized Pandas frame. No model metric is available until genuine records have been ingested and a run succeeds. Tests use artificial fixtures only. Model artifacts and reports belong under ignored `data/models/`.

## Forecasting

`ml.engine.forecast` accepts a unique, contiguous monthly series without missing or infinite values. A minimum four seasonal cycles plus twelve holdout months is required. Missing observations are rejected rather than silently treated as zero. CPI index forecasting and inflation-rate forecasting are separate targets; units must be preserved. Exchange-rate forecasts are experimental statistical estimates.

Features comprise twelve past values, an exclusively past rolling mean and month sine/cosine terms. Candidates are seasonal naive, Ridge, Random Forest and Histogram Gradient Boosting. Numeric imputation and scaling are inside sklearn Pipeline/ColumnTransformer; three-fold expanding TimeSeriesSplit tunes a small parameter grid. CV measures one-step prediction. The final twelve months are forecast recursively: the forecast for each subsequent month uses predicted values rather than actual held-out values. MAE and RMSE preserve source units. MAPE excludes zero targets and reports eligible observation counts; for near-zero rate targets prefer MAE/RMSE.

The lowest holdout MAE chooses the final model, then refits on the full available series. Consequently this holdout is also a selection set: its metric is exploratory and is not an unbiased post-selection estimate. A future external evaluation is necessary before operational deployment. No causal interpretations or guaranteed future economic claims are allowed. Seasonal naive can legitimately win.

Run `python -m ml.train --warehouse data/warehouse.duckdb --indicator CODE --geography Pakistan`. Reports include indicator, dataset, units, observation span and timestamp. The query is parameterized and capped at 2,400 observations; it rejects multiple datasets, units, frequencies or duplicate periods instead of averaging incompatible records. Joblib files are executable Python artifacts: load only trusted locally produced models.

## Agricultural yield

`yield_model` requires genuine district, crop, year, cultivated area and yield observations: at least 100 rows over five years. The latest whole year is held out; crop and district use OneHotEncoder with unseen-category support. RandomForest is compared with a training median baseline. Held-out permutation importance measures the increase in MAE after shuffling each input; it describes association and model reliance, not causal effects. Cultivated area must be known at prediction time. Contemporaneous production is excluded because yield is production divided by area. No district model is trained from national indicators. A missing source or insufficient coverage produces a blocked result.

## Economic periods and anomalies

`regimes` accepts only an explicitly aligned national-indicator matrix. With at least 36 periods and three indicators it scales features, applies PCA, fits KMeans for 2–4 clusters and chooses silhouette score. Output includes cluster means in source units and neutral numbered cluster labels. Full-period clustering is descriptive; its labels cannot be advertised as out-of-sample economic regime predictions.

`anomalies` forms level/change features, fits StandardScaler and IsolationForest on the first 70% of available periods, and evaluates later periods. Dates and anomaly scores remain attached to source observations. Five percent contamination is a modelling assumption, not a measured crisis prevalence. There are no labelled anomaly accuracy claims.

## Statistics

Rolling means and moving volatility require complete windows. Percentage changes across zero denominators or missing values remain unavailable. Pearson/Spearman correlations include pairwise sample sizes and comparisons of levels versus changes. Trending and autocorrelated data can give misleading relationships; correlations never establish causation. Student-t mean confidence intervals and Welch tests require an explicit independent-observation assumption and are blocked by default for macroeconomic time series. They are useful for appropriately sampled independent survey groups, not unadjusted consecutive national observations.

## Current limits

Forecast feature permutation importance, uncertainty bands, backtest visualization, advanced grouped agricultural tuning, model-registry integration and automated retraining are future work. Official sources are often short, revised, mixed frequency or incompletely licensed. Models must remain unavailable when prerequisites fail. Millions of ingestion records do not imply millions of independent forecast training samples.
