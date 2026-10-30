"""Source-owned export using frozen guards and the portable output whitelist.

Only the artifact path predicate is adapted. Geometry, UV, normal, ownership,
atlas and material signatures are checked by the unchanged frozen exporter.
"""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fish_asset_spec import allowed_output,fresh_outputs,sha


def export_source(output):
    import export_packed_fish_source as frozen
    previous=frozen.allowed_artifact
    try:
        frozen.allowed_artifact=allowed_output
        proof=frozen.export_packed_source(output)
        proof['portable_path_adapter_sha256']=sha(__file__)
        return proof
    finally:
        frozen.allowed_artifact=previous


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('blend','output','report'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--json',action='store_true');args=p.parse_args(sys.argv[sys.argv.index('--')+1:]if '--'in sys.argv else sys.argv[1:])
    source=args.blend.resolve();output,report=fresh_outputs([args.output,args.report],[source]);assert source.is_file()and source.suffix=='.blend'and output.suffix=='.glb'and report.suffix=='.json'
    import bpy
    before=sha(source);bpy.ops.wm.open_mainfile(filepath=str(source));proof=export_source(output);assert sha(source)==before;proof['blend_sha256']=before;report.write_text(json.dumps(proof,indent=2)+'\n');print(json.dumps({'ok':True,'model_sha256':proof['output_sha256'],'blend_sha256':before,'parts':len(proof['parts'])}))

if __name__=='__main__':main()
