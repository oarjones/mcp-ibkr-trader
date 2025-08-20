import pytest
import time
from datetime import datetime, timedelta
import pandas as pd
from ibkr_adapter.tws_client import TWSClient, _pace_hist
from ibkr_adapter.adapter import _ib_duration_from_range, ib_hist_params, TWSAdapter
from ibkr_adapter.mapping import resolve_contract
from ibapi.order import Order
from unittest.mock import MagicMock, patch

# Mock TWSClient for testing
class MockTWSClient(TWSClient):
    def __init__(self):
        super().__init__()
        self.reqHistoricalData_calls = []
        self.cancelHistoricalData_calls = []
        self.reqPositions_calls = []
        self.disconnect_called = False
        self.next_valid_id = 1000 # Mock next valid ID

    def reqHistoricalData(self, reqId, contract, endDateTime, durationStr, barSizeSetting, whatToShow, useRTH, formatDate, keepUpToDate, chartOptions):
        self.reqHistoricalData_calls.append({
            "reqId": reqId,
            "contract": contract,
            "endDateTime": endDateTime,
            "durationStr": durationStr,
            "barSizeSetting": barSizeSetting,
            "whatToShow": whatToShow,
            "useRTH": useRTH
        })
        # Simulate historicalData and historicalDataEnd callbacks
        # For testing pacing, we don't need to put actual bars
        self.historicalDataEnd(reqId, "", "")

    def cancelHistoricalData(self, reqId):
        self.cancelHistoricalData_calls.append(reqId)

    def reqPositions(self):
        self.reqPositions_calls.append(True)
        # Simulate position and positionEnd callbacks
        # For testing, we'll just simulate one position and then end
        mock_contract = MagicMock()
        mock_contract.symbol = "MOCK"
        mock_contract.secType = "STK"
        mock_contract.currency = "USD"
        self.position("U123456", mock_contract, 100, 50.0)
        self.positionEnd()

    def disconnect(self):
        self.disconnect_called = True

    def placeOrder(self, orderId, contract, order):
        pass # Mock placeOrder

@pytest.fixture
def mock_tws_client():
    return MockTWSClient()

@pytest.fixture
def tws_adapter(mock_tws_client):
    adapter = TWSAdapter()
    adapter.dry_run = False # Ensure we use the mock client
    adapter.client = mock_tws_client
    return adapter

def test_pacing_hist_calls_queue(mock_tws_client):
    # Reset _last_hist for a clean test
    global _last_hist
    _last_hist = 0.0

    contract = MagicMock()
    contract.symbol = "AAPL"
    end_time = datetime.now().strftime("%Y%m%d %H:%M:%S")

    # First call should not be delayed
    start_time_1 = time.time()
    mock_tws_client.get_historical_data(contract, end_time, "1 D", "1 day")
    end_time_1 = time.time()
    assert (end_time_1 - start_time_1) < 0.1 # Should be almost immediate

    # Second call should be delayed by at least 2 seconds
    start_time_2 = time.time()
    mock_tws_client.get_historical_data(contract, end_time, "1 D", "1 day")
    end_time_2 = time.time()
    assert (end_time_2 - start_time_2) >= 2.0

def test_duration_from_range():
    # Test seconds
    start = "2025-01-01T09:00:00Z"
    end = "2025-01-01T09:00:30Z"
    assert _ib_duration_from_range(start, end) == "30 S"

    # Test days
    start = "2025-01-01T09:00:00Z"
    end = "2025-01-03T09:00:00Z" # 2 days
    assert _ib_duration_from_range(start, end) == "2 D"

    # Test weeks
    start = "2025-01-01T09:00:00Z"
    end = "2025-01-15T09:00:00Z" # 2 weeks
    assert _ib_duration_from_range(start, end) == "2 W"

    # Test months
    start = "2025-01-01T09:00:00Z"
    end = "2025-03-01T09:00:00Z" # 2 months
    assert _ib_duration_from_range(start, end) == "1 M" # Expect 1 M due to 30-day approximation

    # Test edge case: less than a second
    start = "2025-01-01T09:00:00Z"
    end = "2025-01-01T09:00:00Z"
    assert _ib_duration_from_range(start, end) == "0 S"

def test_fx_contract_mapping():
    contract = resolve_contract("EUR.USD", "FX")
    assert contract.secType == "CASH"
    assert contract.exchange == "IDEALPRO"
    assert contract.symbol == "EUR"
    assert contract.currency == "USD"

    contract = resolve_contract("GBP.JPY", "FX")
    assert contract.secType == "CASH"
    assert contract.exchange == "IDEALPRO"
    assert contract.symbol == "GBP"
    assert contract.currency == "JPY"

def test_bracket_transmit_flags(mock_tws_client):
    adapter = TWSAdapter()
    adapter.dry_run = False
    adapter.client = mock_tws_client

    # Mock the _next_order_id to return a predictable sequence
    with patch.object(adapter.client, '_next_order_id', side_effect=[100, 101, 102]):
        adapter.place_bracket_order("AAPL", "STK", 10, "BUY", 150.0, 140.0, 160.0, "DAY")

        # Verify the transmit flags of the orders created by make_bracket_order
        # We need to access the orders created by make_bracket_order, which are then placed
        # Since placeOrder is mocked, we can't directly inspect them.
        # Instead, we'll mock make_bracket_order itself to return mock orders
        # and then assert on their transmit flags.

        # Re-mock place_bracket_order to return mock orders
        mock_orders = []
        for i in range(3):
            mock_order = MagicMock(spec=Order)
            mock_order.transmit = None # Initialize the attribute
            mock_order.orderId = 100 + i # Assign orderId
            mock_orders.append(mock_order)

        with patch.object(adapter.client, 'make_bracket_order', return_value=mock_orders) as mock_make_bracket_order:
            # Set transmit flags on mock orders after they are created
            mock_orders[0].transmit = False
            mock_orders[1].transmit = False
            mock_orders[2].transmit = True

            adapter.place_bracket_order("AAPL", "STK", 10, "BUY", 150.0, 140.0, 160.0, "DAY")

            # Assert on the transmit flags of the mock orders
            parent_order = mock_make_bracket_order.return_value[0]
            take_profit_order = mock_make_bracket_order.return_value[1]
            stop_loss_order = mock_make_bracket_order.return_value[2]

            assert parent_order.transmit == False
            assert take_profit_order.transmit == False
            assert stop_loss_order.transmit == True

def test_positions_blocking_shape(tws_adapter):
    positions = tws_adapter.get_positions()
    assert isinstance(positions, list)
    assert len(positions) > 0 # Assuming at least one mock position is returned

    for pos in positions:
        assert "symbol" in pos
        assert "asset_type" in pos
        assert "qty" in pos
        assert "avg_price" in pos
        assert "unrealized_pnl" in pos
        assert "currency" in pos

        assert isinstance(pos["symbol"], str)
        assert isinstance(pos["asset_type"], str)
        assert isinstance(pos["qty"], (int, float))
        assert isinstance(pos["avg_price"], (int, float))
        # unrealized_pnl can be None or float
        assert pos["unrealized_pnl"] is None or isinstance(pos["unrealized_pnl"], (int, float))
        assert isinstance(pos["currency"], str)

def test_error_map(mock_tws_client):
    from ibkr_adapter.tws_client import IBKRError, IBKR_ERROR_MAP

    # Test a mapped error code
    with patch('loguru.logger.error') as mock_logger_error:
        mock_tws_client.error(reqId=1, errorCode=10167, errorString="Market data not subscribed to.")
        mock_logger_error.assert_called_once()
        assert "Permissions error: Market data not subscribed." in mock_logger_error.call_args[0][0]

    # Test an unmapped error code
    with patch('loguru.logger.error') as mock_logger_error:
        mock_tws_client.error(reqId=2, errorCode=999, errorString="Some unknown error.")
        mock_logger_error.assert_called_once()
        assert "Unknown IBKR error." in mock_logger_error.call_args[0][0]