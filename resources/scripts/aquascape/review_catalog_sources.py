"""Apply explicit operator decisions through the official assets CLI."""
import argparse,json
from pathlib import Path
from catalog_workflows import call

p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--ids',nargs='+',required=True);a=p.parse_args()
for id in a.ids:
    project=a.root/f'projects/aquascape-{id}-views-v5'
    status=call(a.root,['workflow','status','--manifest',str(project/'pipeline/manifest.json'),'--json'])
    if status['status']!='done' or status['next_action']!='human_review':raise ValueError(status)
    assets=json.loads((project/'output/assets-manifest.json').read_text(encoding='utf-8'))['assets']
    for asset in assets:
        call(a.root,['assets','review','accept','--manifest',str(project/'output/assets-manifest.json'),'--asset',asset,'--json'])
    print(json.dumps({'project':project.name,'operator_source_review':'accepted_for_material_and_shape_trial','assets':list(assets),'user_acceptance':'pending'}))
