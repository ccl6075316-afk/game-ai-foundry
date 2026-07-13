#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[release] Preparing embedded Python ..."
python3 scripts/prepare_embedded_python.py --output "$ROOT/gui/runtime/python" --with-rembg

echo "[release] Building GUI ..."
cd "$ROOT/gui"
export CSC_IDENTITY_AUTO_DISCOVERY=false
npm install
npm run build:app

echo "[release] Done. Artifacts in gui/release/"
