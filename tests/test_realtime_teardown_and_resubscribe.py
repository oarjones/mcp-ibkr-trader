import pytest
from unittest.mock import MagicMock, patch, ANY
import threading
import time
from ibkr_adapter.tws_client import TWSClient
from ibapi.contract import Contract

@pytest.fixture
def mock_tws_client():
    with patch('ibkr_adapter.tws_client.EClient') as MockEClient:
        with patch('ibkr_adapter.tws_client.EWrapper') as MockEWrapper:
            MockEClient.return_value = MagicMock(spec=TWSClient)
            MockEWrapper.return_value = MagicMock(spec=TWSClient)

            # Mock the actual EClient methods that super() calls
            MockEClient.reqMktData = MagicMock(return_value=None)
            MockEClient.reqRealTimeBars = MagicMock(return_value=None)
            MockEClient.cancelMktData = MagicMock(return_value=None)
            MockEClient.cancelRealTimeBars = MagicMock(return_value=None)
            MockEClient.disconnect = MagicMock(return_value=None)
            MockEClient.setConnState = MagicMock(return_value=None)
            MockEClient.wrapper = MagicMock(return_value=None) # Mock EClient.wrapper

        client = TWSClient()
        client.wrapper = MagicMock() # Mock the wrapper attribute
        client.serverVersion_ = 0 # Mock serverVersion_ attribute
        # Ensure super() calls work on the mocked client
        client.reqMktData = MagicMock() # This will call our overridden method
        client.cancelMktData = MagicMock()
        client.reqRealTimeBars = MagicMock()
        client.cancelRealTimeBars = MagicMock()
        client.disconnect = MagicMock(side_effect=client.disconnect)
        client.connect = MagicMock(side_effect=lambda h, p, c: setattr(client, 'is_connected', True))
        client.run = MagicMock()
        client.next_valid_id = 1000 # Simulate a valid ID
        client.is_connected = True # Simulate connected state
        client.isConnected = MagicMock(return_value=True) # Mock isConnected to return True
        client.conn = MagicMock() # Mock the conn attribute
        client.conn.sendMsg = MagicMock() # Mock the sendMsg method of conn
        client.connState = 0 # Mock connState attribute
        client.wrapper = MagicMock() # Mock the wrapper attribute

        yield client, MockEClient, MockEWrapper

def test_teardown_on_disconnect(mock_tws_client):
    client, MockEClient, MockEWrapper = mock_tws_client

    # Simulate some active subscriptions
    contract1 = Contract()
    contract1.symbol = "SPY"
    contract2 = Contract()
    contract2.symbol = "QQQ"

    client.reqMktData(1001, contract1, "", False, False, [])
    client.reqRealTimeBars(2001, contract2, 5, "TRADES", 0, [])

    # Manually populate active subscriptions as client.reqMktData/reqRealTimeBars are mocked
    client._active_mktdata_req_ids.add(1001)
    client._active_subs["mktdata"][1001] = {"contract": contract1, "genericTickList": "", "snapshot": False, "regulatorySnapshot": False}
    client._active_rtb_req_ids.add(2001)
    client._active_subs["rtbars"][2001] = {"contract": contract2, "barSize": 5, "whatToShow": "TRADES", "useRTH": 0, "realTimeBarsOptions": []}

    # Reset MockEClient mocks after initial subscriptions
    MockEClient.reqMktData.reset_mock()
    MockEClient.reqRealTimeBars.reset_mock()
    MockEClient.cancelMktData.reset_mock()
    MockEClient.cancelRealTimeBars.reset_mock()

    assert 1001 in client._active_mktdata_req_ids
    assert 2001 in client._active_rtb_req_ids
    assert 1001 in client._active_subs["mktdata"]
    assert 2001 in client._active_subs["rtbars"]

    # Disconnect and verify teardown
    client.disconnect()

    # Assert that cancel methods were called on the mocked super()
    MockEClient.cancelMktData.assert_called_with(1001)
    MockEClient.cancelRealTimeBars.assert_called_with(2001)

    # Assert that internal tracking is cleared
    assert not client._active_mktdata_req_ids
    assert not client._active_rtb_req_ids
    assert not client._active_subs["mktdata"]
    assert not client._active_subs["rtbars"]

def test_resubscribe_on_reconnect(mock_tws_client):
    client, MockEClient, MockEWrapper = mock_tws_client

    # Simulate initial subscriptions
    contract1 = Contract()
    contract1.symbol = "SPY"
    contract2 = Contract()
    contract2.symbol = "QQQ"

    client.reqMktData(1001, contract1, "", False, False, [])
    client.reqRealTimeBars(2001, contract2, 5, "TRADES", 0, [])

    # Manually populate active subscriptions as client.reqMktData/reqRealTimeBars are mocked
    client._active_mktdata_req_ids.add(1001)
    client._active_subs["mktdata"][1001] = {"contract": contract1, "genericTickList": "", "snapshot": False, "regulatorySnapshot": False}
    client._active_rtb_req_ids.add(2001)
    client._active_subs["rtbars"][2001] = {"contract": contract2, "barSize": 5, "whatToShow": "TRADES", "useRTH": 0, "realTimeBarsOptions": []}

    # Simulate disconnection
    client.is_connected = False
    client.connectionClosed()

    # Clear mock call history for resubscription check
    MockEClient.reqMktData.reset_mock()
    MockEClient.reqRealTimeBars.reset_mock()

    # Simulate reconnection and resubscription
    client.connect_and_run("host", 4002, 101) # This will call _resubscribe_active internally

    # Give some time for the thread to run (if connect_and_run starts a thread)
    # In this mock setup, _resubscribe_active is called synchronously
    # If it were truly async, we'd need a small sleep or a more sophisticated mock
    time.sleep(0.1) # Small sleep to allow potential async operations to settle

    # Assert that reqMktData and reqRealTimeBars were called again with original parameters
    MockEClient.reqMktData.assert_any_call(1001, ANY, "", False, False, [])
    MockEClient.reqRealTimeBars.assert_any_call(2001, ANY, 5, "TRADES", 0, [])

    # Assert that internal tracking is still consistent (not duplicated)
    assert 1001 in client._active_mktdata_req_ids
    assert 2001 in client._active_rtb_req_ids
    assert len(client._active_mktdata_req_ids) == 1
    assert len(client._active_rtb_req_ids) == 1
    assert len(client._active_subs["mktdata"]) == 1
    assert len(client._active_subs["rtbars"]) == 1
