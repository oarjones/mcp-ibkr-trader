from fastapi import APIRouter
from pydantic import BaseModel
from enum import Enum

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

class PdtGuardRequest(BaseModel):
    symbol: str
    asset_type: AssetTypeEnum
    side: SideEnum
    is_intraday: bool

class PdtGuardResponse(BaseModel):
    ok: bool
    remaining_intraday_trades: int
    note: str

@router.post("/tool/pdt_guard.validate", response_model=PdtGuardResponse)
async def pdt_guard_validate(request: PdtGuardRequest):
    # Mock implementation
    remaining_trades = 3
    if request.asset_type != AssetTypeEnum.stk or not request.is_intraday:
        remaining_trades = float("inf")

    return PdtGuardResponse(
        ok=True,
        remaining_intraday_trades=remaining_trades,
        note="PDT enabled: true | MOCK counter",
    )
