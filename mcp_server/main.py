from fastapi import FastAPI

app = FastAPI(
    title="mcp-ibkr-trader",
    description="Autonomous trading system connecting a Master Control Program (MCP) server with Interactive Brokers Gateway.",
    version="0.1.0",
)

@app.get("/health", tags=["Monitoring"])
async def read_root():
    return {"status": "ok"}
