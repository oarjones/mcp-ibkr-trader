from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from enum import Enum

router = APIRouter()

class AssetTypeEnum(str, Enum):
    stk = "STK"
    fx = "FX"
    fut = "FUT"
    crypto = "CRYPTO"
    opt = "OPT"

class OrderTypeEntryEnum(str, Enum):
    lmt = "LMT"
    mkt = "MKT"

class OrderTypeStopEnum(str, Enum):
    stp = "STP"

class OrderTypeTakeEnum(str, Enum):
    lmt = "LMT"

class Plan(BaseModel):
    entry: dict
    stop: dict
    take: dict

class PreTradeCheckRequest(BaseModel):
    symbol: str
    asset_type: AssetTypeEnum
    qty: int
    plan: Plan

class PreTradeCheckResponse(BaseModel):
    ok: bool
    reasons: list[str]
    allowed_qty: int
    policy: dict
    dry_run: bool

@router.post("/tool/risk.pre_trade_check", response_model=PreTradeCheckResponse)
async def pre_trade_check(request: PreTradeCheckRequest):
    if request.qty <= 0:
        raise HTTPException(status_code=422, detail="qty must be positive")
    # Mock implementation
    return PreTradeCheckResponse(
        ok=True,
        reasons=[],
        allowed_qty=request.qty,
        policy={
            "risk_per_trade_pct": 0.01,
            "max_daily_loss_pct": 0.05,
        },
        dry_run=True,
    )
