from ibkr_adapter.tws_client import TWSClient
from ibkr_adapter.mapping import resolve_contract
from mcp_server.tools.utils import load_config
from mcp_server.tools.market_data import store_realtime_market_data, RealtimeMarketData
import pandas as pd
from loguru import logger
from datetime import datetime
import random

TF_MAP = {
    "1m":  ("1 min",  "1800 S"),   # 30 min
    "5m":  ("5 mins", "3600 S"),   # 1 h
    "15m": ("15 mins","7200 S"),   # 2 h
    "1d":  ("1 day",  "1 M"),      # 1 mes (ajusta si quieres)
}

def _ib_duration_from_range(start_iso, end_iso):
    import pandas as pd
    delta = pd.to_datetime(end_iso) - pd.to_datetime(start_iso)
    secs = int(delta.total_seconds())
    if secs <= 3600*24:
        return f"{secs} S"
    elif secs <= 3600*24*7:
        return f"{secs//86400} D"
    elif secs <= 3600*24*28:
        return f"{secs//(86400*7)} W"
    else:
        return f"{max(1, secs//(86400*30))} M"

def ib_hist_params(tf, start_iso, end_iso):
    bar_size, _ = TF_MAP.get(tf, ("1 min", "1800 S")) # Default to 1m
    duration = _ib_duration_from_range(start_iso, end_iso)
    return bar_size, duration

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

    def on_order_data(self, symbol: str, price: float, timestamp: datetime, order_id: int | None = None):
        """
        This function is a placeholder for an IBKR API callback that provides order data.
        It should be registered with the IBKR client to receive real-time order updates.
        """
        logger.info(f"Received order data: Symbol={symbol}, Price={price}, Timestamp={timestamp}, OrderID={order_id}")
        market_data_entry = RealtimeMarketData(
            symbol=symbol,
            price=price,
            timestamp=timestamp,
            order_id=order_id
        )
        store_realtime_market_data(market_data_entry)

    def get_bars(self, symbol: str, tf: str, start: str, end: str, use_rth: int | None = None, what_to_show: str = "TRADES") -> pd.DataFrame:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for get_bars")
            seed = f"{symbol}-{tf}-{start}"
            random.seed(seed)
            return pd.DataFrame({
                "ts": [pd.Timestamp("2025-01-01 09:00:00"), pd.Timestamp("2025-01-01 09:01:00")],
                "open": [random.uniform(90, 110), random.uniform(90, 110)],
                "high": [random.uniform(100, 120), random.uniform(100, 120)],
                "low": [random.uniform(80, 100), random.uniform(80, 100)],
                "close": [random.uniform(90, 110), random.uniform(90, 110)],
                "volume": [random.randint(500, 1500), random.randint(500, 1500)],
            })

        # asset_type = self._infer_asset_type(symbol) # Optional, assuming STK for now
        contract = resolve_contract(symbol, "STK")

        bar_size, duration = ib_hist_params(tf, start, end)
        
        # Format end datetime for IBKR
        end_dt_str = end.replace("T", " ").replace("Z", "")

        # Determine useRTH from config or method parameter
        if use_rth is None:
            outside_rth = self.config.get("ibkr", {}).get("market_data", {}).get("hist_defaults", {}).get("outside_rth", False)
            use_rth_val = 0 if outside_rth else 1
        else:
            use_rth_val = use_rth

        bars = self.client.get_historical_data(
            contract=contract,
            endDateTime=end_dt_str,
            durationStr=duration,
            barSizeSetting=bar_size,
            whatToShow=what_to_show,
            useRTH=use_rth_val, 
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
        
        # Ensure correct dtypes
        numeric_cols = ["open", "high", "low", "close", "volume"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Ensure timestamp is tz-naive
        if 'ts' in df.columns:
            df['ts'] = pd.to_datetime(df['ts']).dt.tz_localize(None)

        return df

    def place_bracket_order(self, symbol: str, asset_type: str, qty: int, side: str,
                            entry: float, stop: float, take: float, tif: str) -> dict:
        if self.dry_run:
            logger.info("Dry run mode: returning mock data for place_bracket_order")
            seed = f"{symbol}-{qty}-{entry}-{stop}-{take}"
            random.seed(seed)
            parent_id = random.randint(1000, 9999)
            return {"parent_id": f"dry_run_parent_{parent_id}", "children_ids": [f"dry_run_tp_{parent_id+1}", f"dry_run_sl_{parent_id+2}"]}

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
