"""Disconnect only the five replaced static pipelines and old import hooks."""
import hashlib,json,re,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];GAME=ROOT/'projects/fishing-2d';R=GAME/'plans/reviews/five-fish-release-20261104';names=['FinalizedRainbowTrout176','FinalizedBrownTrout166','FinalizedAtlanticSalmon164','FinalizedSeaBass170','FinalizedRedEmperor169'];changed=[]
for path in [GAME/'game/scripts/aquarium/FishSurfaceOwnership.gd',GAME/'game/scripts/aquarium/VolumeFishExhibit.gd']:
 old=path.read_text(encoding='utf8');backup=R/'history/runtime-before'/path.name;backup.parent.mkdir(parents=True,exist_ok=True);assert not backup.exists();backup.write_text(old,encoding='utf8');lines=old.splitlines(keepends=True);remove=set()
 for i,line in enumerate(lines):
  if any(name+'.gd' in line for name in names):assert i>0 and lines[i-1].lstrip().startswith('if ');remove.update([i-1,i])
 new=''.join(line for i,line in enumerate(lines)if i not in remove);assert new!=old;path.write_text(new,encoding='utf8');changed.append({'path':str(path),'removed_lines':len(remove)})
for s in ['rainbow_trout','brown_trout','atlantic_salmon','sea_bass','red_emperor']:
 path=GAME/f'game/assets/models/fish/{s}.glb.import';old=path.read_text(encoding='utf8');backup=R/'history/import-before'/path.name;backup.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,backup);new=old.replace('meshes/generate_lods=true','meshes/generate_lods=false');new=re.sub(r'^import_script/path=.*$', 'import_script/path=""',new,flags=re.M);path.write_text(new,encoding='utf8');changed.append({'path':str(path),'scope':'Current full-detail source clips/materials; no obsolete SHA-gated animation/LOD post-import hook.'})
for name in names:
 p=GAME/f'game/scripts/aquarium/{name}.gd';dest=R/'methods'/('legacy-'+p.name);shutil.copy2(p,dest)
(R/'legacy-disconnection.validation.json').write_text(json.dumps({'ok':True,'changed':changed,'scope':'Only replaced five-fish branches/hooks disconnected. Other species and shared normal animation/cache behavior retained. Deletion is a separate exact SHA plan.'},indent=2)+'\n')
