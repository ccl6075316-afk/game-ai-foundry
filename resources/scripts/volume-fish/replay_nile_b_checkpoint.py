"""Verify retained Nile inputs; optionally rebuild B in a fresh isolated workspace.

This never installs a fish, edits current candidates, or confers visual approval.
"""
from pathlib import Path
import argparse,hashlib,json,sys,subprocess,shutil,time
repo=Path(__file__).resolve().parents[3]
trial=Path('projects/fishing-2d/experiments/nile-dorsal-route-trial')
checkpoint=repo/trial/'continuation-20261030.assets-manifest.json'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--execute',action='store_true');p.add_argument('--output',type=Path);p.add_argument('--blender',type=Path);p.add_argument('--json',action='store_true');a=p.parse_args()
 m=read(checkpoint);bad=[];line_only=[]
 for r in m['files']:
  f=repo/r['path']
  if not f.is_file():bad.append({'path':r['path'],'reason':'missing; fetch retained Git/LFS asset, do not invent donor'});continue
  if sha(f)!=r['sha256']:
   if r.get('lf_sha256')==hashlib.sha256(f.read_bytes().replace(b'\r\n',b'\n')).hexdigest():line_only.append(r['path'])
   else:bad.append({'path':r['path'],'reason':'content changed'})
 result={'ok':not bad,'kind':'nile_continuation_dependency_verification','files':len(m['files']),'line_endings_only':line_only,'failures':bad,'model_build_started':False,'formal_acceptance':False}
 if bad or not a.execute:print(json.dumps(result,ensure_ascii=False));return 1 if bad else 0
 assert a.output and a.blender and a.blender.is_file(),'Execute requires --output and an installed --blender'
 workspace=a.output.resolve();assert workspace.is_relative_to((repo/'work').resolve()) and workspace!=(repo/'work').resolve(),'Replay outputs must stay in a new subdirectory of repo/work'
 assert not workspace.exists(),'Use a new directory; never overwrite previous/current evidence'
 workspace.mkdir(parents=True);mirror=workspace/'repository';mirror.mkdir();started=time.perf_counter();commands=[]
 try:
  for r in m['files']:
   if not r.get('rebuild_seed'):continue
   target=mirror/r['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(repo/r['path'],target)
  def run(cmd,label):
   started_stage=time.perf_counter();log=workspace/(label+'.log');r=subprocess.run([str(x) for x in cmd],cwd=mirror,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=180)
   log.write_text(r.stdout+r.stderr,encoding='utf8');commands.append({'label':label,'argv':[str(x) for x in cmd],'exit_code':r.returncode,'seconds':time.perf_counter()-started_stage,'log':str(log.relative_to(repo)),'log_sha256':sha(log)})
   assert r.returncode==0 and 'Traceback (most recent call last)' not in r.stdout+r.stderr and 'SCRIPT ERROR' not in r.stdout+r.stderr,'Replay failed: '+label+'; inspect '+str(log)
  scripts=mirror/'resources/scripts/volume-fish';r4=mirror/trial/'round4-ab-textured';r6=mirror/trial/'round6-reference-repair';r7=mirror/trial/'round7-upper-lip-continuity'
  r6.mkdir(exist_ok=True);r7.mkdir(exist_ok=True)
  # Retain historical accepted source evidence, relocate only the archive map.
  archive=read(repo/trial/'round4-ab-textured/accepted-source-archive.json')
  old_root=Path(m['repo_at_capture'])
  def relocated(x):return str(repo/Path(x).relative_to(old_root))
  archive={k:{n:relocated(v) for n,v in x.items()} if k=='review_images' else relocated(x) for k,x in archive.items()}
  write(r4/'accepted-source-archive.json',archive)
  plan_code="import sys,json;from pathlib import Path;sys.path.insert(0,'cli');from volume_archive import snapshot;root=Path.cwd();p=root/'projects/fishing-2d/experiments/nile-dorsal-route-trial/round4-ab-textured';h=snapshot(p/'accepted-source-archive.json',root/'resources/volume-fish/nile-tilapia-reference-cage-163.profile.json',p/'B.json');(p/'B.json').write_text(json.dumps(h,ensure_ascii=False,indent=2)+'\\n',encoding='utf8')"
  run([sys.executable,'-c',plan_code],'00-source-archive')
  # Original Blender script spawns repo/.venv; point only this disposable copy
  # to the current interpreter. No geometry/texture algorithm is modified.
  builder=scripts/'build_nile_ab_textured.py';s=builder.read_text(encoding='utf8');needle="str(repo/'.venv/Scripts/python.exe')";assert s.count(needle)==1;s=s.replace(needle,repr(sys.executable));builder.write_text(s,encoding='utf8')
  relocation={'path':str(builder.relative_to(mirror)),'original_sha256':sha(repo/'resources/scripts/volume-fish/build_nile_ab_textured.py'),'staged_sha256':sha(builder),'only_change':'Replace hardcoded subprocess Python path with current host interpreter; original production script unchanged.'}
  run([a.blender,'--background','--python',builder,'--','--route','B'],'01-new-body-and-seven-fins')
  run([sys.executable,scripts/'prepare_nile_reference_repair.py'],'02-two-dimensional-skin-and-measured-jaws')
  run([a.blender,'--background','--python',scripts/'build_nile_reference_repair.py'],'03-integrated-measured-mouth')
  run([a.blender,'--background','--python',scripts/'mark_nile_upper_lip.py'],'04-actual-upper-lip-boundary')
  run([sys.executable,scripts/'paint_nile_upper_lip.py'],'05-upper-lip-outline-and-fill')
  run([a.blender,'--background','--python',scripts/'apply_nile_upper_lip.py'],'06-save-and-export')
  verify=workspace/'compare_exports.py';verify.write_text('''import bpy,json,sys,hashlib,struct\nfrom pathlib import Path\np=Path(sys.argv[sys.argv.index('--')+1]);reference=Path(sys.argv[sys.argv.index('--')+2]);output=Path(sys.argv[sys.argv.index('--')+3])\ndef state(file):\n bpy.ops.wm.open_mainfile(filepath=str(file));result={}\n for ob in bpy.context.scene.objects:\n  if ob.type!='MESH':continue\n  mesh=ob.data;uv=mesh.uv_layers.active\n  result[ob.name]={'vertices':len(mesh.vertices),'triangles':sum(len(f.vertices)-2 for f in mesh.polygons),'geometry_uv_weights':hashlib.sha256(repr(([tuple(v.co) for v in mesh.vertices],[tuple(f.vertices) for f in mesh.polygons],[[tuple(uv.data[li].uv) for li in f.loop_indices] for f in mesh.polygons],[[tuple((ob.vertex_groups[g.group].name,g.weight)) for g in v.groups] for v in mesh.vertices])).encode()).hexdigest(),'images':[[{'size':list(n.image.size),'pixels':hashlib.sha256(__import__('array').array('f',n.image.pixels[:]).tobytes()).hexdigest()} for n in mat.node_tree.nodes if n.type=='TEX_IMAGE'] for mat in mesh.materials]}\n return result\na=state(p);b=state(reference);checks={'whole_triangles':sum(r['triangles'] for r in a.values()),'parts':a,'same_parts':set(a)==set(b),'all_geometry_uv_weights_equal':all(a[k]['geometry_uv_weights']==b[k]['geometry_uv_weights'] for k in a if k in b),'all_material_image_pixels_equal':all(a[k]['images']==b[k]['images'] for k in a if k in b)}\nchecks['ok']=checks['whole_triangles']==1476 and checks['same_parts'] and checks['all_geometry_uv_weights_equal'] and checks['all_material_image_pixels_equal'];output.write_text(json.dumps(checks,indent=2)+'\\n',encoding='utf8');assert checks['ok'],checks\n''',encoding='utf8')
  compare=workspace/'rebuild-equivalence.validation.json'
  run([a.blender,'--background','--python',verify,'--',r7/'B-artifacts/fish.blend',repo/trial/'round7-upper-lip-continuity/B-artifacts/fish.blend',compare],'07-compare-frozen-checkpoint')
  evidence=read(compare);assert evidence['ok']
  result.update(ok=True,model_build_started=True,scope='Independent new B body and seven fins generated from frozen source inputs, then measured-mouth/skin/lip steps; current candidates untouched. Byte hashes may differ because paths/export metadata differ.',source_relocation=relocation,commands=commands,equivalence=evidence,seconds=time.perf_counter()-started,workspace=str(workspace.relative_to(repo)))
  write(workspace/'replay.validation.json',result)
 except Exception as exc:
  result.update(ok=False,model_build_started=True,error=str(exc),commands=commands,workspace=str(workspace.relative_to(repo)));write(workspace/'replay.validation.json',result);print(json.dumps(result,ensure_ascii=False));return 1
 print(json.dumps({'ok':True,'report':str((workspace/'replay.validation.json').relative_to(repo)),'triangles':evidence['whole_triangles'],'geometry_uv_weights_equal':evidence['all_geometry_uv_weights_equal'],'texture_pixels_equal':evidence['all_material_image_pixels_equal'],'seconds':result['seconds']},ensure_ascii=False));return 0
if __name__=='__main__':raise SystemExit(main())
