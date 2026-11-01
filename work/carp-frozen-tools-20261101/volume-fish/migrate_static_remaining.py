"""Bounded, parameter-driven replay of proven local static-merge stages."""
import argparse,hashlib,json,os,re,shutil,signal,subprocess,threading
from pathlib import Path
FOUNDRY=Path(__file__).resolve().parents[3]
GAME_ROOT=FOUNDRY/'projects/fishing-2d';GAME=GAME_ROOT/'game'
BLENDER=Path('/Users/czl/.gamefactory/toolchain/blender/Blender.app/Contents/MacOS/Blender')
GODOT=Path('/Users/czl/.gamefactory/toolchain/godot/Godot_mono.app/Contents/MacOS/Godot')
PARAMS={'peacock_bass':(177,'PeacockBass','8316f225d9b28588acb716c590882827d169a1619ac5738d79dcbd7a8f560fee'),'nile_tilapia':(178,'NileTilapia','485ecf91d51cc2f9aa303289e674a3807de0051abad68221202551fd2d91879d'),'atlantic_sailfish':(179,'AtlanticSailfish','8b857c3800403d122bdcadbc825e093945eabdc5ddd7125d9c69361abcefb4b8'),'pacific_bluefin_tuna':(180,'PacificBluefinTuna','c3d14b9a77c4a6b199053ba53dcda2e0fa9029fc7a345d157a9a1215550926ef')}
TEMPLATE=GAME_ROOT/'experiments/grass-carp-static-merge/repro'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n')
def run(cmd,b,name,timeout=90):
 env=os.environ.copy();env['PATH']='/Users/czl/.gamefactory/toolchain/dotnet:'+env.get('PATH','')
 p=subprocess.Popen(list(map(str,cmd)),cwd=b,env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,start_new_session=True)
 def stop():
  try:os.killpg(p.pid,signal.SIGKILL)
  except ProcessLookupError:pass
 timer=threading.Timer(timeout,stop);timer.start();lines=[]
 with (b/(name+'.log')).open('w') as out:
  for line in p.stdout:
   out.write(line);out.flush();lines.append(line)
   if 'SCRIPT ERROR' in line or 'Traceback (most recent call last)' in line:stop()
 p.wait();timer.cancel()
 errors=[x for x in lines if 'ERROR:' in x or 'SCRIPT ERROR' in x]
 if p.returncode or errors:raise RuntimeError(f'{name}: exit={p.returncode}: '+''.join(lines[-10:]))
 return ''.join(lines)
def godot(script,b,name,project=GAME,args=None,graphics=False):
 return run([GODOT,*([] if graphics else ['--headless']),'--path',project,'--log-file',b/(name+'-engine.log'),'--script',script,'--',*(args if args is not None else [str(b)])],b,name)
def ctx(sp):
 ident,camel,old=PARAMS[sp];b=GAME_ROOT/'experiments'/(sp.replace('_','-')+'-static-merge');b.mkdir(exist_ok=True);(b/'repro').mkdir(exist_ok=True)
 return b,ident,camel,old
def transform(text,sp):
 b,ident,camel,old=ctx(sp)
 for a,z in [('grass_carp',sp),('grass-carp',sp.replace('_','-')),('GRASS_CARP',sp.upper()),('GrassCarp175',camel+str(ident)),('final175','final'+str(ident)),('final_asset175','final_asset'+str(ident)),('candidate-175','candidate-'+str(ident)),('-175.tres','-'+str(ident)+'.tres'),('c212875e6081cfaf68827da1546d81e2e1ad227271ea7b4744ae2fe981dd80d9',old)]:text=text.replace(a,z)
 return text
def emit(name,sp,source=None):
 b,*_=ctx(sp);p=b/'repro'/name;s=transform((source or TEMPLATE/name).read_text(),sp);p.write_text(s);return p

def capture(sp):
 b,ident,camel,old=ctx(sp);installed=GAME/'assets/models/fish'/(sp+'.glb');assert sha(installed)==old,'Installed input changed'
 for a,z in [(installed,b/'original-installed.glb'),(Path(str(installed)+'.import'),b/'original-installed.glb.import')]:
  if not z.exists():shutil.copy2(a,z)
  assert a.read_bytes()==z.read_bytes()
 if not (b/'old-actual-freeze.validation.json').exists():godot(emit('freeze_old_actual.gd',sp),b,'freeze')
 d=json.loads((b/'old-actual-freeze.validation.json').read_text());assert d['ok'] and d['old_glb_sha256']==old
 if not (b/'old-normalization-bounds.validation.json').exists():godot(emit('capture_old_bounds.gd',sp),b,'bounds')
 script=emit('freeze_current_materials.gd',sp)
 if not (GAME/f'assets/models/fish/motion/final{ident}/{sp}/materials.json').exists():godot(script,b,'materials',args=[])
 exported=emit('export_old_actual.gd',sp);s=exported.read_text();s=re.sub(r'\tassert\(int\(changed.get\("eye_relief112".*\n','',s)
 s=s.replace('node.queue_free()', 'node.get_parent().remove_child(node)\n\t\t\tnode.free()')
 s=s.replace('assert(visible.size() == 10)',f'assert(visible.size() == {len(d["after"])})');exported.write_text(s)
 godot(exported,b,'assembly-export')
 save(b/'migration-parameters.validation.json',{'kind':'frozen_static_merge_parameters','species':sp,'id':ident,'camel':camel,'old_sha':old,'mesh_count':len(d['after']),'mesh_surfaces':{k:len(v['surfaces']) for k,v in d['after'].items()},'bones':d['skeleton_bones'],'tracks':d['animation_tracks'],'formal_acceptance':False})
 print(json.dumps({'species':sp,'capture':True,'meshes':len(d['after']),'bones':d['skeleton_bones'],'tracks':d['animation_tracks']}),flush=True)

def compare(sp):
 b,ident,camel,old=ctx(sp)
 template=GAME_ROOT/'experiments/arapaima-static-merge/repro/compare_geometry.py'
 text=template.read_text().replace('arapaima',sp).replace('ARAPAIMA',sp.upper())
 text=re.sub(r'OLD_SHA = "[a-f0-9]+"', 'OLD_SHA = json.loads((BASE / "old-assembly-export.validation.json").read_text())["assembly_sha256"]',text)
 text=re.sub(r'NEW_SHA = "[a-f0-9]+"', 'NEW_SHA = json.loads((BASE / "blender-export.validation.json").read_text())["candidate_glb_sha256"]',text)
 text=text.replace('if is_icosphere_helper() == {obj.name}:','if obj.name in snapshot.helpers:')
 script=b/'repro/compare_geometry.py';script.write_text(text)
 try:run([BLENDER,'-b','--factory-startup','--python',script],b,'geometry-compare',180)
 except RuntimeError:
  if not (b/'geometry-compare.validation.json').exists():raise
 d=json.loads((b/'geometry-compare.validation.json').read_text());return d

def source(sp):
 b,ident,camel,old=ctx(sp);params=json.loads((b/'migration-parameters.validation.json').read_text())
 assert sha(GAME/'assets/models/fish'/(sp+'.glb'))==old
 script=emit('save_editable_and_export.py',sp)
 text=script.read_text().replace('assert all(obj.parent == rigs[0] for obj in bpy.data.objects if obj.type == "MESH")','# Mesh parent/world transforms and skin are compared, including rigid eye nodes.')
 script.write_text(text)
 run([BLENDER,'-b','--factory-startup','--python',script],b,'blender-source',180)
 d=compare(sp)
 if not d['ok']:
  assert all('raw GLB normal' in x for x in d['problems']),d['problems']
  shutil.copy2(b/'geometry-compare.validation.json',b/'geometry-before-normal-preservation.validation.json')
  module=(GAME_ROOT/'experiments/rainbow-trout-static-merge/repro/preserve_normals.py').read_text()
  module='"""Guarded raw-normal preservation, reused from the verified arapaima/rainbow method."""\n'+module[module.index('from __future__'):]
  module=module.replace('rainbow_trout',sp).replace('RAINBOW_TROUT',sp.upper());(b/'repro/preserve_normals.py').write_text(module)
  export_line=next(line for line in text.splitlines() if line.startswith('bpy.ops.export_scene.gltf('))
  replacement='import sys\nsys.path.insert(0, str(BASE / "repro"))\nfrom preserve_normals import preserve\nRAW = BASE / "raw-export.glb"\n'+export_line.replace('filepath=str(OUTPUT)','filepath=str(RAW)')+'\nnormal_report = preserve(OLD, RAW, OUTPUT, BASE / "normal-preservation.validation.json", expected_old_sha=inventory["assembly_sha256"])\nassert normal_report["ok"] and normal_report["bin_bytes_changed_outside_normal_accessors"] == 0'
  text=text.replace(export_line,replacement);script.write_text(text)
  # Reuse the already-saved source, rather than changing geometry to fix normals.
  script.write_text(text)
  run([BLENDER,'-b','--factory-startup','--python',script],b,'blender-normal-preservation',180)
  params['normal_preservation_required']=True
  d=compare(sp)
 assert d['ok'],d.get('problems')
 verify=emit('verify_reopened_source.py',sp);v=verify.read_text()
 line=next(line for line in v.splitlines() if line.startswith('bpy.ops.export_scene.gltf('))
 # Re-export into the same candidate path, with the same optional guarded step.
 if params.get('normal_preservation_required'):
  replacement='import sys\nsys.path.insert(0, str(BASE / "repro"))\nfrom preserve_normals import preserve\nRAW = BASE / "raw-reopened.glb"\n'+line.replace('filepath=str(OUTPUT)','filepath=str(RAW)')+'\nnormal_report = preserve(BASE / "assembled-old.glb", RAW, OUTPUT, BASE / "normal-preservation-reopened.validation.json", expected_old_sha=json.loads((BASE / "old-assembly-export.validation.json").read_text())["assembly_sha256"])\nassert normal_report["ok"]\nRAW.unlink()'
  v=v.replace(line,replacement)
 verify.write_text(v)
 run([BLENDER,'-b',b/(sp+'-static.blend'),'--python',verify],b,'source-reopen',180)
 params['candidate_sha']=sha(b/(sp+'-static.glb'));save(b/'migration-parameters.validation.json',params)
 print(json.dumps({'species':sp,'source':True,'normal_preserved':params.get('normal_preservation_required',False),'candidate_sha':params['candidate_sha'],'geometry':d['summary']}),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('stage',choices=['capture','source','engine','material','old_visual','install','new_check','main_arrays']);p.add_argument('species',nargs='+',choices=list(PARAMS));a=p.parse_args()
 if a.stage in ['engine','material']:
  from static_merge_engine import engine,material
  for sp in a.species:({'engine':engine,'material':material}[a.stage])(sp)
 elif a.stage in ['old_visual','install','new_check','main_arrays']:
  from static_merge_install import old_visual,install,new_check,main_arrays
  for sp in a.species:({'old_visual':old_visual,'install':install,'new_check':new_check,'main_arrays':main_arrays}[a.stage])(sp)
 else:
  for sp in a.species:globals()[a.stage](sp)
if __name__=='__main__':main()
