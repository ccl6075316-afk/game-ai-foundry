"""Import/LOD/native-animation/material parity using frozen per-fish evidence."""
from migrate_static_remaining import *

def params_for(sp):
 b,i,c,o=ctx(sp);return b,i,c,o,json.loads((b/'migration-parameters.validation.json').read_text())
def hashes(text,d,b):
 return text.replace('24e52770061b0418365d120449afefa100544e6ab3064acb22f65e0b7604a94e',d['candidate_sha']).replace('8ee53e972ef3c73d93de8219daf94b8ef1619f892f6559322c34f23f3fc295b0',sha(b/'old-actual-arrays-and-lods.bin'))
def engine(sp):
 b,i,camel,old,d=params_for(sp);freeze=json.loads((b/'old-actual-freeze.validation.json').read_text());prefix=Path(f'assets/models/fish/motion/final{i}/{sp}')
 project=b/'candidate-project';fish=project/'assets/models/fish';fish.mkdir(parents=True,exist_ok=True)
 (project/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Static Merge Candidate"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
 shutil.copytree(GAME/'scripts',project/'scripts',dirs_exist_ok=True);shutil.copytree(GAME/'shaders',project/'shaders',dirs_exist_ok=True);shutil.copytree(GAME/prefix,project/prefix,dirs_exist_ok=True)
 # After installation the live manifest describes reordered candidate lookup textures.
 # A replay must start from the retained old manifest, never reorder candidate tables twice.
 if (b/'old-materials.json').exists():shutil.copy2(b/'old-materials.json',project/prefix/'materials.json')
 shutil.copy2(b/(sp+'-static.glb'),fish/(sp+'.glb'));shutil.copy2(b/'original-installed.glb',fish/('old_'+sp+'.glb'))
 shutil.copy2(b/'old-native-animation.res',project/prefix/'old-native-animation.res');shutil.copy2(b/'old-actual-arrays-and-lods.bin',project/prefix/'old-lod-data.bin')
 hook=emit(sp+'_post_import.gd',sp,TEMPLATE/'grass_carp_post_import.gd');text=hashes(hook.read_text(),d,b)
 free={n:len(r['surfaces']) for n,r in freeze['after'].items() if not any(x['lods'] for x in r['surfaces'])};rebuild=[n for n in freeze['after'] if n not in free]
 text=re.sub(r'const LOD_FREE_SURFACES := \{.*?\n\}',lambda _: 'const LOD_FREE_SURFACES := '+json.dumps(free),text,flags=re.S)
 text=re.sub(r'const FIN_NAMES := \[.*?\n\]',lambda _: 'const FIN_NAMES := '+json.dumps(rebuild),text,flags=re.S)
 mapper=(TEMPLATE/'vertex_map.gd').read_text();method=mapper[mapper.index('func _build_mapping'):];a=text.index('func _build_mapping');z=text.index('func _rebuild_surface_lods');text=text[:a]+method+'\n'+text[z:]
 text=text.replace('const MATCH_POSITION := 0.0001','const MATCH_POSITION := 0.0000005').replace('old_data.size() == 10',f'old_data.size() == {d["mesh_count"]}')
 text=text.replace('node.mesh.get_surface_count() == 1','node.mesh.get_surface_count() == old_data[name].size()').replace('old_surfaces.size() == 1','old_surfaces.size() == node.mesh.get_surface_count()')
 text=text.replace('\t\tvar old_surface: Dictionary = old_surfaces[0]\n','').replace('_rebuild_surface_lods(node, si, old_surface["arrays"], old_surface)','_rebuild_surface_lods(node, si, old_surfaces[si]["arrays"], old_surfaces[si])').replace('"rebuilt_fins": fin_rows','"rebuilt_meshes": fin_rows')
 text=text.replace('Per fin:','Per LOD-bearing surface:').replace('unchanged winding (normalized cross dot >= 0.99)','unchanged winding for cross magnitude >1e-9; near-degenerate triangles counted separately')
 hook.write_text(text);target=project/'scripts/aquarium/import'/(camel+str(i)+'.gd');target.parent.mkdir(exist_ok=True);shutil.copy2(hook,target)
 sidecar=(b/'original-installed.glb.import').read_text();assert 'import_script/path=""' in sidecar
 (fish/(sp+'.glb.import')).write_text(sidecar.replace('import_script/path=""',f'import_script/path="res://scripts/aquarium/import/{camel}{i}.gd"'))
 key=sp.upper()+'_LOD_RECEIPT';os.environ[key]=str(b/'postimport-lod.receipt.json')
 run([GODOT,'--headless','--path',project,'--import','--log-file',b/'candidate-import-engine.log'],b,'candidate-import');os.environ.pop(key,None)
 inspect=emit('inspect_candidate_import.gd',sp);inspect.write_text(hashes(inspect.read_text(),d,b));godot(inspect,b,'candidate-inspect',project)
 imported=json.loads((b/'candidate-import.validation.json').read_text());assert imported['mesh_count']==d['mesh_count'] and imported['skeleton_bones']==d['bones'];assert set(imported['meshes'])==set(freeze['after'])
 lod=json.loads((b/'postimport-lod.receipt.json').read_text());assert lod['ok']
 for n,r in freeze['after'].items():assert lod['final_counts_after'][n]==[len(x['lods']) for x in r['surfaces']]
 godot(emit('compare_animation_poses.gd',sp),b,'animation-parity',project);poses=json.loads((b/'animation-pose-compare.validation.json').read_text());assert poses['ok'] and poses['old_animation_tracks']==d['tracks']
 material(sp)

def material(sp):
 b,i,camel,old,d=params_for(sp);project=b/"candidate-project";prefix=Path(f"assets/models/fish/motion/final{i}/{sp}")
 poses=json.loads((b/"animation-pose-compare.validation.json").read_text())
 material=json.loads((GAME/prefix/'materials.json').read_text());lookups={};allowed={'rest114_positions','rest114_normals','rest114_uvs','mouth136_records','mouth146_records','material130_positions','material139_positions'}
 for n,rows in material['materials'].items():
  for si,row in enumerate(rows):
   code=(GAME/row['path'].removeprefix('res://')).read_text()
   for ext in re.findall(r'path="(res://[^\"]+\.gdshader)"',code):code+='\n'+(GAME/ext.removeprefix('res://')).read_text()
   keys=sorted(set(re.findall(r'texelFetch\(\s*(\w+)',code)));assert set(keys)<=allowed,keys
   if keys:lookups[f'{n}:{si}']=keys
 d['lookups']=lookups;d['surface_count']=sum(d['mesh_surfaces'].values());save(b/'migration-parameters.validation.json',d)
 repro=project/'repro';repro.mkdir(exist_ok=True);shutil.copy2((b/'repro/vertex_map.gd') if (b/'topology-mapping.validation.json').exists() else TEMPLATE/'vertex_map.gd',repro/'vertex_map.gd')
 if (b/'repro/topology-mapping.json').exists():shutil.copy2(b/'repro/topology-mapping.json',repro/'topology-mapping.json')
 text=hashes(transform((TEMPLATE/'rebind_candidate_materials.gd').read_text(),sp),d,b);text=re.sub(r'const LOOKUPS := .*\n',lambda _: 'const LOOKUPS := '+json.dumps(lookups)+'\n',text)
 a=text.index('\t\t\t\tif si == 0:');z=text.index('\t\t\tvar path :=',a)
 uniforms='''				for table_key in LOOKUPS[label]:
					var prefix_key := String(table_key).trim_suffix("_positions").trim_suffix("_records")
					if String(table_key).begins_with("rest114_"):
						(material as ShaderMaterial).set_shader_parameter("rest114_count", mapping.new_count)
						(material as ShaderMaterial).set_shader_parameter("rest114_size", Vector2i(256, ceili(float(mapping.new_count) / 256.0)))
					elif String(table_key).ends_with("_positions"):
						(material as ShaderMaterial).set_shader_parameter(prefix_key + "_count", mapping.new_count)
						(material as ShaderMaterial).set_shader_parameter(prefix_key + "_size", Vector2i(256, ceili(float(mapping.new_count) / 256.0)))
					elif String(table_key).ends_with("_records"):
						var stride := int(old_material.get_shader_parameter("mouth136_stride")) if table_key == "mouth136_records" else 1
						(material as ShaderMaterial).set_shader_parameter(prefix_key + "_size", Vector2i(256, ceili(float(mapping.new_count * stride) / 256.0)))
'''
 text=text[:a]+uniforms+text[z:];script=b/'repro/rebind_candidate_materials.gd';script.write_text(text);godot(script,b,'material-rebind',project)
 assert json.loads((b/'material-rebind.validation.json').read_text())['ok']
 cold=emit('cold_load_candidate.gd',sp);text=hashes(cold.read_text(),d,b);a=text.index('\t\t\t\tif label == "Closed_body:0":');z=text.index('\t\t\t\tvar result :=',a);text=text[:a]+text[z:]
 text=text.replace('meshes.size() == 10 and surfaces == 11 and lookups.size() == 2',f'meshes.size() == {d["mesh_count"]} and surfaces == {d["surface_count"]} and lookups.size() == {len(lookups)}').replace('get_bone_count() == 18',f'get_bone_count() == {d["bones"]}').replace('get_track_count() == 16',f'get_track_count() == {d["tracks"]}').replace('"skeleton_bones": 18',f'"skeleton_bones": {d["bones"]}').replace('"native_animation_tracks": 16',f'"native_animation_tracks": {d["tracks"]}')
 cold.write_text(text);godot(cold,b,'candidate-cold',project);assert json.loads((b/'local-cold-load.validation.json').read_text())['ok']
 print(json.dumps({'species':sp,'engine':True,'meshes':d['mesh_count'],'surfaces':d['surface_count'],'lookup_groups':len(lookups),'native_pose_delta':poses['max_transform_component_delta']}),flush=True)
