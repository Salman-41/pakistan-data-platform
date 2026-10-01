"""All fixtures below are artificial test data, never platform economic evidence."""

import numpy as np
import pandas as pd
from ml.engine import metrics, lag_frame, forecast, regimes, anomalies, yield_model
from ml.statistics import trends, mean_interval, difference_test


def fixture(n=72):
    return pd.Series(
        np.arange(n) * 0.1 + 10 + np.sin(np.arange(n) * np.pi / 6),
        index=pd.date_range("2000-01-01", periods=n, freq="MS"),
    )


def test_lags_do_not_contain_target():
    s = fixture()
    x, _ = lag_frame(s)
    assert x.iloc[0].lag_1 == s.iloc[11]
    assert np.isclose(x.iloc[0].rolling_mean, s.iloc[:12].mean())


def test_zero_safe_metric():
    assert metrics([0, 2], [1, 1])["mape_percent"] == 50
    assert metrics([0, 0], [1, 2])["mape_percent"] is None


def test_forecast_prerequisites_and_recursive_dates():
    assert forecast(fixture(20))["status"] == "blocked"
    missing = fixture()
    missing.iloc[5] = np.nan
    assert forecast(missing)["status"] == "blocked"
    report, _ = forecast(fixture(), horizon=2)
    assert report["status"] == "trained"
    assert len(report["metrics"]) == 4
    assert report["forecast"][0]["period"] == "2006-01-01"


def test_regimes_prerequisites():
    assert regimes(pd.DataFrame({"one": fixture()}))["status"] == "blocked"


def test_anomalies_fit_before_monitoring():
    report, _ = anomalies(fixture())
    assert report["observations"][0]["period"] > report["training_end"]


def test_yield_blocks_absent_data():
    assert yield_model(pd.DataFrame())["status"] == "blocked"


def test_statistical_missingness_and_assumptions():
    assert mean_interval([1, 2, 3])["status"] == "blocked"
    assert difference_test([1, 2, 3], [4, 5, 6])["status"] == "blocked"
    assert mean_interval([1, 2, 3], independent=True)["mean"] == 2
    result = trends(pd.Series([0.0, 2.0, 4.0]), window=2)
    assert pd.isna(result.percentage_change.iloc[1])
    assert result.rolling_average.iloc[2] == 3


def test_yield_whole_year_holdout_and_encoded_features():
    rows = [
        {
            "year": year,
            "crop": "wheat" if district % 2 else "maize",
            "district": str(district),
            "area": float(100 + district),
            "yield": float(2 + district / 100 + (year - 2000) / 10),
        }
        for year in range(2000, 2006)
        for district in range(20)
    ]
    report, _ = yield_model(pd.DataFrame(rows))
    assert report["holdout_year"] == 2005
    assert report["holdout_rows"] == 20
    assert set(report["permutation_importance_mae_increase"]) == {"year", "area", "crop", "district"}
