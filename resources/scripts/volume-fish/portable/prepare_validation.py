"""Prepare portable import diagnostics while retaining explicit unsupported gates."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from parts import freeze, fresh_output, read, sha
from fish_asset_spec import load_spec, input_paths, preflight

LIMITATIONS = {
    'actual_import_partition': {'supported':True,'runner':'validate_import.gd'},
    'opaque_body_uv_rectangles': {'supported':True,'runner':'parts.py'},
    'full490_physical': {'supported':False,'reason':'Frozen production exporters remain species/part-specific; a reviewed anatomy adapter and per-species constraints are required.'},
    'fin_root_signed_distance': {'supported':False,'reason':'No arbitrary-anatomy root/pose adapter implemented; old reports are not transferred.'},
    'fin_membrane_clearance': {'supported':False,'reason':'No arbitrary-anatomy membrane/pose adapter implemented.'},
    'body_gpu_coverage_discrete': {'supported':True,'runner':'validate_body_gpu.py','scope':'Two distinct native poses, eight matching views each, zero missing body pixels plus transparent negative. Separate explicit GPU execution required.'},
    'body_integrity_full077': {'supported':False,'reason':'Discrete GPU alpha comparison does not establish closed body topology or all production integrity requirements.'},
    'head_form_and_visual_acceptance': {'supported':False,'reason':'Requires species sources, independent views and actual visual review.'},
}

def prepare(model, spec_path, output, references=()):
    model=Path(model).resolve(); spec_path=Path(spec_path).resolve(); output=fresh_output(output)
    references=[Path(path).resolve() for path in references]
    for path in references:
        if not path.is_file(): raise ValueError('Missing reference plan: '+str(path))
    spec=load_spec(spec_path); source_inputs=input_paths(spec); preflight(spec_path)
    manifest=freeze(model,spec)
    helper=Path(__file__).resolve().parent
    # Validate everything before creating a plan-set directory.
    dependencies={str(path):sha(path) for path in [model,spec_path,*source_inputs.values(),*references,helper/'parts.py',helper/'glb_io.py',helper/'fish_asset_spec.py',helper/'PackedFishParts.gd',helper/'validate_import.gd',helper/'capture_body_gpu.gd',helper/'validate_body_gpu.py',Path(__file__).resolve()]}
    output.mkdir(parents=True)
    manifest_path=output/'parts-manifest.json'
    manifest_path.write_text(json.dumps(manifest,ensure_ascii=False,separators=(',',':'))+'\n',encoding='utf8')
    dependencies[str(manifest_path)]=sha(manifest_path)
    plan={'ok':True,'schema_version':1,'kind':'fish_portable_validation_plan','model':str(model),'model_sha256':sha(model),'packed_parts_manifest':str(manifest_path),'packed_parts_manifest_sha256':sha(manifest_path),'spec':str(spec_path),'spec_sha256':sha(spec_path),'source_references':{str(p):sha(p) for p in [*source_inputs.values(),*references]},'source_dependencies':dependencies,'capabilities':LIMITATIONS,'formal_acceptance':False,'next_action':'human_review','scope':'Input preparation only. Arbitrary inventory is supported by new import diagnostics. Original full physical exporters are not generalized; no gate results or prior passes copied.'}
    plan_path=output/'plan-set.validation.json';plan_path.write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    return {'ok':True,'command':'portable.prepare_validation','status':'done','next_action':'none','outputs':[str(manifest_path),str(plan_path)],'summary':{'parts':len(manifest['parts']),'capabilities':LIMITATIONS,'formal_acceptance':False},'failures':[]}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--model',type=Path,required=True);p.add_argument('--spec',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--reference-plan',type=Path,action='append',default=[]);p.add_argument('--json',action='store_true');args=p.parse_args()
    try: result=prepare(args.model,args.spec,args.output,args.reference_plan)
    except (ValueError,AssertionError,KeyError,IndexError,TypeError,OSError) as error:
        result={'ok':False,'command':'portable.prepare_validation','status':'failed','next_action':'fix_input','outputs':[],'failures':[{'kind':'validation','code':'portable_validation_plan_invalid','message':str(error)[:1200]}]}
    print(json.dumps(result,ensure_ascii=False));return 0 if result['ok'] else 1
if __name__=='__main__':raise SystemExit(main())
