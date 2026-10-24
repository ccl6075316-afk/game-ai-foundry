"""Separate full-resolution artwork per camera; deterministic 3D pipeline metadata.

Supersedes the rejected combined production-board experiment. No panel packing
of final views. Generic scene reconstruction automation is the token-saving area.
"""
import argparse
import json
import sys
from pathlib import Path

STYLE='Match the supplied approved aquarium pixel illustration finish: fine deliberate crisp pixel clusters, broad coherent painted color masses, natural material planes, subtle detailed highlights and restrained color. No smooth CGI, no photo noise, no uniform speckling. Isolated on pure white, no floor, water, cast shadow or scenery. No labels, panels, collage, text or extra views. One complete object fills most of this image with clean margins. Keep source resolution: this is one full-resolution artwork, not a multi-view sheet.'


def save_brief(folder,rows,reference):
    folder.mkdir(parents=True,exist_ok=True)
    project={'title':folder.name,'description':'Twenty-asset scenery expansion using independently generated full-resolution cameras. Reuse accepted four existing assets. Code automation reduces repeated Codex work in 3D construction, not artwork detail.','art_direction':STYLE,'dimension':'3d','genre':'aquarium_exhibit','gameplay_loop':'Inspect twenty scenery assets in a native Godot catalogue, including ten animated plant species.','session_goal':'Distinct source-matched generated props and plant anatomy with explicit species and independent views.','player_asset':rows[0]['id'],'controls':{'move_left':['A'],'move_right':['D'],'inspect':['Mouse']},'viewport':rows[0]['generation_size'],'camera':{'mode':'static'},'visual_reference':str(reference).replace('\\','/')}
    (folder/'brief.draft.json').write_text(json.dumps({'project':project,'assets':rows},ensure_ascii=False,indent=2),encoding='utf-8')
    print(folder/'brief.draft.json')


def asset(name,prompt,size):
    w,h=size
    return {'id':name,'name':name,'type':'background','usage':'world_background','generate_method':'image','description':prompt,'display_size':{'width':w,'height':h},'generation_size':{'width':w,'height':h},'aspect_ratio':'1:1' if w==h else ('2:3' if h>w else '3:2'),'use_style_img2img':True,'style_group':'aquascape_full_views_v5','style_anchor_kind':'visual_reference'}


def front_briefs(root,catalog):
    for kind in ['plants','solids']:
        rows=[]
        for s in catalog[kind]:
            desc=(s['scientific_name']+'. '+s['morphology']) if kind=='plants' else s['shape']
            prompt=f'''Create the definitive FRONT artwork of this NEW aquarium scenery design: {desc}
{STYLE}
Camera: strict orthographic FRONT ELEVATION from +Z toward -Z, eye exactly level at the object's center. X is horizontal, Y vertical. No visible area of horizontal top planes from camera tilt; do not use a three-quarter/isometric camera. Preserve believable painted 3D volume and material.
The reference determines pixel drawing finish only; do not copy the reference species or existing prop design. Entire plant root crown/root tips or whole stone/wood base and all extremities must be visible. For a plant, show natural three-dimensional leaf arrangement, distinct leaf identities, anatomically correct base, no pot/soil/rock/wood. For wood, continuous grain through every fork and natural irregular blunt broken ends; no geometric tubes or spikes. One complete illustration, no auxiliary objects.'''
            size=(1024,1536) if kind=='plants' or s['id']=='basalt_column' else (1536,1024)
            rows.append(asset(s['id']+'_front',prompt,size))
        save_brief(root/f'projects/aquascape-{kind}-fronts-v5',rows,root/f'projects/aquascape-{kind}-20-v5/style-reference.png')


def auxiliary(root,catalog):
    for kind in ['plants','solids']:
        for s in catalog[kind]:
            desc=(s['scientific_name']+'. '+s['morphology']) if kind=='plants' else s['shape']
            reference=root/f'projects/aquascape-{kind}-fronts-v5/output/{s["id"]}_front_raw.png'
            if not reference.exists():
                print(json.dumps({'skipped':s['id'],'reason':'Front source is still being generated; do not start dependent views.'}))
                continue
            rows=[]
            for view in ['right','top']:
                camera=('Camera is exactly at the RIGHT END, looking along -X. Orthographic perpendicular end elevation. Horizontal image axis is front/back Z depth, vertical is Y height. The long X axis points straight at the viewer and disappears in projection: horizontal long limbs become short broken end faces. Do NOT show the long front facade again. Match FRONT height and branch elevations.' if view=='right' else 'Camera is directly overhead at +Y, looking straight down -Y. True ORTHOGRAPHIC TOP PLAN: X horizontal and Z depth vertical, image top is rear -Z, image bottom is front +Z. All height foreshortens away. Upright branches become short oval end faces; do not draw their full height upward on the page. For rock, show only footprint and upward-facing planes, with NO visible vertical front facade. For plants, show spread of foreshortened overlapping blades around the same crown, not another upright frontal plant. No isometric or three-quarter tilt.')
                prompt=f'''Render ONE {view.upper()} view of the EXACT SAME object in the supplied front artwork, not a new similar design. Subject: {desc}
{STYLE}
{camera}
Keep every source branch, knot, root foot, leaf identity, stone shoulder and fracture as the same physical object seen from the new camera. Match the source's painted material, color palette and fine pixel finish exactly. Infer hidden surfaces consistently, no new branches or decorative details. This single full-resolution image is a camera-specific material donor and form reference. One complete subject only; no labels, dimensions, inset, extra view or diagram.'''
                size=(1024,1536) if kind=='plants' and view=='right' else (1536,1536)
                rows.append(asset(s['id']+'_'+view,prompt,size))
            if kind=='plants':
                prompt=f'''Create a precise PART SHEET of SIX individually isolated full leaves from the EXACT SAME {desc} in the source artwork.
Match its original fine naturalistic PIXEL ART finish, palette, specific leaf widths, venation, wrinkles and material. White background, no shadow or scenery.
Exactly 3 columns by 2 rows, ONE COMPLETE LEAF including its petiole/basal strip in each cell. Stems at BOTTOM, tips at TOP. All six connected leaves fully inside their cells with generous white gaps, no overlap or grid lines, no text, no roots or whole plant. Six different natural sizes and bends, not six copies: large mature blade, smaller mature blade, younger upright blade, gently cupped blade, sideways curled blade, unfolding young blade. Keep narrow ribbon species genuinely narrow and broad ovate species genuinely broad. Use only variations appropriate to this species; do not turn grass into a fern or add leaflets. This is a dedicated high-resolution leaf sheet only, not packed alongside other views. Its exact original painted silhouettes will become individually shaped 3D leaf shells.'''
                rows.append(asset(s['id']+'_leaves',prompt,(1536,1024)))
            save_brief(root/f'projects/aquascape-{s["id"]}-views-v5',rows,reference)


def plans(root,folder):
    sys.path.insert(0,str(root/'cli'))
    from asset_pipeline import load_brief,build_prompt_scaffold
    from shared_context import build_role_context
    from generation_fingerprint import embed_generation_fingerprint
    from plan_io import build_handoff,save_handoff
    from brief_shards import resolve_asset_specs
    project,assets=load_brief(folder/'brief.json');raw={s['id']:s for s in resolve_asset_specs(folder/'brief.json')}
    for spec in assets:
        plan=build_prompt_scaffold(project,spec,assets=assets).to_dict()
        plan.update(prompt=spec.description,prompt_source='explicit_full_view_template',image_model='openai/gpt-image-2',negative_hints=['One camera-specific full-resolution artwork; no packed views.','No isometric tilt in orthographic cameras.'])
        plan['validation']['forbid_uniform_white_studio']=False
        save_handoff(folder/f'plans/{spec.id}.json',build_handoff(embed_generation_fingerprint(plan,spec=spec,project=project,raw_shard=raw[spec.id]),context=build_role_context(project,spec)))
    print(json.dumps({'ok':True,'project':folder.name,'plans':len(assets),'resolution_preserved':True}))


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--input',type=Path,required=True);p.add_argument('--mode',choices=['fronts','auxiliary','plans'],required=True);p.add_argument('--project',type=Path);p.add_argument('--category',choices=['plants','solids']);a=p.parse_args();catalog=json.loads(a.input.read_text(encoding='utf-8'))
    if a.category:catalog['plants' if a.category=='solids' else 'solids']=[]
    if a.mode=='fronts':front_briefs(a.root,catalog)
    elif a.mode=='auxiliary':auxiliary(a.root,catalog)
    else:plans(a.root,a.project)


if __name__=='__main__':main()
