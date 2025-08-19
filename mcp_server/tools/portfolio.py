from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from enum import Enum

router = APIRouter()

class AssetTypeEnum(str, Enum):
    stk = "STK"
    fx = "FX"
    fut = "FUT"
    crypto = "CRYPTO"
    opt = "OPT"

class Position(BaseModel):
    symbol: str
    asset_type: AssetTypeEnum
    qty: float
    avg_price: float
    unrealized_pnl: float
    currency: str

class PortfolioResponse(BaseModel):
    positions: list[Position]
    equity: float
    timestamp: datetime
    source: str

@router.post("/tool/portfolio.get_positions", response_model=PortfolioResponse)
async def get_positions():
    # Mock implementation
    positions = [
        Position(symbol="MES", asset_type=AssetTypeEnum.fut, qty=1, avg_price=5550.25, unrealized_pnl=125.5, currency="USD"),
        Position(symbol="EUR.USD", asset_type=AssetTypeEnum.fx, qty=-10000, avg_price=1.0910, unrealized_pnl=-15.2, currency="USD"),
    ]
    return PortfolioResponse(
        positions=positions,
        equity=4012.35,
        timestamp=datetime.now(),
        source="MOCK",
    )
