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
