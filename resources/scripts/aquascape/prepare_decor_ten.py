"""Independent front/right/top source briefs for ten aquarium ornaments."""
import argparse,json
from pathlib import Path
from prepare_full_views_catalog import asset,save_brief

STYLE='Match the supplied established fish/aquascape illustration for detailed naturalistic PIXEL ART: deliberate fine crisp pixel clusters, coherent painted volume, restrained believable colors and readable material wear. No smooth CGI, photograph, low-poly render, chibi toy, uniform procedural noise or thick black comic outline. One complete isolated object on pure white, generous clean white margin, no floor or cast shadow, no water, fish, plants, text, labels or extra objects. No diagram, collage or packed views. Preserve full native resolution.'
def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--mode',choices=['fronts','auxiliary'],required=True);a=p.parse_args();root=a.root.resolve();catalog=json.loads((root/'resources/aquascape/decor-10-v1.json').read_text(encoding='utf-8'))
    if a.mode=='fronts':
        rows=[]
        for s in catalog['assets']:
            camera='Strict orthographic FRONT ELEVATION from +Z toward -Z, eye exactly level at object center. X horizontal, Y vertical. Do not tilt the camera or show an isometric view. Ship and pipe long axes run horizontally along X. Jar opens upward on Y; anchor broad face faces the camera.'
            prompt=f'Create the definitive complete FRONT source artwork for this aquarium ornament: {s["shape"]}\n{STYLE}\n{camera}\nThe reference controls drawing finish only; do not copy the fish or add fish scales. This original whole-object drawing will define the exact later 3D design. Keep genuine openings and stable broad connections readable.'
            size=(1024,1536) if s['id'] in ['iron_anchor','broken_column','stone_lantern','ruin_arch','terracotta_jar'] else (1536,1024)
            rows.append(asset(s['id']+'_front',prompt,size))
        folder=root/'projects/aquascape-decor-fronts-v1';reference=root/'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted/great_hammerhead/inputs/style-reference.png';save_brief(folder,rows,reference)
        draft=folder/'brief.draft.json';data=json.loads(draft.read_text(encoding='utf-8'));data['project'].update(title='Aquascape ten ornaments front artwork v1',description='Ten individually generated aquarium ornaments beyond natural rocks, wood and plants; each will receive separate full-resolution right and top artwork.',art_direction=STYLE,gameplay_loop='Freely place, rotate, scale and partially bury ten themed ornaments in the existing editable substrate trial.',session_goal='Ten consistent original designs with complete silhouettes, deliberate openings and later independent side/top donors.');draft.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
    else:
        manifest=json.loads((root/'projects/aquascape-decor-fronts-v1/output/assets-manifest.json').read_text(encoding='utf-8'))
        for s in catalog['assets']:
            entry=manifest['assets'][s['id']+'_front']
            if entry.get('review',{}).get('status')!='accepted':raise ValueError('Front artwork not reviewed: '+s['id'])
            reference=root/f'projects/aquascape-decor-fronts-v1/output/{s["id"]}_front_raw.png';rows=[]
            for view in ['right','top']:
                camera=('Strict orthographic RIGHT END ELEVATION, camera at +X looking along -X. Horizontal image axis is -Z depth, vertical is Y. The front long horizontal X axis disappears into the image: ship/bridge/pipe/chest must be seen END-ON, not their long front again. For the pipe show the genuinely open round end mouth.' if view=='right' else 'Strict orthographic TOP PLAN, camera at +Y looking straight down -Y. X horizontal, Z depth vertical; rear -Z is image top and front +Z is image bottom. Height disappears: do not draw the upright facade or a three-quarter/isometric view. For the jar show its open mouth, thick walls and dark cavity with a solid bottom. For ship show its open cargo well and connected low hull; anchor appears as a narrow but finite forged thickness footprint.')
                subject=s['shape'].replace('Broad front elevation shows the long side wall; right end elevation shows the circular open mouth and thick ring wall.','')
                prompt=f'Render ONE {view.upper()} view of the EXACT SAME designed ornament shown in the supplied FRONT artwork, not a new similar object. Subject: {subject}\n{STYLE}\n{camera}\nPreserve every actual source component, relative proportion, worn edge, opening, material color and landmark as the same physical object from the new direction. Actual reference proportions take priority over approximate descriptive dimensions. Infer hidden surfaces consistently; do not invent extra feet, posts, holes or decorations. Genuine tunnels remain open; jar and cargo-well cavities have solid bottoms. This is one full-resolution camera-specific art donor, no other views or annotations.'
                size=(1024,1536) if view=='right' and s['id'] in ['iron_anchor','broken_column','stone_lantern','ruin_arch','terracotta_jar'] else ((1536,1536) if view=='top' else (1024,1024))
                rows.append(asset(s['id']+'_'+view,prompt,size))
            folder=root/f'projects/aquascape-decor-{s["id"]}-views-v1';save_brief(folder,rows,reference)
            draft=folder/'brief.draft.json';data=json.loads(draft.read_text(encoding='utf-8'));data['project'].update(title=s['id']+' independent right/top artwork',description='Two independent full-resolution cameras derived from the reviewed original front ornament design.',art_direction=STYLE,gameplay_loop='Reconstruct this reviewed ornament and place it freely in the substrate trial.',session_goal='Source-consistent right/top donors; visual review before three-dimensional modeling.');draft.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
