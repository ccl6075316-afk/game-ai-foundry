"""Hash-gated installation and real-entry visual/cold replay for selected fish."""
from static_merge_engine import *

def visual(sp,mode):
 b,i,camel,old,d=params_for(sp);expected=old if mode=='old' else d['candidate_sha'];assert sha(GAME/'assets/models/fish'/(sp+'.glb'))==expected
 script=emit('capture_runtime_views.gd',sp);script.write_text(hashes(script.read_text(),d,b));out=b/('visual-'+mode);out.mkdir(exist_ok=True)
 if not (out/'motion-visual.validation.json').exists() or json.loads((out/'motion-visual.validation.json').read_text()).get('glb_sha256') != expected:
  godot(script,b,'visual-'+mode,args=[str(out),mode],graphics=True)
 report=json.loads((out/'motion-visual.validation.json').read_text());assert report['ok'] and report['glb_sha256']==expected
 print(json.dumps({'species':sp,'visual':mode,'images':len(report['images'])}),flush=True)
def old_visual(sp):visual(sp,'old')
def vec(values):return 'Vector3('+', '.join(map(str,values))+')'
def install(sp):
 b,i,camel,old,d=params_for(sp);assert json.loads((b/'local-cold-load.validation.json').read_text())['ok']
 prefix=Path(f'assets/models/fish/motion/final{i}/{sp}');project=b/'candidate-project';manifest_path=project/prefix/f'materials-candidate-{i}.json';manifest=json.loads(manifest_path.read_text());manifest_sha=sha(manifest_path)
 assert manifest['candidate_glb_sha256']==d['candidate_sha']
 freeze=json.loads((b/'old-actual-freeze.validation.json').read_text());fin_names=[n for n in freeze['after'] if re.match(r'^(Anal|Caudal|Dorsal|Pectoral|Pelvic|Adipose)',n)];fin_surfaces=sum(d['mesh_surfaces'][n] for n in fin_names)
 assert fin_surfaces==freeze['builder_receipt']['fin_surfaces'],(sp,fin_names,fin_surfaces)
 binder=transform((GAME/'scripts/aquarium/FinalizedGrassCarp175.gd').read_text(),sp);binder=hashes(binder,d,b)
 binder=re.sub(r'const MANIFEST_SHA := "[^"]+"','const MANIFEST_SHA := '+json.dumps(manifest_sha),binder)
 before=json.loads((b/'old-normalization-bounds.validation.json').read_text())['before_assembly'];after=freeze['after_bounds'];numbers=lambda s:[float(x) for x in re.findall(r'[-+]?(?:\d*\.?\d+)(?:[eE][-+]?\d+)?',s)]
 assembled={'position':numbers(after['minimum']),'size':numbers(after['size'])}
 for constant,box in [('OLD_BOUNDS',before),('ASSEMBLED_BOUNDS',assembled)]:binder=re.sub(r'const '+constant+r' := .*','const '+constant+' := AABB('+vec(box['position'])+', '+vec(box['size'])+')',binder)
 binder=binder.replace('old_lods.size() == 10',f'old_lods.size() == {d["mesh_count"]}').replace('meshes.size() == 10 and surfaces == 11 and fin_surfaces == 7',f'meshes.size() == {d["mesh_count"]} and surfaces == {d["surface_count"]} and fin_surfaces == {fin_surfaces}')
 binder=binder.replace('["Anal", "Caudal", "Dorsal", "Pectoral_left", "Pectoral_right", "Pelvic_left", "Pelvic_right"]',json.dumps(fin_names)).replace('get_bone_count() == 18',f'get_bone_count() == {d["bones"]}').replace('"native_animation_tracks": 16',f'"native_animation_tracks": {d["tracks"]}')
 binderpath=GAME/'scripts/aquarium'/f'Finalized{camel}{i}.gd';(b/'repro'/binderpath.name).write_text(binder)
 installed=GAME/'assets/models/fish'/(sp+'.glb');current=sha(installed);assert current in [old,d['candidate_sha']]
 if current==old:
  assert json.loads((b/'visual-old/motion-visual.validation.json').read_text())['glb_sha256']==old
  shutil.copy2(GAME/prefix/'materials.json',b/'old-materials.json')
  for item in [x for rows in manifest['materials'].values() for x in rows]+list(manifest['textures'].values()):
   rel=Path(item['path'].removeprefix('res://'));assert rel.parent==prefix;assert sha(project/rel)==item['sha256'];shutil.copy2(project/rel,GAME/rel)
  for source,target in [('old-native-animation.res','old-native-animation.res'),('old-actual-arrays-and-lods.bin','old-lod-data.bin')]:shutil.copy2(b/source,GAME/prefix/target)
  shutil.copy2(manifest_path,GAME/prefix/'materials.json');shutil.copy2(b/(sp+'-static.glb'),installed)
  shutil.copy2(project/'assets/models/fish'/(sp+'.glb.import'),GAME/'assets/models/fish'/(sp+'.glb.import'))
  shutil.copy2(b/'repro'/(sp+'_post_import.gd'),GAME/'scripts/aquarium/import'/(camel+str(i)+'.gd'))
 binderpath.write_text(binder)
 source=GAME/'scripts/aquarium/FishSurfaceOwnership.gd';text=source.read_bytes().decode();nl='\r\n' if '\r\n' in text else '\n';anchor='func apply(model: Node3D, species: String) -> Dictionary:'+nl
 branch=f'    if species=="{sp}" and FileAccess.get_sha256(model.scene_file_path)=="{d["candidate_sha"]}":'+nl+f'        return preload("res://scripts/aquarium/{binderpath.name}").new().apply(model,species)'+nl
 if branch not in text:assert anchor in text;text=text.replace(anchor,anchor+branch,1);source.write_bytes(text.encode())
 source=GAME/'scripts/aquarium/VolumeFishExhibit.gd';text=source.read_bytes().decode();nl='\r\n' if '\r\n' in text else '\n';anchor='        var corrected: Variant = null'+nl
 branch=f'        if species == "{sp}" and FileAccess.get_sha256(model.scene_file_path) == "{d["candidate_sha"]}":'+nl+f'            corrected = preload("res://scripts/aquarium/{binderpath.name}").new().normalization_bounds(model)'+nl
 if branch not in text:assert anchor in text;text=text.replace(anchor,anchor+branch,1);source.write_bytes(text.encode())
 d['manifest_sha']=manifest_sha;d['fin_names']=fin_names;d['fin_surfaces']=fin_surfaces;save(b/'migration-parameters.validation.json',d)
 save(b/'candidate-install.validation.json',{'kind':'local_static_candidate_install','ok':True,'formal_acceptance':False,'species':sp,'old_sha256':old,'candidate_sha256':sha(installed),'manifest_sha256':sha(GAME/prefix/'materials.json'),'binder_sha256':sha(binderpath),'scope':'Only this species and candidate hash skips its old static assembly; normal live controller retained.'})
 print(json.dumps({'species':sp,'installed':True,'meshes':d['mesh_count']}),flush=True)
def new_check(sp):
 b,i,camel,old,d=params_for(sp);assert sha(GAME/'assets/models/fish'/(sp+'.glb'))==d['candidate_sha']
 script=emit('test_final_binder.gd',sp);script.write_text(script.read_text().replace('changed.fin_surfaces == 7',f'changed.fin_surfaces == {d["fin_surfaces"]}'))
 text=godot(script,b,'main-binder',args=[]);marker=sp.upper()+'_BINDER ';receipt=json.loads(next(x[len(marker):] for x in text.splitlines() if x.startswith(marker)));assert receipt['ok'] and receipt['receipt']['static_build_calls']==0
 save(b/'main-cold-binder.validation.json',{'kind':'main_entry_cold_binder','ok':True,'fresh_process':True,'formal_acceptance':False,'species':sp,'installed_glb_sha256':d['candidate_sha'],**receipt})
 # Revalidate lookup texels against the actual main-project imported vertex arrays.
 cold=b/'repro/main_cold_lookups.gd';cold.write_text((b/'repro/cold_load_candidate.gd').read_text().replace(f'materials-candidate-{i}.json','materials.json').replace('local-cold-load.validation.json','main-cold-lookups.validation.json'))
 godot(cold,b,'main-lookup-cold');assert json.loads((b/'main-cold-lookups.validation.json').read_text())['ok']
 visual(sp,'new')
 compare=emit('compare_visual.py',sp);comparison=compare.read_text().replace('from run_freeze import BASE','from pathlib import Path\nBASE = Path(__file__).resolve().parents[1]')
 comparison=re.sub(r'("visual_review": )"[^"\n]*"',lambda m:m[1]+'"Human visual review must be recorded separately in local-checkpoint.validation.json."',comparison)
 compare.write_text(comparison);run([os.sys.executable,compare],b,'visual-compare')
 report=json.loads((b/'visual-compare.validation.json').read_text());assert report['ok']
 print(json.dumps({'species':sp,'main_cold_and_visual':True,'pixels':[{k:v for k,v in r.items() if k in ['view','changed_fish_pixels_over_12','fish_area_ratio_new_over_old']} for r in report['views']]}),flush=True)

def main_arrays(sp):
 b,i,c,o,d=params_for(sp)
 script=emit('inspect_main_import.gd',sp,TEMPLATE/'inspect_candidate_import.gd')
 text=hashes(script.read_text(),d,b).replace('candidate-import.validation.json','main-import-arrays.validation.json').replace('Isolated import only; no game asset installed or runtime static builder applied.','Fresh main-project import array inventory; shader lookup order compared to the accepted isolated import.')
 script.write_text(text);godot(script,b,'main-import-arrays')
 original=json.loads((b/'candidate-import.validation.json').read_text());current=json.loads((b/'main-import-arrays.validation.json').read_text())
 assert original['meshes']==current['meshes'], (sp,'main imported arrays/LOD/skin differ from isolated import')
 save(b/'main-array-parity.validation.json',{'kind':'main_vs_isolated_import_array_parity','ok':True,'species':sp,'candidate_sha256':d['candidate_sha'],'all_surface_array_hashes_skin_and_lod_equal':True,'isolated_report_sha256':sha(b/'candidate-import.validation.json'),'main_report_sha256':sha(b/'main-import-arrays.validation.json')})
 print(json.dumps({'species':sp,'main_array_parity':True}),flush=True)
