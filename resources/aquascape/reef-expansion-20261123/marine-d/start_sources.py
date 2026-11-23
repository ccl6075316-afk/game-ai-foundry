"""Dispatch and track two frozen six-view Foundry jobs at a time."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import sys

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / "resources/scripts/aquascape"))
from prepare_full_views_catalog import asset, plans

BASE_FOLDER = ROOT / "projects/aquascape-reef-foundation-style-r2-20261123"
BASE = json.loads((BASE_FOLDER / "brief.draft.json").read_text())
SUBJECTS = json.loads(Path(__file__).with_name("subjects.json").read_text())
LAYOUT = """One six-direction MATERIAL AND FORM concept sheet, exact regular 3-column by 2-row grid, top row FRONT, RIGHT, BACK, bottom row LEFT, TOP, BOTTOM. All six are the same natural single object, with the same irregular outline, attachment points, color and scale. Put very small labels above the objects with white gap below the labels, each cell has plenty of pure white margin, no bordering box or divider. Keep object safely within the middle 76% of cell height, taking enough space to read at full resolution.
True orthographic FRONT looking from +Z, a straight front elevation; RIGHT from +X a straight vertical end elevation along the long axis; BACK from -Z, agree with FRONT after horizontal mirroring; LEFT from -X, agree with RIGHT after horizontal mirroring. TOP from +Y, looking exactly straight down with rear at the top of the image. BOTTOM from -Y looks directly up with the front at the top of its image, showing the same plan shape together with the attachment area closest to camera. True top and bottom plans: vertical height disappears. Match visible outlines between each opposed pair; interiors paint the real plant overlap and opposite surface detail.
Keep natural pigment and deliberate crisp small pixel clusters like the supplied style reference and no CGI outlines or gradients. White background, no water, bubbles, shadow, 3/4 camera, display pedestal, loose debris, ruler or environment. Paint material at the same style scale in all six cameras. Negative spaces in the cluster must remain white in the matching views. The reference image is color/rendering style only; render the specified organism/structure. Do not copy the species or object in the style reference."""

def run(row):
    key = row["id"]
    folder = ROOT / "projects" / f"aquascape-d-{key}-20261123"
    folder.mkdir(exist_ok=True)
    size = " × ".join(str(value) for value in row["nominal_xyz_m"])
    prompt = f"Initial material art for a new placeable aquarium set. {row['brief']} Target X × Y × Z = {size} meters.\n\n{LAYOUT}"
    spec = asset(f"{key}_six_views", prompt, (1536, 1024))
    props = {**BASE["project"], "title": f"Six views · {row['name_zh']}",
             "description": "Single aquatic organism or root structure six-view concept",
             "visual_reference": str(BASE_FOLDER / "output/reef_shelf_terrace_front_raw.png"),
             "player_asset": spec["id"], "viewport": spec["generation_size"]}
    draft = folder / "brief.draft.json"
    brief = folder / "brief.json"
    manifest = folder / "pipeline/manifest.json"
    draft.write_text(json.dumps({"project":props,"assets":[spec]},ensure_ascii=False,indent=2)+"\n")
    with (folder / "setup.log").open("a") as log:
        def cli(*args):
            subprocess.run(["bash","gamefactory",*map(str,args),"--json"],check=True,stdout=log,stderr=log)
        if not brief.is_file():
            cli("brief","freeze","--input",draft,"--output",brief)
        if not manifest.is_file():
            for step in ("context","validate","init"):
                cli("workflow",step,"--brief",brief)
            plans(ROOT,folder)
        cli("workflow","run","--manifest",manifest,"--stage","assets","--jobs",1)
        cli("workflow","status","--manifest",manifest)
    print(f"{key} finished assets stage",flush=True)

selection = set(sys.argv[1:])
with ThreadPoolExecutor(max_workers=2) as pool:
    jobs = [(row["id"],pool.submit(run,row)) for row in SUBJECTS if not selection or row["id"] in selection]
    for name,job in jobs:
        try:
            job.result()
        except subprocess.CalledProcessError as error:
            print(f"{name}: {error}", file=sys.stderr, flush=True)
