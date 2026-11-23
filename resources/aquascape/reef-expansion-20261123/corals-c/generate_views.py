"""Prepare and run source-art workflow for six orthographic material directions."""
import json
from pathlib import Path
import subprocess
import sys

folder = Path(__file__).resolve().parent
root = folder.parents[3]
sys.path.insert(0, str(root / "resources/scripts/aquascape"))
from prepare_full_views_catalog import asset, plans

profile = json.loads((folder / "profile.json").read_text())
batch = int(sys.argv[1])
selected = profile[2 * batch - 2: 2 * batch]
if not selected:
    raise ValueError("Batch must be from 1 to 7")
project = root / "projects" / f"aquascape-c-six-material-{batch:02d}-20261123"
project.mkdir(exist_ok=True)
seed = root / "projects/aquascape-reef-foundation-style-r2-20261123"
base = json.loads((seed / "brief.draft.json").read_text())
style = seed / "output/reef_backwall_front_raw.png"
rows = []
for key, name, species, _, _, dims, _, shape, *_ in selected:
    obj = f"{species}, " if species else ""
    prompt = f"""A six-view orthographic turnaround material design for ONE identical aquarium reef animal colony, {obj}{shape}
The 3D design spans X width {dims[0]}, Y height {dims[1]}, Z depth {dims[2]} meters. Material: clean aquarium pixel art, match the confident crisp sparse pixel clusters and coherent color masses of the style image. The reference shows pixel finish only, NOT subject matter. Render a different animal, no rocks apart from tiny substrate contact if essential.
Strict evenly spaced 3-column by 2-row layout of exactly SIX views on solid completely plain white. Each equal panel contains one whole isolated object, with at least 24px white gutters all around. No grids, borders, typography, shadows falling on ground, perspective or tilt:
upper left = FRONT from +Z, orthographic level; upper center = RIGHT from +X, orthographic level; upper right = BACK from -Z, orthographic level.
lower left = LEFT from -X, orthographic level; lower center = TOP from +Y straight down; lower right = BOTTOM from -Y straight up, shows only side undersides and basal attachment, NO view into upward facing openings.
Compare opposite silhouettes: preserve mirrored structural landmarks, the same branch junctions, height and number of visible major lobes. Different physical planes should be visible on reverse and side, not duplicate front art. Top must be parallel plan view with no standing wall; bottom is not a view from above. Contact foot is low, small, natural. No floor, water background, fish, adjacent props, blurry noise, antialiasing or outlines in white."""
    rows.append(asset(key, prompt, (1536, 1024)))
title = f"Reef animals C, six-view material source {batch:02d}"
base["project"].update(title=title, description=title, visual_reference=str(style),
                       player_asset=rows[0]["id"], viewport=rows[0]["generation_size"],
                       art_direction="Original clean crisp aquarium pixel art, six simultaneous orthographic directions per material sheet.")
draft = project / "brief.draft.json"
draft.write_text(json.dumps({"project": base["project"], "assets": rows}, ensure_ascii=False, indent=2) + "\n")
brief = project / "brief.json"
manifest = project / "pipeline/manifest.json"
with (project / "setup.log").open("a") as log:
    def cli(*args):
        subprocess.run(["bash", "gamefactory", *map(str, args), "--json"], cwd=root, check=True, stdout=log, stderr=log)
    if not brief.exists():
        cli("brief", "freeze", "--input", draft, "--output", brief)
    cli("workflow", "context", "--brief", brief)
    cli("workflow", "validate", "--brief", brief)
    if not manifest.exists():
        cli("workflow", "init", "--brief", brief)
        plans(root, project)
        cli("workflow", "run", "--manifest", manifest, "--stage", "assets", "--jobs", 2)
    cli("workflow", "status", "--manifest", manifest)
