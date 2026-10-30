"""Investigation-only witnesses. Never modifies portable source or fish inputs."""
import contextlib
import copy
import io
import json
from pathlib import Path
import struct
import subprocess
import sys
from unittest.mock import patch
from PIL import Image,PngImagePlugin
ROOT=Path(__file__).resolve().parents[3]
PORTABLE=ROOT/'resources/scripts/volume-fish/portable'
sys.path.insert(0,str(PORTABLE));sys.path.insert(0,str(PORTABLE/'tests'))
from test_asset_core import fixture
import verify_parity as parity
from fish_asset_spec import load_spec,preflight,input_paths,sha,inspect_reference
from glb_io import read_glb,arrays
from pack_fish_material_atlas import write_glb
WORK=Path(__file__).resolve().parent
CASES=WORK/'cases';CASES.mkdir()
results=[]

def prepare(name):
    folder=CASES/name;folder.mkdir();specpath,candidate=fixture(folder)
    spec=load_spec(specpath);inputs=input_paths(spec)
    return folder,specpath,candidate,spec,inputs

def observe(call):
    try:
        result=call()
        return {'accepted':bool(result.get('ok',True)),'exception':None,'result':result}
    except Exception as error:
        return {'accepted':False,'exception':type(error).__name__,'message':str(error)}

def verify(spec,candidate,inputs):return parity.verify(inputs['reference_glb'],candidate,spec)

def change_weight(path,weights):
    doc,data=read_glb(path);data=bytearray(data);index=doc['meshes'][0]['primitives'][0]['attributes']['WEIGHTS_0'];access=doc['accessors'][index];view=doc['bufferViews'][access['bufferView']]
    for row in range(access['count']):struct.pack_into('<4f',data,view.get('byteOffset',0)+access.get('byteOffset',0)+row*view.get('byteStride',16),*weights)
    write_glb(path,doc,data)

def change_position(path,value):
    doc,data=read_glb(path);data=bytearray(data);access=doc['accessors'][doc['meshes'][0]['primitives'][0]['attributes']['POSITION']];view=doc['bufferViews'][access['bufferView']];struct.pack_into('<f',data,view.get('byteOffset',0)+access.get('byteOffset',0),value);write_glb(path,doc,data)

# 1: Same changed geometry rejected normally but accepted by optimized Python.
folder,specpath,candidate,spec,inputs=prepare('optimized')
change_position(candidate,.125)
normal=observe(lambda:verify(spec,candidate,inputs))
code="import json,sys;from pathlib import Path;sys.path.insert(0,sys.argv[1]);from verify_parity import verify;r=verify(sys.argv[2],sys.argv[3]);print(json.dumps({'ok':r['ok'],'position_error':r['attributes']['POSITION']['max_component_error']}))"
optimized=subprocess.run([sys.executable,'-O','-c',code,str(PORTABLE),str(inputs['reference_glb']),str(candidate)],capture_output=True,text=True,timeout=10)
results.append({'id':'1','case':'assert-stripping','normal':normal,'optimized':{'returncode':optimized.returncode,'stdout':optimized.stdout,'stderr':optimized.stderr},'confirmed':not normal['accepted'] and optimized.returncode==0 and json.loads(optimized.stdout)['ok']})

# 2: Definitions remain, primitive binding removed or points past material array.
for kind in ('missing','bad_index'):
    folder,specpath,candidate,spec,inputs=prepare('material_'+kind);doc,data=read_glb(candidate);primitive=doc['meshes'][0]['primitives'][0]
    if kind=='missing':primitive.pop('material')
    else:primitive['material']=999
    write_glb(candidate,doc,data);observed=observe(lambda:verify(spec,candidate,inputs))
    results.append({'id':'2','case':'primitive_material_'+kind,'observed':observed,'confirmed':observed['accepted']})

# 3a: An otherwise unused negative slot is ignored while positive mass remains1.
folder,specpath,candidate,spec,inputs=prepare('negative_weights');change_weight(candidate,[1,-.5,0,0]);observed=observe(lambda:verify(spec,candidate,inputs))
results.append({'id':'3','case':'negative_weight_unused_slot','weights':[1,-.5,0,0],'observed':observed,'candidate_inspection':observe(lambda:inspect_reference(candidate)),'confirmed':observed['accepted']})
# 3b: Positive unnormalized changes are caught as differences, source validity is not.
folder,specpath,candidate,spec,inputs=prepare('unnormalized_weights');change_weight(candidate,[.5,0,0,0]);changed=observe(lambda:verify(spec,candidate,inputs));change_weight(inputs['reference_glb'],[.5,0,0,0]);same=observe(lambda:verify(spec,candidate,inputs))
results.append({'id':'3','case':'unnormalized_positive_weights','candidate_only':changed,'both_invalid_same':same,'reference_inspection':observe(lambda:inspect_reference(inputs['reference_glb'])),'confirmed':not changed['accepted'] and same['accepted']})
# 3c: A 5e-8 slot is below existing1e-6 semantic tolerance; acceptance alone is not a defect.
folder,specpath,candidate,spec,inputs=prepare('small_weight_tolerance');change_weight(candidate,[1,5e-8,0,0]);observed=observe(lambda:verify(spec,candidate,inputs));results.append({'id':'3','case':'small_weight_inside_tolerance','observed':observed,'disposition':'expected acceptance inside declared1e-6 tolerance'})

# 4: Distinct PNG payload preserving decoded RGBA is accepted and explicitly recorded.
folder,specpath,candidate,spec,inputs=prepare('png_reencoding');doc,data=read_glb(candidate);view=doc['bufferViews'][doc['images'][0]['bufferView']];payload=data[view.get('byteOffset',0):view.get('byteOffset',0)+view['byteLength']];image=Image.open(io.BytesIO(payload));encoded=io.BytesIO();meta=PngImagePlugin.PngInfo();meta.add_text('synthetic-investigation','same RGBA, different container');image.save(encoded,format='PNG',pnginfo=meta);new=encoded.getvalue();buffer=bytearray(data);buffer.extend(b'\0'*(-len(buffer)%4));view['byteOffset']=len(buffer);view['byteLength']=len(new);buffer.extend(new);write_glb(candidate,doc,buffer);observed=observe(lambda:verify(spec,candidate,inputs));results.append({'id':'4','case':'different_PNG_same_RGBA','observed':observed,'disposition':'intentional semantic RGBA parity; report distinguishes PNG byte hashes, no false byte identity claim'})

# 5a: Swap candidate bytes after parse; report hashes unverified replacement bytes.
folder,specpath,candidate,spec,inputs=prepare('candidate_toctou');before=sha(candidate);original_read=parity.read_glb;parsed_hash=None

def raced_read(path):
    result=original_read(path)
    if Path(path).resolve()==candidate.resolve():change_position(candidate,.25)
    return result
with patch.object(parity,'read_glb',side_effect=raced_read):observed=observe(lambda:verify(spec,candidate,inputs))
results.append({'id':'5','case':'candidate_mutation_after_read','candidate_before_sha256':before,'candidate_after_sha256':sha(candidate),'observed':observed,'confirmed':observed['accepted'] and observed['result']['candidate']['sha256']==sha(candidate) and before!=sha(candidate),'detail':'Verifier consumed POSITION0 but report binds replaced candidate POSITION.25 with0 measured component error.'})
# 5b: CLI uses parsed oldspec but signs late new(spec) with impossible expectedcount.
folder,specpath,candidate,spec,inputs=prepare('spec_toctou');before=sha(specpath);real_verify=parity.verify;output=folder/'raced-proof.validation.json'
def raced_verify(*args,**kwargs):
    result=real_verify(*args,**kwargs);changed=copy.deepcopy(spec);changed['expected']['triangles']=999;specpath.write_text(json.dumps(changed));return result
stdout=io.StringIO()
with patch.object(parity,'verify',side_effect=raced_verify),patch.object(sys,'argv',['verify_parity.py','--spec',str(specpath),'--candidate',str(candidate),'--output',str(output),'--json']),contextlib.redirect_stdout(stdout):
    observed=observe(lambda:(parity.main() or {'ok':True}))
proof=json.loads(output.read_text())if output.exists()else{}
results.append({'id':'5','case':'spec_mutation_before_late_report_hash','spec_before_sha256':before,'spec_after_sha256':sha(specpath),'observed':observed,'reported_spec_sha256':proof.get('spec_sha256'),'reported_inventory':proof.get('derived_reference_inventory'),'subsequent_preflight':observe(lambda:preflight(specpath)),'confirmed':observed['accepted'] and proof.get('spec_sha256')==sha(specpath)and before!=sha(specpath),'stdout':stdout.getvalue()})

# 6: Static source-authoring proof explicitly defers fresh parity/final gates. Show mandatory runner gate.
results.append({'id':'6','case':'wrong_rest_source_build','reproduced':False,'disposition':'No Blender run per task. Source authoring preserves its existing rig but does not prove rest equivalence; run_source mandatory cold parity rejects changed node rest/IBMs before final spec/manifestdone. Existing unit rest mutation negative and full source smoke cover gate; not a standalone build acceptance claim.','confidence':'Medium (static source trace, bounded by no Blender witness)'})
# 7: Emptyexpected still derives measured hashbound inventory and rejects mismatching candidate.
folder,specpath,candidate,spec,inputs=prepare('empty_expected');spec['expected']={};specpath.write_text(json.dumps(spec));baseline=observe(lambda:preflight(specpath));change_position(candidate,.125);mismatch=observe(lambda:verify(spec,candidate,inputs));results.append({'id':'7','case':'empty_expected','preflight':baseline,'mismatching_candidate':mismatch,'disposition':'Counts are measured from exact hashbound baseline, not bypassed; expected keys are optional extra assertions. No observed parity weakening.'})

# Keep concise technical evidence; strip full parity payloads, retain decisive fields.
for result in results:
    for key,value in list(result.items()):
        if isinstance(value,dict)and isinstance(value.get('result'),dict):
            full=value['result']
            value['result']={k:full[k]for k in ('ok','candidate','PNG_bytes_equal','atlas_RGBA_exact','attributes','triangles','bones','summary')if k in full}
report={'kind':'anvil_debug_investigation_phase1','ok':True,'mode':'Normal','initial_mode':'Degraded Medium until first runtime witness','source_files_unchanged':True,'source_hashes':{str((PORTABLE/name).relative_to(ROOT)):sha(PORTABLE/name)for name in ('fish_asset_spec.py','build_source.py','source_snapshot.py','verify_parity.py','glb_io.py')},'results':results,'scope':'Investigation only; no production source changes, no Blender/GPU/real fish.','proposed_fixes':'Pending phase1 adversarial review before pattern/hypothesis gate.'}
(WORK/'phase1.validation.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps({'ok':True,'report':str(WORK/'phase1.validation.json'),'cases':len(results),'confirmed':[r['case']for r in results if r.get('confirmed')]}))
