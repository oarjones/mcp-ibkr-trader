from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from enum import Enum
import random

router = APIRouter()

class TimeframeEnum(str, Enum):
    min1 = "1m"
    min5 = "5m"
    min15 = "15m"
    day1 = "1d"

class AssetTypeEnum(str, Enum):
    stk = "STK"
    fx = "FX"
    fut = "FUT"
    crypto = "CRYPTO"
    opt = "OPT"

class WhatToShowEnum(str, Enum):
    trades = "TRADES"
    midpoint = "MIDPOINT"
    bid_ask = "BID_ASK"

class MarketDataRequest(BaseModel):
    symbol: str
    asset_type: AssetTypeEnum
    tf: TimeframeEnum
    start: datetime
    end: datetime
    what_to_show: WhatToShowEnum = WhatToShowEnum.trades

class Bar(BaseModel):
    t: datetime
    o: float
    h: float
    l: float
    c: float
    v: int

class MarketDataResponse(BaseModel):
    symbol: str
    tf: TimeframeEnum
    bars: list[Bar]
    meta: dict

def get_timeframe_delta(tf: TimeframeEnum):
    if tf == TimeframeEnum.min1:
        return timedelta(minutes=1)
    elif tf == TimeframeEnum.min5:
        return timedelta(minutes=5)
    elif tf == TimeframeEnum.min15:
        return timedelta(minutes=15)
    elif tf == TimeframeEnum.day1:
        return timedelta(days=1)

@router.post("/tool/market_data.get_bars", response_model=MarketDataResponse)
async def get_bars(request: MarketDataRequest):
    # Mock implementation
    if request.start >= request.end:
        raise HTTPException(status_code=400, detail="start must be before end")

    bars = []
    current_time = request.start
    time_delta = get_timeframe_delta(request.tf)
    
    # Seed the random number generator for deterministic results
    seed = f"{request.symbol}-{request.tf}-{request.start}"
    rng = random.Random(seed)

    while current_time < request.end:
        open_price = rng.uniform(1.0, 100.0)
        close_price = open_price + rng.uniform(-0.5, 0.5)
        high_price = max(open_price, close_price) + rng.uniform(0.0, 0.2)
        low_price = min(open_price, close_price) - rng.uniform(0.0, 0.2)
        volume = rng.randint(100, 1000)
        
        bars.append(Bar(
            t=current_time,
            o=open_price,
            h=high_price,
            l=low_price,
            c=close_price,
            v=volume
        ))
        current_time += time_delta

    return MarketDataResponse(
        symbol=request.symbol,
        tf=request.tf,
        bars=bars,
        meta={"what_to_show": request.what_to_show, "source": "MOCK", "count": len(bars)},
    )