#!/usr/bin/env bash
set -euo pipefail

collection_review="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
foundry_root="$(cd "$collection_review/../../../.." && pwd)"
game_dir="$foundry_root/projects/fishing-2d/game"
godot_app="$HOME/.gamefactory/toolchain/godot/Godot_mono.app"
scratch="$foundry_root/work/reef-expansion-20261123/collection-review"
window_helper="$scratch/window-helper"

if [[ ! -f "$game_dir/project.godot" || ! -x "$godot_app/Contents/MacOS/Godot" ]]; then
  printf '%s\n' '需要当前游戏工程和本机 Foundry Godot Mono。' >&2
  exit 1
fi

if [[ "${1:-}" == "--check" ]]; then
  DOTNET_ROOT="$HOME/.gamefactory/toolchain/dotnet" "$godot_app/Contents/MacOS/Godot" --headless \
    --path "$game_dir" --script "$collection_review/review.gd" -- \
    "$collection_review/layouts.json" --headless --check "$foundry_root/work/reef-expansion-20261123/collection-review/check"
  exit
fi

mkdir -p "$window_helper"
if [[ ! -f "$window_helper/liborder_tank.dylib" || "$collection_review/window-order.m" -nt "$window_helper/liborder_tank.dylib" ]]; then
  xcrun clang -dynamiclib -fblocks -framework AppKit \
    "$collection_review/window-order.m" -o "$window_helper/liborder_tank.dylib"
fi
cp "$collection_review/order.gdextension" "$window_helper/order.gdextension"


launch() {
  local log_file="$1"
  shift
  local options=()
  local operations=()
  if [[ $# -gt 0 ]]; then
    options=(-W)
    operations=("$@")
  fi
  open ${options[@]+"${options[@]}"} -n -g -j -a "$godot_app" \
    --env "DOTNET_ROOT=$HOME/.gamefactory/toolchain/dotnet" \
    --env "FOUNDRY_BACKGROUND_PREVIEW=1" \
    --env "DYLD_INSERT_LIBRARIES=$window_helper/liborder_tank.dylib" \
    --args --path "$game_dir" --rendering-method gl_compatibility \
    --log-file "$log_file" --script "$collection_review/review.gd" -- \
    "$collection_review/layouts.json" "$window_helper/order.gdextension" ${operations[@]+"${operations[@]}"}
}

if [[ "${1:-}" == "--capture" ]]; then
  stamp="$(mktemp "$scratch/.capture.XXXXXX")"
  trap 'rm -f "$stamp"' EXIT
  launch "$scratch/capture.log" --capture "$collection_review"
  if [[ ! "$collection_review/placement.json" -nt "$stamp" ]] ||
    ! /usr/bin/grep -Eq '"ok":[[:space:]]*true' "$collection_review/placement.json"; then
    printf '组合截图未通过，请查看 %s\n' "$scratch/capture.log" >&2
    exit 1
  fi
else
  launch "$scratch/interactive.log"
fi
