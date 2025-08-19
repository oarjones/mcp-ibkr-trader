#!/bin/bash
# run_live.sh

# This script runs the system in live trading mode.

export APP_ENV=live

uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
