"""Freeze hall surface artwork requirements; let Foundry own generation jobs."""
import argparse,json,shutil
from pathlib import Path
from prepare_full_views_catalog import asset,save_brief,plans

STYLE=('Create actual hand-painted PIXEL ART material artwork matching the supplied accepted fish illustration: '
       'deliberate crisp square pixel clusters, restrained natural colors and coherent painted material changes. '
       'Design on a 256 by 256 logical pixel grid enlarged exactly 4x to a native 1024 by 1024 image. '
       'The pixel clusters must be visible and purposeful, not fine photographic grain, random noise or smooth gradients. '
       'This is a full-bleed seamless square ALBEDO TEXTURE for an editable 3D aquarium hall, seen perpendicular to its surface. '
       'All four edges must tile continuously. Flat neutral diffuse illumination, no perspective, no ambient occlusion, '
       'no cast shadows, no bevelled 3D preview, no sphere, no borders, no background, no labels or lettering. '
       'The input fish controls pixel illustration finish only; do not copy the fish, its silhouette or scales.')

SPECS={
 'hall_floor': 'A clean public aquarium floor made of FOUR broad square worn stone tiles, arranged exactly 2x2. Muted slate gray with a restrained blue-green cast, thin dark gray grout, small stepped pixel edge chips and a few coherent mineral patches within each slab. Quiet broad material planes with sparse wear, no busy gravel, speckling, checkerboard colors, ornate motifs or dirty ruins. The complete repeat covers 2 by 2 meters; grout continues across all edges. Keep contrast moderate so the exhibited fish and ornaments remain the focus.',
 'hall_wall': 'Painted pale limestone-gray mineral plaster for a welcoming aquarium interior. An uninterrupted wall finish, NOT bricks, blocks or floor tiles. Readable small groups of square brush marks, broad subtle cool gray paint variations, occasional restrained pixel scratches. Mid-light neutral albedo so engine tint can produce cream or teal walls. No strong directional lighting, bold cracks, mold, high-contrast camouflage or isolated single-pixel noise. Complete repeat covers 2 by 2 meters.',
 'hall_wood': 'Dry maintained medium oak timber for a public aquarium viewing bench. Four continuous straight parallel planks run HORIZONTALLY along image X, with narrow dark plank joints; distinctive stepped pixel wood grain, occasional small knots and restrained warm gray-gold worn edges. Match the detailed painted timber finish of our aquarium ornaments, but this is cared-for indoor furniture, not rotten wreckage. No water, seaweed, nails, metal bands or silhouette. Keep wood brown rather than saturated orange. Seamless repeat covers 2 by 2 meters.'
}

def main():
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--plans',action='store_true');a=p.parse_args();root=a.root.resolve();folder=root/'projects/aquarium-hall-materials-v3'
 if a.plans:
  plans(root,folder)
  for name in SPECS:
   path=folder/f'plans/{name}.json';data=json.loads(path.read_text(encoding='utf-8'));data['plan']['validation']['min_color_variance']=8.0;data['plan']['negative_hints']=['No perspective render or material preview board.','No photograph, smooth gradients, fish, random stipple noise or text.'];path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
  return
 reference=root/'projects/fishing-2d/experiments/blender-fish/hammer-pair-121/accepted/great_hammerhead/inputs/style-reference.png'
 rows=[asset(name,desc+'\n'+STYLE,(1024,1024)) for name,desc in SPECS.items()]
 save_brief(folder,rows,reference)
 path=folder/'brief.draft.json';data=json.loads(path.read_text(encoding='utf-8'));data['project'].update(title='Aquarium hall generated pixel materials v3',description='Replace smooth placeholder hall surfaces with three generated pixel-art material sources. Preserve editable parcels, tanks, partitions, collision, saves and all existing tank artwork.',art_direction=STYLE,gameplay_loop='Expand standardized indoor parcels and place tanks and partitions in a hall with the same pixel illustration finish as its exhibits.',session_goal='Inspect generated floor, wall and bench timber artwork, then compare in actual Godot hall and close first-person views.')
 path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
 inputs=folder/'inputs';inputs.mkdir(exist_ok=True);shutil.copyfile(reference,inputs/'accepted-fish-style.png')

if __name__=='__main__':main()
