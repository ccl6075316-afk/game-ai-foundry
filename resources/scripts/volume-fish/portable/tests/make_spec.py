"""Create hash-bound recipe for a locally generated synthetic fixture."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fish_asset_spec import ROOT,sha,inspect_reference
p=argparse.ArgumentParser();p.add_argument('--fixture',type=Path,required=True);a=p.parse_args();d=a.fixture.resolve();packed=d/'packed';report=json.loads((packed/'packing.validation.json').read_text())
refs={k:{'path':str(v.relative_to(ROOT)),'sha256':sha(v)} for k,v in {'source_blend':d/'source.blend','reference_glb':packed/'merged-mask.glb','atlas':packed/'atlas.png','packing_report':packed/'packing.validation.json'}.items()}
spec={'kind':'fish_asset_finalization_spec','version':1,'inputs':refs,'source_mesh_name':'Piece0','expected':{**inspect_reference(packed/'merged-mask.glb'),'source_mesh_objects':len(report['parts'])},'parts':[{'name':row['node']+'_surface_'+str(row['surface']),'role':'body' if i==0 else 'aux' if i%2 else 'fin','logical_name':'body'if i==0 else row['node'],'source_node':row['node'],'source_surface':row['surface']}for i,row in enumerate(report['parts'])]}
(d/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
