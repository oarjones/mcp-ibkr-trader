import pytest
from ibkr_adapter.adapter import TWSAdapter
import pandas as pd

def test_get_bars_dry_run():
    adapter = TWSAdapter()
    df = adapter.get_bars("AAPL", "1m", "2025-01-01 09:00:00", "2025-01-01 09:10:00")
    assert isinstance(df, pd.DataFrame)
    assert not df.empty

def test_place_bracket_order_dry_run():
    adapter = TWSAdapter()
    order = adapter.place_bracket_order("AAPL", "STK", 10, "BUY", 180.0, 175.0, 190.0, "DAY")
    assert isinstance(order, dict)
    assert "parent_id" in order

def test_get_positions_dry_run():
    adapter = TWSAdapter()
    positions = adapter.get_positions()
    assert isinstance(positions, list)
    assert len(positions) > 0

def test_get_bars_parses_dates():
    """
    Tests if the 'ts' column in the DataFrame returned by get_bars is of datetime64 type.
    """
    adapter = TWSAdapter() # dry_run is True by default
    df = adapter.get_bars("AAPL", "1m", "2025-01-01 09:00:00", "2025-01-01 09:10:00")
    assert df['ts'].dtype == 'datetime64[ns]'

def test_get_bars_dry_run_deterministic():
    """
    Tests if get_bars in dry_run mode returns the same DataFrame for the same inputs.
    """
    adapter = TWSAdapter() # dry_run is True by default
    df1 = adapter.get_bars("MSFT", "5m", "2025-02-01 10:00:00", "2025-02-01 10:10:00")
    df2 = adapter.get_bars("MSFT", "5m", "2025-02-01 10:00:00", "2025-02-01 10:10:00")
    pd.testing.assert_frame_equal(df1, df2)


# To run live tests, set dry_run to false in config.example.yaml
# and ensure IB Gateway is running.
# @pytest.mark.live
# def test_get_bars_live():
#     adapter = TWSAdapter()
#     if adapter.dry_run:
#         pytest.skip("Skipping live test in dry run mode")
#     df = adapter.get_bars("EUR.USD", "1 min", "2025-08-19 09:00:00", "2025-08-19 09:10:00")
#     assert isinstance(df, pd.DataFrame)
#     assert not df.empty