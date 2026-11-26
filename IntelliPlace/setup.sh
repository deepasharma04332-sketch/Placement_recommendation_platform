#!/usr/bin/env bash
# Mac / Linux: run ./setup.sh once
set -e
cd "$(dirname "$0")/backend"
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
[ -f .env ] || cp .env.example .env
echo "SETUP COMPLETE! Now run ./run.sh"
