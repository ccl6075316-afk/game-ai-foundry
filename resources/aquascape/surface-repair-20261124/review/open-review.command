#!/usr/bin/env bash
set -euo pipefail

review="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
foundry="$(cd "$review/../../../.." && pwd)"
game="$foundry/projects/fishing-2d/game"
helper="$foundry/resources/aquascape/reef-expansion-20261123/collection-review"
scratch="$foundry/work/surface-repair-20261124/review"
godot_app="${GF_GODOT_APP:-$HOME/.gamefactory/toolchain/godot/Godot_mono.app}"
export DOTNET_ROOT="${DOTNET_ROOT:-$HOME/.gamefactory/toolchain/dotnet}"
export PATH="$DOTNET_ROOT:$PATH"

if [[ ! -f "$game/project.godot" || ! -x "$godot_app/Contents/MacOS/Godot" ]]; then
    printf '%s\n' '需要当前 fishing-2d 工程和本机 Godot Mono。' >&2
    exit 1
fi

mkdir -p "$scratch"
if [[ ! -f "$game/.godot/mono/temp/bin/Debug/GameFactoryDemo.dll" ]]; then
    dotnet build "$game/GameFactoryDemo.csproj" --nologo -v:q
fi
if ! "$godot_app/Contents/MacOS/Godot" --headless --editor --import --path "$game" >"$scratch/import.log" 2>&1; then
    cat "$scratch/import.log" >&2
    exit 1
fi
if [[ ! -f "$scratch/liborder_tank.dylib" || "$helper/window-order.m" -nt "$scratch/liborder_tank.dylib" ]]; then
    xcrun clang -dynamiclib -fblocks -framework AppKit "$helper/window-order.m" -o "$scratch/liborder_tank.dylib"
fi
cp "$helper/order.gdextension" "$scratch/order.gdextension"

arguments=()
flags=()
label=window
for option in "$@"; do
    case "$option" in
        --before)
            python="$foundry/.venv/bin/python"
            [[ -x "$python" ]] || python=python3
            "$python" "$review/prepare_baseline.py" "$scratch/baseline"
            arguments+=(--baseline "$scratch/baseline")
            ;;
        --check)
            mkdir -p "$scratch/check"
            arguments+=(--check "$scratch/check/comparison.png")
            label=check
            flags=(-W)
            ;;
        *)
            printf 'Unknown option %s\n' "$option" >&2
            exit 2
            ;;
    esac
done
open ${flags[@]+"${flags[@]}"} -n -g -j -a "$godot_app" \
    --env "DOTNET_ROOT=$DOTNET_ROOT" \
    --env "FOUNDRY_BACKGROUND_PREVIEW=1" \
    --env "DYLD_INSERT_LIBRARIES=$scratch/liborder_tank.dylib" \
    --args --path "$game" --rendering-method gl_compatibility --log-file "$scratch/$label.log" \
    --script "$review/inspector.gd" -- "$scratch/order.gdextension" ${arguments[@]+"${arguments[@]}"}
if [[ "$label" == check ]]; then
    /usr/bin/grep -F 'Review ready:' "$scratch/check.log"
fi
