"""Analytical calculations with explicit missingness and inferential assumptions."""

import numpy as np
import pandas as pd
from scipy import stats


def trends(series, window=12):
    s = series.sort_index().astype(float)
    return pd.DataFrame(
        {
            "value": s,
            "percentage_change": s.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan) * 100,
            "rolling_average": s.rolling(window, min_periods=window).mean(),
            "moving_volatility": s.pct_change(fill_method=None)
            .replace([np.inf, -np.inf], np.nan)
            .rolling(window)
            .std(),
        }
    )


def compare(frame):
    """Pairwise complete data; levels and changes answer different questions."""
    numeric = frame.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)
    changes = numeric.pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
    return {
        "pearson_levels": numeric.corr(method="pearson", min_periods=12).to_dict(),
        "spearman_levels": numeric.corr(method="spearman", min_periods=12).to_dict(),
        "pearson_changes": changes.corr(min_periods=12).to_dict(),
        "pairwise_observations": numeric.notna().astype(int).T.dot(numeric.notna().astype(int)).to_dict(),
        "assumptions": [
            "Correlations are associations, not causation.",
            "Trending levels can produce spurious correlations; inspect changes and stationarity.",
            "Different units and periods must be aligned explicitly.",
        ],
    }


def mean_interval(values, confidence=0.95, independent=False):
    if not independent:
        return {
            "status": "blocked",
            "reason": "Student t interval requires an explicit independent-sample assumption; economic time series are autocorrelated.",
        }
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    if len(a) < 3:
        return {"status": "blocked", "reason": "Need at least three finite observations."}
    low, high = stats.t.interval(confidence, len(a) - 1, loc=a.mean(), scale=stats.sem(a))
    if np.all(a == a[0]):
        low = high = float(a[0])
    return {
        "status": "calculated",
        "mean": float(a.mean()),
        "lower": float(low),
        "upper": float(high),
        "n": len(a),
        "assumption": "Independent observations with approximately normal sample mean.",
    }


def difference_test(first, second, independent=False):
    if not independent:
        return {
            "status": "blocked",
            "reason": "Welch t-test is not appropriate for unadjusted autocorrelated time series.",
        }
    a = np.asarray(first, dtype=float)
    b = np.asarray(second, dtype=float)
    a = a[np.isfinite(a)]
    b = b[np.isfinite(b)]
    if min(len(a), len(b)) < 3:
        return {"status": "blocked", "reason": "Need at least three observations in each independent group."}
    result = stats.ttest_ind(a, b, equal_var=False)
    return {
        "status": "calculated",
        "statistic": float(result.statistic),
        "p_value": float(result.pvalue),
        "assumption": "Independent groups; unequal variances allowed; exploratory test without multiple comparison correction.",
    }
