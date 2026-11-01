"""Repeatable small Blender smoke: two inventories, source save and cold export.

Only synthetic inputs are created. Output directory must be fresh under the
portable work root. No model service, real fish, GPU or production gate is run.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fish_asset_spec import ROOT,fresh_outputs,sha,preflight,input_paths,load_spec
from verify_parity import verify

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--blender',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--json',action='store_true');a=p.parse_args();a.output=a.output.resolve();fresh_outputs([a.output],[]);a.output.mkdir(parents=True)
    scripts=Path(__file__).resolve().parents[1];tests=scripts/'tests';frozen=scripts.parent;items=[]
    def run(args):
        result=subprocess.run([str(x)for x in args],cwd=ROOT,capture_output=True,text=True)
        if result.returncode or 'Traceback (most recent call last)'in result.stdout+result.stderr:
            raise RuntimeError('Synthetic command failed: '+str(args)+'\n'+result.stdout+'\n'+result.stderr)
    def blender(script,args):run([a.blender,'--background','--python-exit-code','1','--python',script,'--',*args])
    for label,bones,parts,clips in [('a',3,3,2),('b',2,2,1)]:
        folder=a.output/label
        blender(tests/'make_synthetic.py',['--output',folder,'--bones',str(bones),'--parts',str(parts),'--clips',str(clips)])
        run([sys.executable,frozen/'pack_fish_material_atlas.py','--model',folder/'unpacked.glb','--output',folder/'packed'])
        run([sys.executable,tests/'make_spec.py','--fixture',folder]);specpath=folder/'spec.json';spec=load_spec(specpath);inputs=input_paths(spec);before={key:sha(path)for key,path in inputs.items()}
        baseline=preflight(specpath)
        run([sys.executable,scripts/'run_source.py','--spec',specpath,'--blender',a.blender,'--output',folder/'run','--execute','--json'])
        blender(tests/'verify_saved_source.py',['--original',folder/'source.blend','--authored',folder/'run/source/fish.blend','--output',folder/'saved-source.validation.json'])
        proof=json.loads((folder/'run/validation-report.json').read_text())
        assert before=={key:sha(path)for key,path in inputs.items()}
        assert sha(folder/'run/fish.glb')==sha(folder/'run/source/fish.glb')
        items.append({'fixture':label,'inventory':baseline['summary']['inventory'],'parts':len(spec['parts']),'cold_export_bytes_equal':True,'original_inputs_unchanged':True,'saved_rig_rest_pose_actions_NLA_equal':True,'proof':str((folder/'run/validation-report.json').relative_to(ROOT))})
    result={'ok':True,'kind':'portable_synthetic_blender_source_and_cold_export_smoke','helpers':{str(path.relative_to(ROOT)):sha(path)for path in [scripts/'build_source.py',scripts/'verify_parity.py',scripts/'fish_asset_spec.py',scripts/'source_snapshot.py',scripts/'glb_io.py',scripts/'run_source.py',scripts/'export_source.py',frozen/'export_packed_fish_source.py']},'fixtures':items,'scope':'Synthetic tool tests only; no fish acceptance or production gates.'};report=a.output/'validation-report.json';report.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'ok':True,'report':str(report.resolve()),'fixtures':items}))
if __name__=='__main__':main()
