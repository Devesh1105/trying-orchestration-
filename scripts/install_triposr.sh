#!/usr/bin/env bash
# Install TripoSR into ./vendor/TripoSR
set -euo pipefail

VENDOR_DIR="$(cd "$(dirname "$0")/.." && pwd)/vendor"
mkdir -p "$VENDOR_DIR"

if [ -d "$VENDOR_DIR/TripoSR" ]; then
  echo "TripoSR already installed at $VENDOR_DIR/TripoSR"
  exit 0
fi

echo "Cloning TripoSR…"
git clone https://github.com/VAST-AI-Research/TripoSR.git "$VENDOR_DIR/TripoSR"

echo "Installing TripoSR dependencies…"
pip install -r "$VENDOR_DIR/TripoSR/requirements.txt"

echo "TripoSR installed successfully."
