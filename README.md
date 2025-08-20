# mcp-ibkr-trader

Autonomous trading system connecting a Master Control Program (MCP) server with Interactive Brokers Gateway.

## Quick Start

1.  **Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

2.  **Run the server:
    ```bash
    uvicorn mcp_server.main:app --reload
    ```

3.  **Run tests:
    ```bash
    pytest -q
    ```

4.  **Example usage:
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