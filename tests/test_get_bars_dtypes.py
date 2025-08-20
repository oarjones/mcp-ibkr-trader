import pytest
import pandas as pd
import numpy as np
from ibkr_adapter.adapter import TWSAdapter
from datetime import datetime

@pytest.fixture(scope="module")
def adapter():
    # Initialize TWSAdapter in dry_run mode for testing dtypes
    # This assumes config.example.yaml is set up for dry_run=True
    # Or you can pass a mock config path
    return TWSAdapter(config_path="config.example.yaml")

def test_get_bars_dtypes(adapter):
    symbol = "EUR.USD"
    tf = "1m"
    start = "2025-01-01T09:00:00Z"
    end = "2025-01-01T09:05:00Z"
    what_to_show = "TRADES"

    df = adapter.get_bars(symbol, tf, start, end, what_to_show=what_to_show)

    assert isinstance(df, pd.DataFrame)
    assert not df.empty

    # Assert dtypes for numeric columns
    assert df["open"].dtype == np.float64
    assert df["high"].dtype == np.float64
    assert df["low"].dtype == np.float64
    assert df["close"].dtype == np.float64

    # Assert dtypes for volume (should be Int64 for nullable integer)
    assert str(df["volume"].dtype) == "Int64"

    # Assert dtypes for timestamp (should be datetime64[ns] and tz-naive)
    assert str(df["ts"].dtype).startswith("datetime64")
    assert df["ts"].dt.tz is None

    # Check for NaN values in critical columns (optional, but good practice)
    assert not df[["open", "high", "low", "close", "volume", "ts"]].isnull().any().any()
