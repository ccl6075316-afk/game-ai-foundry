# Arapaima species mesh experiments

Blender/Python prototypes for the [2026-10-15 visual investigation](../../../../docs/anvil/debug-sessions/2026-10-15-arapaima-species-mesh.md). `build_arapaima.py` is the latest continuous body/head hypothesis. Numbered copies preserve failed iterations; `graft_old_fins.py` and `graft_old_front.py` are controlled comparisons with the accepted local game GLB. `texture_probe.py` creates diagnostic UV projection only. `render_fair_clay.py` renders eight matched views.

The scripts take explicit input/output arguments after `--` and depend on the local accepted source images and game GLB under `projects/fishing-2d/game/assets/models/fish/`. Those ignored game assets and large generated `.blend`/`.glb` files are not part of this code archive. This experiment is not an accepted volume asset or an animation-ready model.
