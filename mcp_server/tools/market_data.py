from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum

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

@router.post("/tool/market_data.get_bars", response_model=MarketDataResponse)
async def get_bars(request: MarketDataRequest):
    # Mock implementation
    if request.start >= request.end:
        raise HTTPException(status_code=400, detail="start must be before end")

    bars = [
        Bar(t=request.start, o=1.0, h=1.1, l=0.9, c=1.05, v=100),
        Bar(t=request.end, o=1.05, h=1.15, l=1.0, c=1.1, v=120),
    ]
    return MarketDataResponse(
        symbol=request.symbol,
        tf=request.tf,
        bars=bars,
        meta={"what_to_show": request.what_to_show, "source": "MOCK", "count": len(bars)},
    )
