"""Bind six accepted exports to the existing source-owned canonical loader.

Only the declared six rows and their retired import/static branches change.
Carp keeps its exact reviewed controller; all other controller bytes stay put.
"""
import hashlib,json,re,shutil,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d';R=G/'plans/reviews/six-fish-release-20261104'
NAMES=['red_seabream','black_seabream','crucian','grass_carp','carp','bluegill']
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def write(p,d):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf8')
def ref(p):return {'path':str(p.resolve()),'sha256':sha(p)}
def retain(src,dst):
 dst.parent.mkdir(parents=True,exist_ok=True)
 if dst.exists():assert sha(src)==sha(dst)
 else:shutil.copy2(src,dst)

def main():
 R.mkdir(parents=True,exist_ok=True);tablepath=G/'game/assets/models/fish/motion/width20261101/manifest.json';backup=R/'history/runtime-before/width-table.json'
 if not backup.exists():retain(tablepath,backup)
 previous=read(backup);table=read(tablepath);initial=read(G/'plans/reviews/six-fish-database-20261104/manifest.json')
 if not(R/'history/initial-six-review-manifest.json').exists():retain(G/'plans/reviews/six-fish-database-20261104/manifest.json',R/'history/initial-six-review-manifest.json')
 # A byte-identical game-local copy allows the reviewed carp controller to run
 # in an exported game without substituting the other species' controller.
 original=ROOT/'resources/runtime/godot/VolumeFishMotion.gd';carp=G/'game/scripts/aquarium/ReleasedCarpMotion20261104.gd';retain(original,carp)
 for s in NAMES:
  folder=R/s
  if not(folder/'spec.json').exists():continue
  spec=read(folder/'spec.json');model=Path(spec['model']['path']);assert sha(model)==spec['model']['sha256']
  motion=Path(spec['motion']['profile']['path']);motion=motion if motion.is_absolute()else ROOT/motion;cfg=read(motion)
  dest=tablepath.parent/(s+'.json')
  if dest.exists():assert sha(dest)==sha(motion),'Existing motion differs; do not overwrite silently'
  else:retain(motion,dest)
  # Red's .3 is its accepted canonical normalization. Its old source-comparison
  # viewer used a distinct full-canvas scale; do not migrate that as a size edit.
  scale=previous['profiles'][s]['model_scale']if s in ['red_seabream','black_seabream']else spec['viewer']['model_scale']
  script='res://scripts/aquarium/ReleasedCarpMotion20261104.gd'if s=='carp'else'res://scripts/aquarium/FoundryFishMotion.gd'
  scriptfile=G/'game'/script.removeprefix('res://')
  table['profiles'][s]={'model_sha256':sha(model),'triangles':spec['expected']['triangles'],'logical_fins':7,'real_length_cm':cfg['real_length_cm'],'model_scale':scale,'motion_profile':'res://assets/models/fish/motion/width20261101/'+s+'.json','motion_sha256':sha(dest),'motion_runtime':script,'motion_runtime_sha256':sha(scriptfile),'appearance_and_rig_frozen':True,'user_accepted_date':'2026-11-04','release_metadata':f'resources/volume-fish/{s.replace("_","-")}-final-20261104.json'}
  assert sha(scriptfile)==spec['motion']['runtime']['sha256'],s+' reviewed controller changed'
 for s,row in previous['profiles'].items():
  if s not in NAMES:assert table['profiles'][s]==row,'Unrelated frozen row changed'
 write(tablepath,table)
 # Never modify these sources more than the declared retired branches and
 # per-accepted-species controller selection.
 exhibit=G/'game/scripts/aquarium/VolumeFishExhibit.gd';ownership=G/'game/scripts/aquarium/FishSurfaceOwnership.gd';loader=G/'game/scripts/aquarium/FinalizedWidthBatch20261101.gd'
 legacy=['FinalizedGrassCarp175','FinalizedCrucian168','FinalizedCarp167','FinalizedBluegill165'];changed=[]
 for p in [exhibit,ownership]:
  before=R/'history/runtime-before'/p.name
  if not before.exists():retain(p,before)
  text=before.read_text(encoding='utf8');lines=text.splitlines(keepends=True);remove=set()
  for i,line in enumerate(lines):
   if any(name+'.gd'in line for name in legacy):assert i>0 and lines[i-1].lstrip().startswith('if ');remove.update([i-1,i])
  text=''.join(line for i,line in enumerate(lines)if i not in remove)
  if p==exhibit:
   needle='    var controller_path: String = MOTION_SCRIPT\n'
   assert text.count(needle)==1
   text=text.replace(needle,needle+'    if finalized_width:controller_path = preload("res://scripts/aquarium/FinalizedWidthBatch20261101.gd").new().controller_script(species)\n')
  p.write_text(text,encoding='utf8');changed.append(ref(p))
 before=R/'history/runtime-before'/loader.name
 if not before.exists():retain(loader,before)
 text=before.read_text(encoding='utf8');assert 'func controller_script('not in text
 text+='\nfunc controller_script(species: String) -> String:\n\tvar row: Dictionary=table()[species]\n\tvar script: String=row.get("motion_runtime","res://scripts/aquarium/FoundryFishMotion.gd")\n\tif row.has("motion_runtime_sha256"):assert(FileAccess.get_sha256(script)==row.motion_runtime_sha256,"Reviewed motion controller changed: "+species)\n\treturn script\n'
 loader.write_text(text,encoding='utf8');changed.append(ref(loader))
 imports=[]
 for s in NAMES:
  p=G/f'game/assets/models/fish/{s}.glb.import';before=R/'history/import-before'/p.name
  if not before.exists():retain(p,before)
  text=before.read_text(encoding='utf8').replace('meshes/generate_lods=true','meshes/generate_lods=false');text=re.sub(r'^import_script/path=.*$','import_script/path=""',text,flags=re.M);p.write_text(text,encoding='utf8');imports.append(ref(p))
 write(R/'shared-runtime-preparation.validation.json',{'ok':True,'kind':'six_accepted_source_owned_runtime_bindings','table':ref(tablepath),'rows_ready':[s for s in NAMES if(R/s/'spec.json').exists()],'changed_code':changed,'imports':imports,'reviewed_carp_runtime':ref(carp),'other_controller_bytes_changed':False,'retired_legacy_branches':legacy,'scope':'Existing accepted source-owned loader, six reviewed motion configs and per-species original controller; all other table rows retained. Canonical fresh/cache/direct checks still required after all six rows become ready.'})
 print(json.dumps({'ok':True,'rows_ready':[s for s in NAMES if(R/s/'spec.json').exists()],'runtime_bindings_prepared':True,'canonical_checks_pending':True}))
if __name__=='__main__':main()
