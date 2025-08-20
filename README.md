# mcp-ibkr-trader

Autonomous trading system connecting a Master Control Program (MCP) with Interactive Brokers Gateway.

## Quick Start

1.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the server:**
    ```bash
    uvicorn mcp_server.main:app --reload
    ```

3.  **Run tests:**
    ```bash
      pytest -q
    ```

4.  **Example usage:**
    ```bash
    curl -s -X POST http://localhost:8000/tool/market_data.get_bars \
      -H 'Content-Type: application/json' \
      -d '{"symbol":"EUR.USD","asset_type":"FX","tf":"1m","start":"2025-08-01T07:00:00Z","end":"2025-08-01T07:30:00Z"}'
    ```

## Configuration

The system can be configured via `config.example.yaml`. Key settings include:

*   **`ibkr.market_data.hist_defaults.outside_rth`**: A boolean flag to control whether historical data requests include data outside Regular Trading Hours (RTH).
    *   If `true`, `useRTH` is set to `0` (data outside RTH is included).
    *   If `false`, `useRTH` is set to `1` (only RTH data is included).

## IBKR Adapter Details

The `ibkr_adapter` module includes several refinements for robust interaction with the Interactive Brokers TWS API:

*   **Real-time Subscription Management**:
    *   **Teardown on Disconnect**: Active real-time market data and real-time bars subscriptions are automatically cancelled when the `TWSClient` disconnects, preventing orphaned subscriptions and resource leaks.
    *   **Resubscription on Reconnect**: Upon successful reconnection to the TWS Gateway, the adapter attempts to re-establish any real-time market data or real-time bars subscriptions that were active prior to the disconnection. This ensures continuity of data streams.

*   **Historical Data Concurrency**:
    *   `get_historical_data` calls are limited to a maximum of 2 concurrent requests using a threading semaphore. This helps to prevent pacing violations with the IBKR API. If more than 2 requests are made simultaneously, subsequent requests will wait or raise a `TimeoutError` if the semaphore cannot be acquired within the specified timeout.

*   **`get_bars` DataFrame dtypes**:
    *   The `get_bars` method in `ibkr_adapter/adapter.py` ensures consistent data types for the returned Pandas DataFrame:
        *   `open`, `high`, `low`, `close`: `float64`
        *   `volume`: `Int64` (nullable integer)
        *   `ts` (timestamp): `datetime64[ns]` (timezone-naive)
    This guarantees data quality for subsequent analytical operations.
