#!/bin/bash
# run_paper.sh

# This script runs the system in paper trading mode.

export APP_ENV=paper

uvicorn mcp_server.main:app --host 0.0.0.0 --port 8000
