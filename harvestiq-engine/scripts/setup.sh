#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

pick_python() {
  for candidate in python3.12 python3.13 python3; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if ! PYTHON_BIN="$(pick_python)"; then
  echo "ERROR: No Python 3 found. Install Python 3.12+ (recommended: brew install python@3.12)"
  exit 1
fi

PY_VERSION="$("$PYTHON_BIN" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
echo "Using $PYTHON_BIN (Python $PY_VERSION)"

if [[ "$PY_VERSION" == "3.14" ]]; then
  echo ""
  echo "WARNING: Python 3.14 is very new. For best MongoDB Atlas compatibility use Python 3.12 or 3.13."
  echo "  brew install python@3.12"
  echo "  rm -rf .venv && /opt/homebrew/bin/python3.12 -m venv .venv && ./scripts/setup.sh"
  echo ""

  CERT_INSTALLER="/Applications/Python 3.14/Install Certificates.command"
  if [[ -f "$CERT_INSTALLER" ]]; then
    echo "Installing macOS SSL certificates for Python 3.14..."
    bash "$CERT_INSTALLER" || true
  fi
fi

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  "$PYTHON_BIN" -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/pip install --upgrade pip
.venv/bin/pip install -r requirements.txt

if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "Created .env from .env.example"
  echo "IMPORTANT: Edit .env and set MONGODB_URI to your MongoDB Atlas connection string."
fi

echo ""
echo "Setup complete."
echo "Next:"
echo "  1. Edit .env with MongoDB Atlas URI"
echo "  2. .venv/bin/python scripts/seed_crop_characteristics.py"
echo "  3. .venv/bin/python scripts/backfill_farm_locations.py  # if upgrading from Day 1"
echo "  4. ./scripts/start.sh"
