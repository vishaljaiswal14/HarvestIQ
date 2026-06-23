#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if [ ! -d "node_modules" ]; then
  echo "Installing frontend dependencies..."
  npm install
fi

if [ ! -f ".env.local" ]; then
  cp .env.local.example .env.local
  echo "Created .env.local from .env.local.example"
fi

echo "Starting HarvestIQ frontend on http://localhost:3000"
exec npm run dev
