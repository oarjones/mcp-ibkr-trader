import pytest
from unittest.mock import MagicMock, patch, ANY
import time
from ibkr_adapter.tws_client import TWSClient
from ibapi.contract import Contract

@pytest.fixture
def mock_tws_client():
    with patch('ibkr_adapter.tws_client.EClient', autospec=True) as MockEClient:
        client = TWSClient()
        # Mock the EClient instance that super() will refer to
        client.instance_mock = MockEClient.return_value
        
        # Simulate a successful connection
        client.is_connected = True
        client.next_valid_id = 1000
        yield client

def test_teardown_on_disconnect(mock_tws_client):
    client = mock_tws_client
    contract1 = Contract()
    contract1.symbol = "SPY"
    contract2 = Contract()
    contract2.symbol = "QQQ"

    # Subscribe to data, which calls the mocked EClient methods via super()
    client.reqMktData(1001, contract1, "", False, False, [])
    client.reqRealTimeBars(2001, contract2, 5, "TRADES", 0, [])

    # Verify subscriptions were recorded
    assert 1001 in client._active_mktdata_req_ids
    assert 2001 in client._active_rtb_req_ids

    # Disconnect and verify teardown calls
    client.disconnect()

    # Assert that the cancel methods on the EClient mock were called
    client.instance_mock.cancelMktData.assert_called_with(1001)
    client.instance_mock.cancelRealTimeBars.assert_called_with(2001)

    # Assert that internal tracking is now empty
    assert not client._active_mktdata_req_ids
    assert not client._active_rtb_req_ids

def test_resubscribe_on_reconnect(mock_tws_client):
    client = mock_tws_client
    contract1 = Contract()
    contract1.symbol = "SPY"
    contract2 = Contract()
    contract2.symbol = "QQQ"

    # Initial subscriptions
    client.reqMktData(1001, contract1, "", False, False, [])
    client.reqRealTimeBars(2001, contract2, 5, "TRADES", 0, [])

    # Simulate a disconnection by the server
    client.is_connected = False
    client.connectionClosed()

    # Reset mocks to ensure we are testing the resubscription calls specifically
    client.instance_mock.reqMktData.reset_mock()
    client.instance_mock.reqRealTimeBars.reset_mock()

    # Simulate a reconnect, which should trigger resubscription
    with patch.object(client, 'run'): # Mock run to avoid starting a real thread
        client.connect("host", 4002, 101)
        client.is_connected = True # Manually set connected status after connect call
        client._resubscribe_active()

    # Assert that the resubscription calls were made
    client.instance_mock.reqMktData.assert_called_with(1001, contract1, "", False, False, [])
    client.instance_mock.reqRealTimeBars.assert_called_with(2001, contract2, 5, "TRADES", 0, [])
