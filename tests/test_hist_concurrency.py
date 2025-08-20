import pytest
from unittest.mock import MagicMock, patch
import threading
import time
from ibkr_adapter.tws_client import TWSClient
from ibapi.contract import Contract
from loguru import logger
from queue import Queue

@pytest.fixture
def mock_tws_client_for_hist_concurrency():
    with patch('ibkr_adapter.tws_client.EClient') as MockEClient:
        with patch('ibkr_adapter.tws_client.EWrapper') as MockEWrapper:
            MockEClient.return_value = MagicMock(spec=TWSClient)
            MockEWrapper.return_value = MagicMock(spec=TWSClient)

        client = TWSClient()
        client.connect = MagicMock()
        client.run = MagicMock()
        client.next_valid_id = 1000
        client.is_connected = True

        # Mock reqHistoricalData to simulate work and allow signaling completion
        def mock_reqHistoricalData(reqId, *args, **kwargs):
            # Simulate putting some data into the queue
            client.get_response_queue(reqId).put(MagicMock(date="20250101  09:00:00", open=100, high=101, low=99, close=100.5, volume=1000))
            client.get_response_queue(reqId).put(MagicMock(date="20250101  09:01:00", open=100.5, high=101.5, low=99.5, close=101, volume=1100))
            # Simulate historicalDataEnd
            with client._events_lock:
                ev = client._end_events.get(reqId)
            if ev: ev.set()

        client.reqHistoricalData = MagicMock(side_effect=mock_reqHistoricalData)
        client.cancelHistoricalData = MagicMock()

        yield client

def test_historical_concurrency_limit(mock_tws_client_for_hist_concurrency):
    client = mock_tws_client_for_hist_concurrency
    client._hist_sem = threading.Semaphore(value=2) # Ensure semaphore is set to 2

    contract = Contract()
    contract.symbol = "TEST"

    # Events to control thread execution
    thread_started_event = threading.Event()
    release_semaphore_event = threading.Event()

    results_queue = Queue()
    errors_queue = Queue()

    def target_get_bars(client_instance, contract_instance, timeout, thread_num, results_q, errors_q):
        logger.info(f"Thread {thread_num}: Attempting to get historical data with timeout {timeout}")
        try:
            thread_started_event.set() # Signal that thread has started
            # get_historical_data calls reqHistoricalData internally
            client_instance.get_historical_data(
                contract=contract_instance,
                endDateTime="20250101 16:00:00 EST",
                durationStr="1 D",
                barSizeSetting="1 min",
                timeout=timeout
            )
            results_q.put(f"success_{thread_num}")
            logger.info(f"Thread {thread_num}: Successfully got historical data")
        except TimeoutError as e:
            errors_q.put(f"timeout_{thread_num}: {e}")
            logger.warning(f"Thread {thread_num}: TimeoutError: {e}")
        except Exception as e:
            errors_q.put(f"error_{thread_num}: {e}")
            logger.error(f"Thread {thread_num}: Unexpected error: {e}")

    threads = []

    # Launch 2 threads that will acquire the semaphore and wait
    for i in range(2):
        thread = threading.Thread(target=target_get_bars, args=(client, contract, 5.0, i, results_queue, errors_queue))
        threads.append(thread)
        thread.start()
        thread_started_event.wait(timeout=1.0) # Wait for thread to start
        thread_started_event.clear()

    # Give some time for the first two threads to acquire the semaphore
    time.sleep(0.1)

    # Launch the 3rd thread, which should time out trying to acquire the semaphore
    thread3 = threading.Thread(target=target_get_bars, args=(client, contract, 0.1, 2, results_queue, errors_queue)) # Short timeout
    threads.append(thread3)
    thread3.start()
    thread3.join(timeout=1.0) # Wait for thread 3 to finish or timeout

    # Collect results from queues
    results = []
    for _ in range(2): # Expect 2 successful results
        results.append(results_queue.get(timeout=5.0)) # Add a timeout to prevent infinite loop

    errors = []
    while not errors_queue.empty(): # Only one error expected
        errors.append(errors_queue.get())

    # Assert that thread 3 timed out trying to acquire the semaphore
    assert any("Historical semaphore acquire timeout" in err for err in errors)
    assert len(errors) == 1 # Only one error expected from thread 3
    assert len(results) == 2 # First two threads should have succeeded

    # Verify reqHistoricalData was called 2 times (by the two successful threads)
    assert client.reqHistoricalData.call_count == 2

    # Clean up threads (they might still be running if they didn't timeout)
    for thread in threads:
        thread.join()
    time.sleep(0.1) # Give some time for queue puts to complete