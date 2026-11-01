import argparse,json,hashlib
from pathlib import Path
import numpy as np
from validate_mouth_body139 import binding_matches
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--plan',type=Path,required=True);p.add_argument('--runtime',type=Path,required=True);p.add_argument('--game',type=Path,required=True);a=p.parse_args();plan=json.loads(a.plan.read_text());report=json.loads(a.runtime.read_text());items={x['species']:x for x in plan['items']};rows=[]
 assert report['ok'] and report['config_sha256']==sha(a.game/'assets/models/fish/motion/mouth-repair139.json')
 assert {x['species'] for x in report['rows']}=={'bluegill','zander','grass_carp','nile_tilapia','peacock_bass'}
 for row in report['rows']:
  s=row['species'];assert row['same_original_skin_and_skeleton'] and sha(row['path'])==row['sha256'];active=json.loads(Path(row['path']).read_text());item=items[s];cfg=item['candidate_lips'];assert sha(cfg['path'])==cfg['sha256'];expected=json.loads(Path(cfg['path']).read_text())['parts'];names=json.loads(Path(item['skinning_report']['path']).read_text())['summary']['skin_joint_names'];binding_matches(active,expected,names)
  for aa,bb in zip(active['parts'],expected):
   for key in ['uv','uv2']:
    if key in bb:assert np.array_equal(np.asarray(aa[key],'f4'),np.asarray(bb[key],'f4')),(s,key)
  rows.append({'species':s,'ok':True,'vertices':sum(len(x['vertices']) for x in expected),'resource_sha256':item['profile']['lips']['sha256'],'exact_geometry_uv_bones_and_packed_weights':True})
 result={'ok':True,'records':rows,'candidate_plan_sha256':sha(a.plan),'runtime_sha256':sha(a.runtime),'scope':'Actual final lip arrays, native UV and exact original-rig UNORM16 binding; no substitute for visual/source/contact/body/fin gates.'};(a.runtime.parent/'completion.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps({'ok':True,'fish':len(rows)}))
if __name__=='__main__':main()
