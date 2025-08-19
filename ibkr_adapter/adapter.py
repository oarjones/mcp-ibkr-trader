from ibkr_adapter.tws_client import TWSClient
from ibkr_adapter.mapping import resolve_contract
from mcp_server.tools.utils import load_config
import pandas as pd
from loguru import logger

TF_MAP = {
    "1m":  ("1 min",  "1800 S"),   # 30 min
    "5m":  ("5 mins", "3600 S"),   # 1 h
    "15m": ("15 mins","7200 S"),   # 2 h
    "1d":  ("1 day",  "1 M"),      # 1 mes (ajusta si quieres)
}

def ib_hist_params(tf, start_iso, end_iso):
    bar_size, default_duration = TF_MAP.get(tf, ("1 min", "1800 S")) # Default to 1m
    # Calculation of duration based on start/end is omitted for now for simplicity
    return bar_size, default_duration

class TWSAdapter:
    def __init__(self, config_path="config.example.yaml"):
        self.config = load_config()
        self.dry_run = bool(self.config.get("dry_run", True))

        if not self.dry_run:
            self.client = TWSClient()
            ib_config = self.config.get("ibkr", {})
            host = ib_config.get("host", "127.0.0.1")
            port = int(ib_config.get("port", 4002))
            client_id = int(ib_config.get("client_id", 101))
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

        # asset_type = self._infer_asset_type(symbol) # Optional, assuming STK for now
        contract = resolve_contract(symbol, "STK")

        bar_size, duration = ib_hist_params(tf, start, end)
        
        # Format end datetime for IBKR
        end_dt_str = end.replace("T", " ").replace("Z", "")

        bars = self.client.get_historical_data(
            contract=contract,
            endDateTime=end_dt_str,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow="TRADES",
            useRTH=1, 
            timeout=20
        )

        rows = []
        for b in bars:
            # b.date can be "YYYYMMDD  HH:MM:SS" or "YYYYMMDD"
            ts = pd.to_datetime(b.date, format="%Y%m%d  %H:%M:%S", errors="coerce")
            if pd.isna(ts):
                ts = pd.to_datetime(b.date, format="%Y%m%d", errors="coerce")
            rows.append({
                "ts": ts, 
                "open": b.open, 
                "high": b.high,
                "low": b.low, 
                "close": b.close, 
                "volume": getattr(b, "volume", 0)
            })

        df = pd.DataFrame(rows).dropna(subset=["ts"]).sort_values("ts").reset_index(drop=True)
        return df

    def place_bracket_order(self, symbol: str, asset_type: str, qty: int, side: str,
                            entry: float, stop: float, take: float, tif: str) -> dict:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for place_bracket_order")
            return {"parent_id": "dry_run_parent", "children_ids": ["dry_run_tp", "dry_run_sl"]}

        ib_config = self.config.get("ibkr", {})
        use_crypto_sec_type = ib_config.get("use_crypto_sec_type", True)

        contract = resolve_contract(
            symbol,
            asset_type,
            # contract_month should be passed as an argument if needed for FUT orders
            use_crypto_sec_type=use_crypto_sec_type
        )
        parent_order_id = self.client._next_order_id()
        
        orders = self.client.make_bracket_order(
            parentId=parent_order_id,
            action=side,
            quantity=qty,
            limitPrice=entry,
            takeProfitPrice=take,
            stopLossPrice=stop
        )

        for o in orders:
            self.client.placeOrder(o.orderId, contract, o)

        return {"parent_id": parent_order_id,
                "children_ids": [parent_order_id + 1, parent_order_id + 2]}

    def get_positions(self) -> list[dict]:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for get_positions")
            return [{"symbol": "DRY", "asset_type":"STK", "qty":100, "avg_price":100.0, "unrealized_pnl":10.0}]
        
        return self.client.get_positions_blocking()

    def __del__(self):
        if not self.dry_run:
            self.client.disconnect()
