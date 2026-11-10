from pathlib import Path
import json,sys,hashlib,argparse
E=Path(__file__).resolve().parent;R=E.parents[1];sys.path.insert(0,str(R/'resources/scripts/volume-fish/portable'))
from parts import freeze
p=argparse.ArgumentParser();p.add_argument('stage');a=p.parse_args();folder=E/a.stage;model=folder/'fish.glb';spec=json.loads((E/'parts-spec.json').read_text(encoding='utf8'));manifest=freeze(model,spec);mp=folder/'parts-manifest.json';mp.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf8');plan=json.loads((E/'baseline.plan.json').read_text(encoding='utf8'));plan.update(model=str(model),model_sha256=hashlib.file_digest(model.open('rb'),'sha256').hexdigest(),packed_parts_manifest=str(mp),packed_parts_manifest_sha256=hashlib.file_digest(mp.open('rb'),'sha256').hexdigest());(folder/'review.plan.json').write_text(json.dumps(plan,indent=2),encoding='utf8');print(plan['model_sha256'])
