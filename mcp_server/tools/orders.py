from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional

router = APIRouter()

class AssetTypeEnum(str, Enum):
    stk = "STK"
    fx = "FX"
    fut = "FUT"
    crypto = "CRYPTO"
    opt = "OPT"

class SideEnum(str, Enum):
    buy = "BUY"
    sell = "SELL"

class OrderTypeEntryEnum(str, Enum):
    lmt = "LMT"
    mkt = "MKT"

class OrderTypeStopEnum(str, Enum):
    stp = "STP"

class OrderTypeTakeEnum(str, Enum):
    lmt = "LMT"

class TifEnum(str, Enum):
    day = "DAY"
    gtc = "GTC"

class EntryOrder(BaseModel):
    type: OrderTypeEntryEnum
    price: Optional[float] = None

class StopOrder(BaseModel):
    type: OrderTypeStopEnum
    stop_price: float

class TakeOrder(BaseModel):
    type: OrderTypeTakeEnum
    price: float

class PlaceBracketRequest(BaseModel):
    plan_id: str
    account: str
    symbol: str
    asset_type: AssetTypeEnum
    qty: int
    side: SideEnum
    entry: EntryOrder
    stop: StopOrder
    take: TakeOrder
    tif: TifEnum
    requires_approval: bool = False

class PlaceBracketResponse(BaseModel):
    plan_id: str
    parent_id: str
    children_ids: list[str]
    status: str
    dry_run: bool

@router.post("/tool/orders.place_bracket", response_model=PlaceBracketResponse)
async def place_bracket(request: PlaceBracketRequest):
    if request.qty <= 0:
        raise HTTPException(status_code=422, detail="qty must be positive")
    if request.side == SideEnum.buy:
        if request.entry.price and request.stop.stop_price >= request.entry.price:
            raise HTTPException(status_code=400, detail="stop_price must be below entry.price for BUY orders")
        if request.entry.price and request.take.price <= request.entry.price:
            raise HTTPException(status_code=400, detail="take.price must be above entry.price for BUY orders")
    if request.side == SideEnum.sell:
        if request.entry.price and request.stop.stop_price <= request.entry.price:
            raise HTTPException(status_code=400, detail="stop_price must be above entry.price for SELL orders")
        if request.entry.price and request.take.price >= request.entry.price:
            raise HTTPException(status_code=400, detail="take.price must be below entry.price for SELL orders")
    if request.requires_approval:
        raise HTTPException(status_code=409, detail="requires_approval is not supported in this module")

    # Mock implementation
    return PlaceBracketResponse(
        plan_id=request.plan_id,
        parent_id="SIM-ORD-123",
        children_ids=["SIM-TP-456", "SIM-SL-789"],
        status="ACCEPTED",
        dry_run=True,
    )
