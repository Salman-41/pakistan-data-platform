"""Small analytical matrices only: never train on an unbounded warehouse extract."""

from __future__ import annotations
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, HistGradientBoostingRegressor, IsolationForest
from sklearn.inspection import permutation_importance
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.model_selection import TimeSeriesSplit, GridSearchCV
from sklearn.metrics import mean_absolute_error, mean_squared_error, silhouette_score


def blocked(reason):
    return {"status": "blocked", "reason": reason}


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    nz = np.abs(actual) > 1e-10
    return {
        "mae": float(mean_absolute_error(actual, predicted)),
        "rmse": float(np.sqrt(mean_squared_error(actual, predicted))),
        "mape_percent": float(np.mean(np.abs((actual[nz] - predicted[nz]) / actual[nz])) * 100) if nz.any() else None,
        "mape_eligible_rows": int(nz.sum()),
    }


def lag_frame(series, lag=12):
    s = series.astype(float)
    x = pd.DataFrame({f"lag_{i}": s.shift(i) for i in range(1, lag + 1)})
    # All windows end before the target timestamp.
    x["rolling_mean"] = s.shift(1).rolling(lag).mean()
    x["month_sin"] = np.sin(2 * np.pi * s.index.month / 12)
    x["month_cos"] = np.cos(2 * np.pi * s.index.month / 12)
    valid = x.notna().all(axis=1) & s.notna()
    return x[valid], s[valid]


def recursive(model, history, horizon, lag):
    h = history.copy()
    predictions = []
    for _ in range(horizon):
        next_date = h.index[-1] + pd.offsets.MonthBegin(1)
        padded = pd.concat([h, pd.Series([0.0], index=[next_date])])
        x, _ = lag_frame(padded, lag)
        val = float(model.predict(x.tail(1))[0])
        predictions.append(val)
        h.loc[next_date] = val
    return predictions


def forecast(series, seasonal_period=12, holdout=12, horizon=6):
    """Monthly contiguous series. Recursive holdout never consumes held-out targets."""
    s = series.sort_index().astype(float)
    if len(s) > 2400:
        return blocked("Forecast exceeds 2,400-period bounded analysis limit.")
    if not isinstance(s.index, pd.DatetimeIndex) or s.index.has_duplicates:
        return blocked("Require unique DatetimeIndex periods.")
    if s.isna().any() or not np.isfinite(s).all():
        return blocked("Missing/nonfinite values require a documented imputation decision.")
    if not s.index.equals(pd.date_range(s.index.min(), periods=len(s), freq="MS")):
        return blocked("Require contiguous monthly observations at month-start.")
    if len(s) < seasonal_period * 4 + holdout:
        return blocked("Require at least four seasonal cycles plus holdout observations.")
    train, test = s.iloc[:-holdout], s.iloc[-holdout:]
    x, y = lag_frame(train, seasonal_period)
    candidates = {
        "ridge": (Ridge(), {"model__alpha": [1.0, 10.0, 100.0]}),
        "random_forest": (
            RandomForestRegressor(n_estimators=100, random_state=42, n_jobs=1),
            {"model__max_depth": [3, 6]},
        ),
        "hist_gradient_boosting": (
            HistGradientBoostingRegressor(max_iter=100, random_state=42),
            {"model__max_leaf_nodes": [7, 15]},
        ),
    }
    results, fitted = {}, {}
    history = list(train.values)
    baseline = []
    for _ in range(holdout):
        baseline.append(history[-seasonal_period])
        history.append(baseline[-1])
    results["seasonal_naive"] = metrics(test, baseline)
    for name, (estimator, grid) in candidates.items():
        preprocessing = ColumnTransformer(
            [("numeric", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), list(x.columns))]
        )
        pipe = Pipeline([("features", preprocessing), ("model", estimator)])
        # CV describes one-step lag predictions; the untouched outer test measures recursive multi-step use.
        search = GridSearchCV(pipe, grid, cv=TimeSeriesSplit(n_splits=3), scoring="neg_mean_absolute_error", n_jobs=1)
        search.fit(x, y)
        predictions = recursive(search.best_estimator_, train, holdout, seasonal_period)
        results[name] = {
            **metrics(test, predictions),
            "cv_one_step_mae": float(-search.best_score_),
            "parameters": search.best_params_,
        }
        fitted[name] = search.best_estimator_
    selected = min(results, key=lambda n: results[n]["mae"])
    if selected == "seasonal_naive":
        hist = list(s.values)
        future = []
        for _ in range(horizon):
            future.append(hist[-seasonal_period])
            hist.append(future[-1])
        artifact = {"history": s, "seasonal_period": seasonal_period}
    else:
        x_all, y_all = lag_frame(s, seasonal_period)
        artifact = fitted[selected].fit(x_all, y_all)
        future = recursive(artifact, s, horizon, seasonal_period)
    output = {
        "status": "trained",
        "selected_model": selected,
        "training_rows": len(train),
        "holdout_rows": holdout,
        "holdout_start": str(test.index[0].date()),
        "metrics": results,
        "forecast": [
            {"period": str(d.date()), "value": float(v)}
            for d, v in zip(pd.date_range(s.index[-1] + pd.offsets.MonthBegin(1), periods=horizon, freq="MS"), future)
        ],
        "limitations": [
            "Statistical estimates; no guaranteed economic prediction.",
            "Model selection uses holdout; results are exploratory and require a later untouched evaluation.",
            "CV scores measure one-step predictions; outer holdout measures recursive forecasts.",
        ],
    }
    return output, artifact


def regimes(frame):
    if len(frame) > 2400 or frame.shape[1] > 32:
        return blocked("Regime matrix exceeds 2,400 periods or 32 indicators.")
    frame = frame.sort_index().dropna()
    if len(frame) < 36 or frame.shape[1] < 3:
        return blocked("Need at least 36 aligned national periods and three comparable indicators.")
    if not np.isfinite(frame.to_numpy(dtype=float)).all():
        return blocked("Nonfinite regime features.")
    diagnostics, models = {}, {}
    for k in (2, 3, 4):
        pipe = Pipeline(
            [
                ("scale", StandardScaler()),
                ("pca", PCA(n_components=min(3, frame.shape[1]))),
                ("cluster", KMeans(n_clusters=k, n_init=10, random_state=42)),
            ]
        )
        labels = pipe.fit_predict(frame)
        transformed = pipe[:-1].transform(frame)
        if len(set(labels)) < 2:
            continue
        diagnostics[k] = float(silhouette_score(transformed, labels))
        models[k] = pipe
    if not diagnostics:
        return blocked("Indicators do not support distinct clusters.")
    k = max(diagnostics, key=diagnostics.get)
    model = models[k]
    labels = model.predict(frame)
    summaries = frame.assign(cluster=labels).groupby("cluster").mean().round(6).to_dict("index")
    return {
        "status": "trained",
        "rows": len(frame),
        "clusters": k,
        "silhouette_scores": diagnostics,
        "cluster_means_original_units": summaries,
        "periods": [{"period": str(p.date()), "cluster": int(c)} for p, c in zip(frame.index, labels)],
        "limitations": [
            "Descriptive full-period clustering, not a causal or future regime classifier.",
            "Neutral numeric cluster labels; compare means before interpretation.",
        ],
    }, model


def anomalies(series, train_fraction=0.7):
    s = series.sort_index().astype(float)
    changes = s.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    frame = pd.DataFrame({"value": s, "change": changes}).dropna()
    split = int(len(frame) * train_fraction)
    if split < 24 or len(frame) - split < 6:
        return blocked("Require 24 training and six later monitoring observations.")
    model = Pipeline(
        [
            ("scale", StandardScaler()),
            ("detector", IsolationForest(n_estimators=100, contamination=0.05, random_state=42, n_jobs=1)),
        ]
    )
    model.fit(frame.iloc[:split])
    later = frame.iloc[split:]
    labels = model.predict(later)
    scores = model.decision_function(later)
    return {
        "status": "trained",
        "training_end": str(frame.index[split - 1].date()),
        "observations": [
            {"period": str(p.date()), "value": float(v), "anomaly": bool(l == -1), "score": float(score)}
            for p, v, l, score in zip(later.index, later.value, labels, scores)
        ],
        "limitations": [
            "Unsupervised novelty flags, not validated economic crises.",
            "Contamination is a modelling assumption; no labelled anomaly accuracy is claimed.",
        ],
    }, model


def yield_model(frame):
    required = {"year", "crop", "district", "area", "yield"}
    if not required.issubset(frame.columns):
        return blocked("Need genuine year, crop, district, cultivated area and yield fields.")
    if len(frame) > 50000:
        return blocked("Yield extract exceeds 50,000 rows; use an explicit bounded selection.")
    frame = frame.dropna(subset=list(required)).sort_values("year")
    if (
        not np.isfinite(frame[["year", "area", "yield"]].to_numpy(dtype=float)).all()
        or (frame.area <= 0).any()
        or (frame["yield"] < 0).any()
    ):
        return blocked("Yield features require finite numbers, positive area and nonnegative yield.")
    if len(frame) < 100 or frame.year.nunique() < 5:
        return blocked("Require 100 genuine observations spanning five years.")
    cutoff = frame.year.unique()[-1]
    train = frame[frame.year < cutoff]
    test = frame[frame.year == cutoff]
    if len(train) < 50 or len(test) < 10:
        return blocked("Insufficient chronological train/test observations.")
    numeric = ["year", "area"]
    categorical = ["crop", "district"]
    preprocessing = ColumnTransformer(
        [
            ("numeric", Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())]), numeric),
            ("categorical", OneHotEncoder(handle_unknown="ignore", sparse_output=False), categorical),
        ]
    )
    model = Pipeline(
        [
            ("features", preprocessing),
            ("model", RandomForestRegressor(n_estimators=100, max_depth=8, n_jobs=1, random_state=42)),
        ]
    )
    model.fit(train[numeric + categorical], train["yield"])
    baseline = np.full(len(test), train["yield"].median())
    importance = permutation_importance(
        model,
        test[numeric + categorical],
        test["yield"],
        scoring="neg_mean_absolute_error",
        n_repeats=5,
        random_state=42,
        n_jobs=1,
    )
    return {
        "status": "trained",
        "training_rows": len(train),
        "holdout_year": int(cutoff),
        "holdout_rows": len(test),
        "permutation_importance_mae_increase": {
            name: float(value) for name, value in zip(numeric + categorical, importance.importances_mean)
        },
        "metrics": {
            "training_median": metrics(test["yield"], baseline),
            "random_forest": metrics(test["yield"], model.predict(test[numeric + categorical])),
        },
        "limitations": [
            "Area must be known at prediction time; no contemporaneous production feature is allowed.",
            "No weather, soil or causal effects inferred.",
        ],
    }, model
