from ibkr_adapter.tws_client import TWSClient
from ibkr_adapter.mapping import resolve_contract
from mcp_server.tools.utils import load_config
import pandas as pd
from loguru import logger

class TWSAdapter:
    def __init__(self, config_path="config.example.yaml"):
        self.config = load_config()
        self.dry_run = self.config.get("dry_run", True)
        
        if not self.dry_run:
            self.client = TWSClient()
            ib_gateway_config = self.config.get("ib_gateway", {})
            host = ib_gateway_config.get("host", "127.0.0.1")
            port = ib_gateway_config.get("port", 4002)
            client_id = ib_gateway_config.get("client_id", 1)
            self.client.connect_and_run(host, port, client_id)

    def get_bars(self, symbol: str, tf: str, start: str, end: str) -> pd.DataFrame:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for get_bars")
            return pd.DataFrame({
                "ts": [pd.Timestamp("2025-01-01 09:00:00"), pd.Timestamp("2025-01-01 09:01:00")],
                "open": [100, 101],
                "high": [102, 102],
                "low": [99, 100],
                "close": [101, 101.5],
                "volume": [1000, 1200],
            })

        contract = resolve_contract(symbol, "STK") # Assuming STK for now
        reqId = self.client.next_valid_id
        self.client.next_valid_id += 1
        
        bars_data = self.client.get_historical_data(
            reqId=reqId,
            contract=contract,
            endDateTime=end,
            durationStr="1 D", # This should be calculated based on start and end
            barSizeSetting=tf,
            whatToShow="TRADES",
            useRTH=1,
        )
        
        df = pd.DataFrame(bars_data)
        df['ts'] = pd.to_datetime(df['date'], unit='s')
        df = df[['ts', 'open', 'high', 'low', 'close', 'volume']]
        return df

    def place_bracket_order(self, symbol: str, asset_type: str, qty: int, side: str,
                            entry: float, stop: float, take: float, tif: str) -> dict:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for place_bracket_order")
            return {"parent_id": "dry_run_parent", "children_ids": ["dry_run_tp", "dry_run_sl"]}

        contract = resolve_contract(symbol, asset_type)
        parent_order_id = self.client.next_valid_id
        self.client.next_valid_id += 3
        
        bracket_orders = self.client.make_bracket_order(
            parentOrderId=parent_order_id,
            action=side,
            quantity=qty,
            limitPrice=entry,
            takeProfitPrice=take,
            stopLossPrice=stop,
        )

        for order in bracket_orders:
            self.client.placeOrder(order.orderId, contract, order)

        return {"parent_id": parent_order_id, "children_ids": [parent_order_id + 1, parent_order_id + 2]}

    def get_positions(self) -> list[dict]:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for get_positions")
            return [{"symbol": "DRY", "qty": 100, "avg_price": 100, "unrealized_pnl": 10}]

        positions_data = self.client.get_positions()
        return positions_data

    def __del__(self):
        if not self.dry_run:
            self.client.disconnect()
