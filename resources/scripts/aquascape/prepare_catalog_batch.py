"""Fixed aquascape production-board briefs and no-LLM handoffs.

The user explicitly authorized templating the settled workflow to save tokens.
The official scaffold/context/fingerprint builders are reused, never forged.
"""
import argparse
import json
import sys
from pathlib import Path
from PIL import Image

STYLE='Detailed naturalistic PIXEL ART matching the supplied approved aquarium artwork: deliberate crisp pixel clusters, subtle painted highlights, coherent broad material planes, believable asymmetry and restrained colors. Not CGI, not smooth airbrush, not photographic grain, not uniform noise. White background throughout, no water, floor, cast shadows, frames or diagram lines.'


def brief(root,catalog,kind):
    folder=root/f'projects/aquascape-{kind}-20-v5';folder.mkdir(exist_ok=True)
    board=Image.new('RGB',(3072,2048),'white')
    keys=['anubias_master','java_fern_master','rock_master','driftwood_master']
    for i,key in enumerate(keys):board.paste(Image.open(root/f'projects/aquascape-source-v2/output/{key}_raw.png').convert('RGB'),((i%2)*1536,(i//2)*1024))
    board.save(folder/'style-reference.png')
    rows=[]
    for spec in catalog['plants' if kind=='plants' else 'solids']:
        if kind=='plants':
            prompt=f'''Make ONE square technical ART PRODUCTION BOARD of exactly one submerged aquarium plant species: {spec['scientific_name']}. {spec['morphology']}
{STYLE}
The reference establishes the drawing FINISH only. Do not copy its plant species or rock/wood subjects.
Layout is strict: UPPER HALF (y=0 to 48%): THREE equal-width cells in one row, showing the SAME complete plant in FRONT, RIGHT SIDE and TOP views, with small labels FRONT / SIDE / TOP only above those views. FRONT camera level, SIDE perpendicular, TOP straight overhead. Root crown, roots and every leaf tip fully visible. Same leaf identities and same physical arrangement in all three views. TOP shows a spread of foreshortened leaves around the crown, not another front elevation.
LOWER HALF (y=54% to 98%): EXACTLY SIX isolated full leaves from that plant, in a 3-column by 2-row regular layout. Each lower cell has ONE individual blade WITH ITS FULL PETIOLE OR BASAL STRIP, stem at BOTTOM, tip at TOP, no roots. Six distinct sizes, curvatures and ages, same palette and vein pattern as the plant above. The lower leaves have clean white gaps and do not touch each other or any panel boundary. Keep narrow ribbon leaves genuinely narrow. No whole plants in the lower cells. No extra miniatures, no dimension arrows, no other labels. Every lower leaf must be entirely connected from stem to tip and fully inside its cell. These exact generated leaf silhouettes and paint will be traced into 3D, so do not substitute texture swatches.'''
        else:
            prompt=f'''Make ONE square FOUR-VIEW technical production board for ONE exact aquarium scenery object. Design: {spec['shape']}
{STYLE}
Exactly four equal cells in a 2x2 layout with white gaps: HERO in UPPER LEFT, FRONT in UPPER RIGHT, RIGHT in LOWER LEFT, TOP in LOWER RIGHT. Only these small four labels at top of each cell. Same exact object in all cells, shared landmarks and material patterns.
HERO is an attractive three-quarter reference showing the whole object and its natural material.
FRONT is a strict level orthographic elevation, looking along the depth axis: world length X horizontal, height Y vertical. No camera tilt or perspective.
RIGHT is a strict orthographic END view from the object's RIGHT end, looking along negative X. Horizontal dimension is the front-back DEPTH, not the object's long facade. Main horizontal limbs point at the viewer and foreshorten into broken end faces. Keep the height equal to FRONT.
TOP is a strict overhead PLAN, looking vertically downward. Horizontal world X length equals FRONT; vertical world Z footprint depth equals RIGHT width. Tall upright portions become short foreshortened end faces, not tall branches. Do not show vertical front walls in TOP. TOP must not be a three-quarter object. No copied front silhouette in all cells.
Fit all four complete objects inside their own cell with margin. No redesign, no detached material swatches, no dimensions, no cut-off tips. The reference is for pixel drawing finish only; create the specified new distinctive object, not a copy of the reference rock or wood.'''
        rows.append({'id':spec['id'],'name':spec['id'],'type':'background','usage':'world_background','generate_method':'image','description':prompt,'display_size':{'width':2048,'height':2048},'generation_size':{'width':2048,'height':2048},'aspect_ratio':'1:1','use_style_img2img':True,'style_group':'aquascape_catalog_v5','style_anchor_kind':'visual_reference'})
    payload={'project':{'title':f'aquascape-{kind}-20-v5','description':'Expand the approved scenery process to twenty distinct assets, reusing four existing assets and generating sixteen new designs. Fixed prompts and mechanical operations are deterministic; visual acceptance remains manual.','art_direction':STYLE,'dimension':'3d','genre':'aquarium_exhibit','gameplay_loop':'Inspect source-matched scenery in a rotating Godot catalogue.','session_goal':'Ten species of gently animated plants and ten static stone/wood designs including existing accepted trials.','player_asset':rows[0]['id'],'controls':{'move_left':['A'],'move_right':['D'],'inspect':['Mouse']},'viewport':{'width':2048,'height':2048},'camera':{'mode':'static'},'visual_reference':str(folder/'style-reference.png').replace('\\','/')},'assets':rows}
    (folder/'brief.draft.json').write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8');print(folder/'brief.draft.json')


def plans(root,kind):
    sys.path.insert(0,str(root/'cli'))
    from asset_pipeline import load_brief,build_prompt_scaffold
    from shared_context import build_role_context
    from generation_fingerprint import embed_generation_fingerprint
    from plan_io import build_handoff,save_handoff
    from brief_shards import resolve_asset_specs
    folder=root/f'projects/aquascape-{kind}-20-v5';path=folder/'brief.json'
    project,assets=load_brief(path);raw={s['id']:s for s in resolve_asset_specs(path)}
    for spec in assets:
        plan=build_prompt_scaffold(project,spec,assets=assets).to_dict()
        plan.update(prompt=spec.description,prompt_source='user_authorized_fixed_aquascape_template_v5',image_model='openai/gpt-image-2',negative_hints=['Preserve strict panel layout and true orthographic cameras.','No extra subjects or scenery; keep complete connected parts.'])
        plan['validation']['forbid_uniform_white_studio']=False
        plan=embed_generation_fingerprint(plan,spec=spec,project=project,raw_shard=raw[spec.id])
        handoff=build_handoff(plan,context=build_role_context(project,spec))
        save_handoff(folder/f'plans/{spec.id}.json',handoff)
    print(json.dumps({'ok':True,'plans':len(assets),'prompt_llm_calls':0,'image_generation':'Still required; no procedural replacement art.'}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--mode',choices=['briefs','plans'],required=True);a=p.parse_args()
    catalog=json.loads(a.input.read_text(encoding='utf-8'))
    for kind in ['plants','solids']:
        if a.mode=='briefs':brief(a.root,catalog,kind)
        else:plans(a.root,kind)


if __name__=='__main__':main()
