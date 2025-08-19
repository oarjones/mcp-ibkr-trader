from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
from enum import Enum
import random

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
async def get_positions(account: str = "DU1234567"):
    # Mock implementation
    seed = f"{account}"
    rng = random.Random(seed)
    
    num_positions = rng.randint(0, 2)
    positions = []
    total_pnl = 0

    for _ in range(num_positions):
        asset_type = rng.choice(list(AssetTypeEnum))
        symbol = f"SYM{rng.randint(1, 100)}"
        qty = rng.randint(1, 100) * rng.choice([-1, 1])
        avg_price = rng.uniform(10, 200)
        unrealized_pnl = rng.uniform(-100, 100)
        total_pnl += unrealized_pnl
        positions.append(
            Position(
                symbol=symbol,
                asset_type=asset_type,
                qty=qty,
                avg_price=avg_price,
                unrealized_pnl=unrealized_pnl,
                currency="USD",
            )
        )

    return PortfolioResponse(
        positions=positions,
        equity=4000 + total_pnl,
        timestamp=datetime.now(),
        source="MOCK",
    )