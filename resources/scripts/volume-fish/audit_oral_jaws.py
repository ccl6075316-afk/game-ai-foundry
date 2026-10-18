"""Read-only static oral-cleft rays. A painted mouth on a closed shell must fail."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy,bmesh
from mathutils import Vector
from mathutils.bvhtree import BVHTree
sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'cli'))
from volume_mouth import slit_v,validate_oral_context

parser=argparse.ArgumentParser()
parser.add_argument('--blend',required=True);parser.add_argument('--profile',required=True);parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
profile=json.loads(Path(args.profile).read_text(encoding='utf-8'));mouth=profile['oral_jaws']
if mouth.get('separate_lower'):parser.error('Separate lower jaw uses audit_separate_jaw.py; full-width empty-slit rays do not judge a covering lip')
validate_oral_context(mouth,profile['body'],profile['rig']['spine'])
bpy.ops.wm.open_mainfile(filepath=str(Path(args.blend).resolve()))
body=bpy.data.objects['Closed_body'];bm=bmesh.new();bm.from_mesh(body.data);tree=BVHTree.FromBMesh(bm);bm.free()
rows=[];failures=[]
samples=[.1,.3,.5,.7,.9]+([.95,.97] if mouth.get('slit_path') else [])
for t in samples:
    u=mouth['corner'][0]+t*(mouth['front'][0]-mouth['corner'][0])
    z=(.5-slit_v(mouth,u))/profile['source_aspect_ratio']
    hits={}
    for name,offset in [('cleft',0),('upper',mouth['gap']*2),('lower',-mouth['gap']*2)]:
        location,normal,index,distance=tree.ray_cast(Vector((u-.5,-1,z+offset)),Vector((0,1,0)),2)
        hits[name]=location is not None
    ok=not hits['cleft'] and hits['upper'] and hits['lower']
    rows.append({'t':t,'u':u,'ray_hits':hits,'ok':ok})
    if not ok:failures.append('Cleft must be open across width, with actual skin above/below at t='+str(t))
sha=lambda path:hashlib.sha256(Path(path).read_bytes()).hexdigest()
report={'ok':not failures,'scope':'Static raw mesh cross-mouth rays including terminal turn when curved; no articulation or anatomical width/occlusion acceptance.', 'blend_sha256':sha(args.blend),'profile_sha256':sha(args.profile),'samples':rows,'failures':failures}
Path(args.output).write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
if failures:sys.exit(1)
