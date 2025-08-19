import time
import uuid
from fastapi import FastAPI, Request, Response
from mcp_server.tools import market_data, orders, portfolio, pdt_guard, risk

app = FastAPI(
    title="mcp-ibkr-trader",
    description="Autonomous trading system connecting a Master Control Program (MCP) server with Interactive Brokers Gateway.",
    version="0.1.0",
)

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    correlation_id = request.headers.get('X-Correlation-ID') or str(uuid.uuid4())
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    response.headers["X-Process-Time-Ms"] = str(process_time * 1000)
    response.headers["X-Correlation-ID"] = correlation_id
    response.headers["X-Served-By"] = "mcp-ibkr-trader"
    return response

@app.get("/health", tags=["Monitoring"])
async def health():
    return {"status": "ok", "dry_run": True, "uptime_sec": time.time() - start_time}

@app.get("/version", tags=["Monitoring"])
async def version():
    return {"commit": "abc1234", "built_at": "2025-08-19T08:00:00Z", "version": "0.1.0"}

app.include_router(market_data.router, tags=["Tools"])
app.include_router(orders.router, tags=["Tools"])
app.include_router(portfolio.router, tags=["Tools"])
app.include_router(pdt_guard.router, tags=["Tools"])
app.include_router(risk.router, tags=["Tools"])

start_time = time.time()