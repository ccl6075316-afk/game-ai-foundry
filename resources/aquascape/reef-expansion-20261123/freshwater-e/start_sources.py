from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import json
import subprocess
import sys

root = Path.cwd()
sys.path.insert(0, str(root / 'resources/scripts/aquascape'))
from prepare_full_views_catalog import asset, plans

batch = root / 'resources/aquascape/reef-expansion-20261123/freshwater-e'
base = json.loads((root / 'projects/aquascape-reef-foundation-style-r2-20261123/brief.draft.json').read_text())

# Physical scene dimensions are design targets for the game.
subjects = {
    'wood_hollow_tunnel': ('掏空沉木隧道', 'wood', [2.75, 0.92, 1.05], 'A centuries-weathered full hollow log resting lengthwise along X. One cylindrical heartwood tunnel with two open end faces, facing +X and -X. A genuine hollow dark interior with a thick irregular wooden ring at each end and no side window. Side silhouette lies low, slopes unevenly down from the right, has splintered butt end, blunt fractured wood ridge, a thicker bark foot and a few creased flutes. Clear narrow gray-brown bark planes, warmer umber end grain and a gray-orange inner ring.'),
    'wood_overhang_perch': ('横伸伏木架', 'wood', [2.85, 1.15, 1.48], 'One low horizontally growing snag from the edge of a river, rooted with two broad continuous feet on front-left and back-left. An asymmetric swept thick dead limb cantilevers to the right, forming a true overhang with narrow clear space below. Broad angular intact splintered grain, a rounded swept nose with one blunt break and ridges across the upper flank. No two-legged bridge or horizontal log cylinder. Auburn umber core, slate brown bark and pale aged grain along breaks.'),
    'wood_upturned_root_plate': ('倒伏树盘', 'wood', [2.35, 1.66, 1.58], 'A naturally uprooted sideways tree stump with exposed root plate taller than it is deep and a short trunk base sticking out the back. Dense fluted wood forms an irregular upright half fan to one side of the old trunk; broad tapered root fins sweep down into two asymmetrical contact feet, with naturally torn fingers. Brown weathered grain, ridged attachment and mud-gray underside; medium-dark root tangle recesses at center. No soil clod, no leaves, no other objects.'),
    'wood_low_root_weave': ('低展根网', 'wood', [2.39, 0.48, 1.67], 'A sprawling subdued low freshwater driftwood root from an undercut bank. One short tapered crown on the left-back, splitting into asymmetrical concave finger roots spreading rightward and forward flush with the bottom, blunt fractured roots and real negative spaces visible from overhead. Clear grain runs through connected forks. Deep weathered walnut with warm faint beige breaks, thin muted gray edges. No roots pointing high in the air, no dead twigs placed separately.'),
    'hairgrass_meadow': ('细发草甸', 'plant', [0.78, 0.32, 0.49], 'A naturally grown contiguous underwater patch of Eleocharis acicularis (needle spikerush), low and leafy with fine tufted grass-like bright olive-green culms, their gentle fine arches emerging from spreading low clonal runners with short sand-colored roots, no seed head. Entire natural runner patch on white. Keep base, clumps and runner positions consistent across opposite views.'),
    'lake_quillwort_rosette': ('水韭根冠', 'plant', [0.56, 0.43, 0.48], 'A natural submerged Isoetes lacustris lake quillwort with a compact short brown corm and complete small pale anchoring root system. Thickened bases support green glossy, straight to gently splayed long tapered quill leaves, mostly erect in a clean single basal rosette. The crown is not a carpet. Do not show spores, decoration or a pot.'),
    'bolbitis_fern_clump': ('沉木羽叶蕨', 'plant', [0.93, 0.57, 0.62], 'One natural cluster of submerged Bolbitis heudelotii with rich cool translucent olive divided pinnate fronds emerging from a long horizontal dark creeping rhizome with complete rootlets, clearly separated and slightly translucent lanceolate pinnae, uneven branching frond silhouettes. Show the complete naturally attached root system without supporting wood or rock.'),
    'marsilea_runner_patch': ('匍匐四叶苹丛', 'plant', [0.69, 0.19, 0.46], 'A naturally grown freshwater submerged Marsilea hirsuta patch. Low slender horizontal runners with tiny pale short roots at joints and spaced soft green upright petioles carrying rounded spatulate leaflets, several ripe pinnately arranged four-lobed blades, a few single or divided submerged forms in the same natural patch. Short carpet growth, never many similar copies of one leaflet or the upright clover meadow of a terrestrial plant.'),
    'water_lily_float_stems': ('长柄浮叶睡莲', 'plant', [1.23, 1.58, 1.04], 'One natural freshwater Nymphaea water lily group growing from a small dark anchored horizontal rhizome, long slender curved petioles rise through the water to broad horizontal olive-green almost circular floating leaves with deep radial sinuses. Sparse foliage and clearly exposed positive curving stalks, with only one or two small submersed leaves, no flowers. Exact top shows several overlapping circular leaves with slit edges.'),
    'duckweed_root_patch': ('细根浮萍毯', 'plant', [0.52, 0.10, 0.43], 'A naturally clustered patch of surface-floating common duckweed, Lemna minor morphology as reference. A dense but broken sheet of small rounded smooth green fronds packed in connected pairs and islands, with fine short brown-green pendant root threads descending individually under fronds. No rooted bottom or long plant stalks. Show separated surface islands, not one continuous flat solid green blob.'),
    'laceleaf_rosette': ('透孔莲座水草', 'plant', [0.78, 0.72, 0.63], 'One whole naturally grown Madagascar lace plant Aponogeton madagascariensis rooted crown with raised narrow oval leaf blades, recognizable pale-to-olive fenestrated lace lattice primarily where soft tissue is naturally absent, distinct anatomical midribs and leaf veins, no emergent blooms. Leaf tips sweep out into space, anchored compact tuber and dark creamy roots.'),
    'riverwort_moss_mat': ('溪床贴石藓片', 'plant', [0.48, 0.14, 0.32], 'One natural very low irregular attached patch of Riccardia chamedryfolia-like freshwater liverwort, compact dark green flattened divided thalli compactly tangled into overlapping tiny shallow forks, with diffuse thin reddish rhizoids under the mat. Colored leafy edges read as small layered flat fans and matte green pads, not feathery stems; exclude the actual rock from every view.'),
}

layout = '''
Start the design by showing all six views of the same exact material-painted asset on one 3 columns by 2 rows board with wide white gaps and only compact labels above each drawing. Top row: FRONT, RIGHT, BACK. Bottom row: LEFT, TOP, BOTTOM. Each panel contains only one precise orthographic isolated view. Material: closely match crisp deliberate studio pixel clusters of the supplied reference; no blurry bilinear lines, reflective CGI or photography. Pure white background, no ground shadow, no water or environment.
FRONT +Z and BACK -Z show horizontally mirrored physical silhouettes. RIGHT +X and LEFT -X are exact end projections where the long X axis points into the page; only show Z width at those ends. TOP +Y directly down, rear at the top, show the actual plan of the complete shape. BOTTOM -Y directly up, front at the top, show the same footprint and painted undersides. No tilt or three-quarter camera in any panel. Keep the object, branch network, form breaks and material consistent across all views. Fit entire object into each cell. Choose a coherent readable spatial arrangement with genuine depth based on the given natural body, not a different object in each panel.
'''

revisions = {
    'wood_upturned_root_plate': 'The subject is a short upright ear-shaped uprooted root plate, a jagged upright broad shield of gnarled flattened roots with scalloped outer tips and layers from an uprooted beech. It is longer across the upright root disk than the trunk projects. Broad face of disk faces FRONT; from BACK show trunk base pointing directly along Z away from viewer (appears as one squat circle). From TOP show a short worn trunk stub pointing to the rear from the broad thin root disc. Its entire trunk is less than HALF HEIGHT of the standing root plate and never extends horizontally sideways along X. No soil, no gravel, no moss or plant foliage. Maintain this design in all six. Ignore the shape of visual reference, use its finish only.',
    'lake_quillwort_rosette': 'Botanically precise submerged Isoetes lacustris lake quillwort. Botanically distinctive needle-like awl-shaped quills as fine as chives, grass-blade outlines and mostly pencil straight, sharp stiff tips. The moderate quills form a sparse dense-centered single upstanding rosette with an open spreading perimeter. Glossy thin taper and green surface, conspicuous short brown corm and thin pale roots at the same ground level. Each quill is less than four percent of its own height at its widest point. NO sword leaves, NO broad foliage, NO thick leaf tips, NO detached elements. All six views of this plant only.',
    'riverwort_moss_mat': 'Only a natural LOW broad olive-green growing patch of irregularly flattened branched aquatic liverwort thalli as found on stream rock. Completely remove any foreground secondary object. The isolated tiny lobed branching thalli are green through their mass and form strata; the roots are a few tiny dark reddish rhizoids immediately below the overlapping mats. A small empty gap in the irregular low green patch reveals white backdrop. Absolutely no piece of driftwood or pebbles in any panel. Favor authentic dark pinnately branched flattened lobes and lively but restrained pixel shading. The plant is the only subject in all six panels.',
}
def run_item(arg):
    key, revised = arg
    name, kind, size, subject = subjects[key]
    if revised:
        subject = revisions[key]
    folder = root / f'projects/aquascape-e-{key.replace("_", "-")}{"-r2" if revised else ""}'
    folder.mkdir(exist_ok=True)
    if (folder / 'pipeline/manifest.json').exists():
        raise SystemExit(f'Existing workflow needs status or resume: {folder}')
    style = root / ('projects/aquascape-solids-20-v5/style-reference.png' if kind == 'wood' else 'projects/aquascape-plants-20-v5/style-reference.png')
    dimensions = ' × '.join(map(str, size))
    row = asset(key+'_six_views', f'Initial design and color source for freshwater aquarium scenery. Design dimensions X × Y × Z: {dimensions} m. {subject}\n{layout}', (1536,1024))
    project = {**base['project'], 'title': name, 'description': 'Freshwater scenery six-view source', 'visual_reference':str(style), 'player_asset':row['id'], 'viewport':row['generation_size']}
    (folder/'brief.draft.json').write_text(json.dumps({'project':project,'assets':[row]},ensure_ascii=False,indent=2)+'\n')
    with (folder/'setup.log').open('w') as logfile:
        def cli(*args):
            subprocess.run(['bash','gamefactory',*map(str,args),'--json'],check=True,stdout=logfile,stderr=logfile)
        frozen=folder/'brief.json'
        cli('brief','freeze','--input',folder/'brief.draft.json','--output',frozen)
        cli('workflow','context','--brief',frozen)
        cli('workflow','validate','--brief',frozen)
        cli('workflow','init','--brief',frozen)
        plans(root,folder)
        cli('workflow','run','--manifest',folder/'pipeline/manifest.json','--stage','assets','--jobs',1)
    print(folder.name, 'source generated for review', flush=True)

if __name__ == '__main__':
    (batch/'subjects.json').write_text(json.dumps({k:dict(zip(('name','kind','dimensions_m','form_reference'),v)) for k,v in subjects.items()},ensure_ascii=False,indent=2)+'\n')
    with ThreadPoolExecutor(max_workers=2) as pool:
        arguments = sys.argv[1:]
        revised = '--revise' in arguments
        keys = [a for a in arguments if a != '--revise'] or (revisions if revised else subjects)
        list(pool.map(run_item, [(key, revised) for key in keys]))
