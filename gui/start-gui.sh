#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d node_modules ]]; then
  echo "[game-ai-foundry] First run: npm install ..."
  npm install
fi

export GAMEFACTORY_ROOT="${GAMEFACTORY_ROOT:-$(cd .. && pwd)}"
echo "[game-ai-foundry] GAMEFACTORY_ROOT=$GAMEFACTORY_ROOT"
echo "[game-ai-foundry] Starting GUI (Vite + Electron) ..."
echo "[game-ai-foundry] If the window is blank, close it and run this script again."

exec npm run dev
