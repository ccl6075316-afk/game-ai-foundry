#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "[release] Preparing embedded Python ..."
python3 scripts/prepare_embedded_python.py --output "$ROOT/gui/runtime/python" --with-rembg

echo "[release] Preparing embedded Pi ..."
node scripts/prepare_embedded_pi.mjs --output "$ROOT/gui/runtime/pi"

echo "[release] Building GUI ..."
cd "$ROOT/gui"
export CSC_IDENTITY_AUTO_DISCOVERY=false
npm install
# Set PUBLISH=1 and GH_TOKEN / GITHUB_TOKEN to upload artifacts + latest.yml for auto-update.
if [[ "${PUBLISH:-}" == "1" ]]; then
  echo "[release] Publishing to GitHub Releases (electron-builder --publish always) ..."
  npm run build && npx electron-builder --publish always
else
  npm run build:app
  echo "[release] Tip: PUBLISH=1 GH_TOKEN=… ./scripts/build-release.sh 可上传并生成自动更新元数据"
fi

echo "[release] Done. Artifacts in gui/release/"
