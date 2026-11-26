#!/usr/bin/env bash
# Mac / Linux: run ./run.sh to start the server
cd "$(dirname "$0")/backend"
source .venv/bin/activate
echo "Open http://localhost:8000 in your browser"
uvicorn app.main:app --port 8000
