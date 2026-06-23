#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  echo "Virtual environment not found. Run ./scripts/setup.sh first."
  exit 1
fi

if [ ! -f ".env" ]; then
  echo ".env file not found. Run ./scripts/setup.sh or copy .env.example to .env"
  exit 1
fi

echo "Starting HarvestIQ backend on http://127.0.0.1:8000"
echo "API docs: http://127.0.0.1:8000/docs"
echo ""

exec .venv/bin/python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
