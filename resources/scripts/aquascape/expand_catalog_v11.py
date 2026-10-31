"""Additional species/props; source workflows remain the authority for artwork.

Prompts describe species and normal foliage, never prescribe leaf counts/angles.
"""
import argparse,json,sys
from pathlib import Path
from prepare_full_views_catalog import asset,save_brief,STYLE
from catalog_workflows import call

ROOT=Path(__file__).resolve().parents[3]
CFG=ROOT/'resources/aquascape/expansion-v11.json'
REVIEW=ROOT/'projects/fishing-2d/plans/reviews/aquascape-expansion-v11'

def save(p,d):
    p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2),encoding='utf-8')

def seed():
    plants=[
      ('bacopa_round','圆叶节节菜','Bacopa rotundifolia','Fresh green fleshy round to broadly oval paired leaves along upright branching stems. A natural loose stem clump.',.30,'stem'),
      ('dwarf_baby_tears','迷你矮珍珠','Hemianthus callitrichoides','A low creeping carpet patch of tiny rounded bright green leaves on fine branching runners, naturally uneven low cushion.',.065,'carpet'),
      ('ammannia_gracilis','红柳','Ammannia gracilis','A natural upright stem clump, narrow elongated copper-red to salmon leaves with green lower foliage. Open branching habit.',.38,'stem'),
      ('water_sprite','水蕨','Ceratopteris thalictroides','A rooted water sprite with delicate finely divided fresh green fronds and a soft airy fern outline. Ordinary submerged foliage.',.32,'fern'),
      ('java_moss','爪哇莫丝','Taxiphyllum barbieri','A natural loose low moss tuft with fine irregular branching green strands and minute moss foliage, an airy irregular cushion, no stone or wood.',.10,'moss'),
      ('cabomba','绿菊水草','Cabomba caroliniana','A natural clump of upright slender stems with distinctive bright green fan-shaped finely divided submerged foliage, delicate open fans.',.36,'stem'),
      ('hornwort','金鱼藻','Ceratophyllum demersum','A natural submerged stem bunch with dark green forked needle-like foliage in whorls, a bushy bottlebrush silhouette. Rootless stems gathered at the base, no invented root bundle.',.36,'stem'),
      ('hydrocotyle','三裂天胡荽','Hydrocotyle tripartita','A low spreading patch on creeping runners, fresh green small three-lobed clover-like leaves on slender petioles. Normal gently extended foliage.',.11,'carpet'),
      ('rotala','圆叶宫廷','Rotala rotundifolia','A natural slender stem clump with small narrow elongated submerged leaves, green lower growth transitioning to warm pink-orange shoot tips. Delicate branching silhouette.',.34,'stem'),
      ('ludwigia_rubin','红叶丁香','Ludwigia repens Rubin','A natural branching stem clump with broad oval pointed leaves, rich burgundy and ruby red upper foliage and olive green lower foliage. Ordinary flat leaves.',.28,'stem')]
    solids=[
      ('dragon_stone','黄龙石','rock','A single ochre-brown aquarium dragon stone, deeply eroded irregular grooves and pitted ridges, rugged upright asymmetric form, broad stable base.',.32),
      ('lava_rock','火山熔岩石','rock','A dark reddish black porous volcanic lava rock, rounded irregular squat form, rough large natural pores in painted texture.',.30),
      ('slate_stack','青灰叠层石','rock','A naturally fractured low broad slate outcrop, thin horizontal blue-grey sedimentary shelves stepping down asymmetrically, stable broad footprint, one coherent rock.',.38),
      ('quartz_rock','乳白石英岩','rock','A chunky milky white aquarium quartz rock with broad angular translucent-looking mineral faces and warm grey veins, irregular blunt facets, no long crystal spikes.',.28),
      ('spider_wood','蛛根沉木','wood','A pale tan aquarium spiderwood root, graceful arching fine branching root limbs connected to a compact central knot, natural blunt weathered tips, stable root feet.',.42),
      ('mopani_wood','双色莫帕尼木','wood','A dense gnarled low mopani driftwood, contrasting honey tan smooth worn face and very dark brown underside, compact twisting solid trunk with short stout root feet.',.37),
      ('mangrove_root','红树支根木','wood','A dark russet mangrove root with a raised central trunk supported by natural arching stilt roots, visible open spaces beneath roots, broad stable footprint, weathered blunt ends.',.40),
      ('bamboo_shelter','竹节躲避屋','decor','A short weathered hollow bamboo section lying horizontally, olive golden bamboo skin and a distinct raised bamboo node near the back, large open circular front entrance and visible dark inner wall, stable flat underside.',.25),
      ('slate_cave','石板躲避洞','decor','A small aquarium shelter assembled from flat dark grey slate, a low slab roof resting on natural stone side walls, clearly open broad low front entrance and deep inner chamber, no door.',.30),
      ('ruined_tower','残破城堡塔','decor','A small aquarium ornament of an old mossy grey stone castle tower, squat round masonry tower with a broken crenellated top, a large arched swim-through doorway at the base, restrained worn stone carving, no flags or scenery.',.25)]
    data={'schema_version':1,'plants':[dict(id=i,name_zh=n,scientific_name=sn,morphology=m,height_m=h,growth_form=g,category='plant',budget_type='broadleaf_plant') for i,n,sn,m,h,g in plants],
      'solids':[dict(id=i,name_zh=n,category=c,shape=s,width_m=w,budget_type=c) for i,n,c,s,w in solids],
      'plant_art_policy':'A natural clump of the species, ordinary gently extended foliage. No prescribed leaf count, arrangement, spread/bend angle, curled, hooked, flipped-up or unfolding showcase leaf.',
      'research':[
        {'url':'https://store.steampowered.com/app/4941890/Fish_Game__Plant_Variety_Pack_1/','evidence':'Official game list includes Bacopa rotundifolia, Hemianthus callitrichoides and Ammannia gracilis. Avoid duplicating existing sword/crypt/vallisneria forms.'},
        {'url':'https://store.steampowered.com/news/posts/?enddate=1785859255&feed=steam_community_announcements','evidence':'Fish Game developer announcement adds Ceratopteris thalictroides (Water Sprite).'},
        {'url':'https://tropica.com/en/plants/1-2-grow','evidence':'Aquarium producer lists Hydrocotyle tripartita and Taxiphyllum barbieri.'},
        {'url':'https://tropica.com/en/guide/get-the-right-start/supporting-plants','evidence':'Aquarium producer lists fan-stem Cabomba and Ceratophyllum demersum.'},
        {'url':'https://tropica.com/ProductMedia/Layouts/L010/702_UK.pdf','evidence':'Aquarium producer layout uses Ludwigia repens Rubin and Rotala rotundifolia.'}],
      'research_scope':'Game lists establish examples, not frequency statistics across all games. Additional species selected from real aquarium planting references for distinct silhouettes. No third-party game art is copied.',
      'user_acceptance':'pending'}
    if CFG.exists():raise RuntimeError('Expansion config already exists; do not overwrite')
    save(CFG,data)

def folder(kind):return ROOT/f'projects/aquascape-expansion-v11-{kind}'

def views_folder(s):return folder(s['id']+'-views'+s.get('views_revision',''))

def fronts(cfg):
    for kind in ['plants','solids']:
        rows=[]
        for s in cfg[kind]:
            desc=s.get('scientific_name','')+'. '+s.get('morphology',s.get('shape',''))
            policy=cfg['plant_art_policy'] if kind=='plants' else ''
            prompt=f'Create ONE definitive FRONT artwork of a new aquarium asset: {desc}\n{STYLE}\nCamera: orthographic front elevation, eye level, no isometric tilt. Complete object including base and extremities, clean margins. {policy}\nNo pot, substrate, floor, water, labels, extra objects or extra views. Reference is drawing finish only; create the specified new subject.'
            rows.append(asset(s['id']+'_front',prompt,(1024,1536) if kind=='plants' else (1536,1024)))
        save_brief(folder(kind),rows,ROOT/f'projects/aquascape-{kind}-20-v5/style-reference.png')

def auxiliary(cfg):
    for s in cfg['plants']+cfg['solids']:
        kind='plants' if s['category']=='plant' else 'solids';reference=folder(kind)/f'output/{s["id"]}_front_raw.png'
        if not reference.exists():raise RuntimeError('Front still pending: '+s['id'])
        desc=s.get('scientific_name','')+'. '+s.get('morphology',s.get('shape',''));rows=[]
        if kind=='plants':
            prompt=f'Illustrate separated normal foliage samples from this same {desc}. Match the supplied whole plant exactly in pixel drawing finish, colour, leaf shape and anatomy. {cfg["plant_art_policy"]}\nOn pure white, show complete ordinary leaves or complete representative foliage sprigs/fronds with their natural basal attachment, enough clean white space to isolate them. Preserve the species-specific fan divisions, fern divisions, needle whorls or moss sprigs where applicable. No whole plant, roots, text, grid or other objects. Native detailed pixel illustration, no photo or smooth CGI.'
            rows=[asset(s['id']+'_leaves',prompt,(1536,1024))]
        else:
            for view in ['right','top']:
                camera=('Camera exactly at the RIGHT END looking along -X. Orthographic perpendicular END ELEVATION. X length disappears into the screen; horizontal image dimension is Z depth and vertical is Y height. Long front limbs become foreshortened cross-sections. Do not repeat the long front facade. No camera tilt.' if view=='right' else 'Camera directly above at +Y, looking STRAIGHT VERTICALLY DOWN -Y. True ORTHOGRAPHIC TOP PLAN: X horizontal, Z depth vertical. Height Y disappears into the screen. Do not draw the object standing upright: no tall front facade, no front doorway facade. A vertical tower appears as its circular roof footprint with its broken upper rim; a vertical trunk becomes an end-grain cross-section surrounded by roots. A horizontal tube appears as its long roof and has no visible front circular interior. This is an overhead plan, not a 3/4 perspective illustration. No tilt.')
                rows.append(asset(s['id']+'_'+view,f'Render the EXACT SAME object from the supplied front artwork: {desc}\n{STYLE}\n{camera}\nKeep the same physical branches, holes, roof, openings and broken edges. Infer hidden surfaces consistently. One complete object with clean margins; no labels, diagrams or extra views.',(1536,1536)))
        save_brief(views_folder(s),rows,reference)

def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['seed','fronts','auxiliary']);a=p.parse_args()
    if a.mode=='seed':seed()
    elif a.mode=='fronts':fronts(json.loads(CFG.read_text(encoding='utf-8')))
    else:auxiliary(json.loads(CFG.read_text(encoding='utf-8')))
if __name__=='__main__':main()
