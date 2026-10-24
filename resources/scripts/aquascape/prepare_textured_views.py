"""Prepare reference contact sheets and frozen-brief drafts; never paint textures."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw


def main():
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);a=p.parse_args()
    root=a.root;review=root/'projects/fishing-2d/plans/reviews/aquascape-three-views-v3'
    for kind,master in [('rock','rock_master'),('wood','driftwood_master')]:
        folder=root/f'projects/aquascape-{kind}-materials-v3';folder.mkdir(exist_ok=True)
        board=Image.new('RGB',(3072,2048),'white');draw=ImageDraw.Draw(board)
        original=Image.open(root/f'projects/aquascape-source-v2/output/{master}_raw.png').convert('RGB')
        board.paste(original,(0,0))
        draw.text((1650,180),'UPPER LEFT: COLOR AND PIXEL DRAWING REFERENCE ONLY',fill='black')
        draw.text((1650,240),'BOTTOM: EXACT FRONT / RIGHT END / TOP SHAPES TO PAINT',fill='black')
        for i,view in enumerate(['front','right','top']):
            im=Image.open(review/f'{kind}-{view}.png').convert('RGB')
            # Exact source pixels: contact sheet only, no generated or altered paint.
            board.paste(im,(i*1024+(1024-im.width)//2,1080+(950-im.height)//2))
            draw.text((i*1024+450,1040),view.upper(),fill='black')
        board.save(folder/'reference.png')
        desc=f'''Paint the three BOTTOM grayscale orthographic views in the supplied reference, using the UPPER LEFT original artwork's exact pixel drawing finish and palette. The upper left artwork is only a material reference and must NOT appear in the output. Output ONE white 3072x1024 sheet containing exactly THREE separate views in a single row: FRONT left, RIGHT END middle, TOP right. Small labels FRONT / RIGHT / TOP at the top. Preserve the bottom drawings' silhouettes, cameras and branch/facet identities. Each object fully visible with generous white margin. No dimensions, rulers, diagram lines or other text. Strict orthographic: front is level elevation, side is narrow end-on, top is a flat overhead footprint, no vertical front walls in TOP. Do NOT rotate any gray view into the original artwork's three-quarter camera. Keep exact same object and distinctive landmarks. Refined naturalistic game PIXEL ART with crisp deliberate pixel clusters, broad coherent painted material planes and subtle detail; no CGI, no smooth airbrush or photographic noise. Flat neutral illumination shared by all views, no cast shadows, no scene, no water, no fish or plants. This is full surface artwork for three different projection donors, NOT a seamless material swatch. '''
        if kind=='rock':desc+='Cool slate gray stone with muted warm pale worn edges and deep blue-gray fissures. Preserve high terraced left shoulder, diagonal fracture and scooped lower right shoulder. Continue fractures between front, end and top; no moss, no brown wood. TOP must be overhead planes and footprint only.'
        else:desc+='Desaturated umber and gray-brown driftwood with restrained honey worn grain following every fork. Retain long S-shaped horizontal trunk, broken left root, single short upward fork and two splayed lower roots. RIGHT is the end silhouette with large central broken oval main-trunk face, upright fork behind and root feet below; no long horizontal trunk in RIGHT. TOP has short oval upright stub, not a tall branch. Do not add or remove branches. End grain occurs only at the genuine broken ends; all side grain flows through junctions.'
        draft={'project':{'title':f'aquascape-{kind}-materials-v3','description':'Generated matching-camera pixel material views for the reviewed three-view scenery trial.','art_direction':'Preserve the supplied source pixel artwork finish and exact three-view structure.','dimension':'3d','genre':'aquarium_exhibit','gameplay_loop':'Inspect generated materials on jointly constrained three-view scenery in Godot.','session_goal':'Three source-matched colored orthographic views, then a review-only game preview.','player_asset':f'{kind}_material_views','controls':{'move_left':['A'],'move_right':['D'],'inspect':['Mouse']},'viewport':{'width':3072,'height':1024},'camera':{'mode':'static'},'visual_reference':str(folder/'reference.png').replace('\\','/')},'assets':[{'id':f'{kind}_material_views','name':f'{kind}_material_views','type':'background','usage':'world_background','generate_method':'image','description':desc,'display_size':{'width':3072,'height':1024},'generation_size':{'width':3072,'height':1024},'aspect_ratio':'3:1','use_style_img2img':True,'style_group':'aquascape_v3','style_anchor_kind':'visual_reference'}]}
        (folder/'brief.draft.json').write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf-8')
        print(folder)


if __name__=='__main__':main()
