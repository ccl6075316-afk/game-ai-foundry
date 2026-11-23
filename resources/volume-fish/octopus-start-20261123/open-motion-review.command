#!/bin/zsh
set -e
review_dir="${0:A:h}/motion-r7/review"
exec /usr/bin/open -n -a /Users/czl/.gamefactory/toolchain/godot/Godot_mono.app --env DOTNET_ROOT=/Users/czl/.gamefactory/toolchain/dotnet --args --path "$review_dir" --rendering-method gl_compatibility --audio-driver Dummy --script "$review_dir/Actions.gd"
