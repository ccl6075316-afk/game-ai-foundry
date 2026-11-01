"""Resolve coincident shader-lookup vertices by directed triangle-fan identity."""
from migrate_static_remaining import *
from collections import defaultdict,Counter
import itertools

def build(sp):
 assert sp == 'peacock_bass', 'This topology probe is bound to Peacock Bass 177 only'
 b,*_=ctx(sp);project=b/'candidate-project'
 run([GODOT,'--headless','--path',project,'--import','--log-file',b/'restore-default-import-engine.log'],b,'restore-default-import')
 godot(b/'repro/export_mapping_probe.gd',b,'mapping-probe',project)
 data=json.loads((b/'mapping-probe.json').read_text());output={};proof=[]
 for si,row in data.items():
  a,z=row['old'],row['new'];op,ou=a['positions'],a['uv'];np,nu=z['positions'],z['uv'];buckets=defaultdict(list)
  def cell(p):return tuple(int(v//.001) for v in p)
  for oi,p in enumerate(op):buckets[cell(p)].append(oi)
  def near(p,uv):
   c=cell(p);out=[]
   for delta in itertools.product([-1,0,1],repeat=3):
    for oi in buckets.get(tuple(c[k]+delta[k] for k in range(3)),[]):
     if max(abs(x-y) for x,y in zip(p,op[oi]))<=5e-7 and max(abs(x-y) for x,y in zip(uv,ou[oi]))<=1e-6:out.append(oi)
   return out
  canonical=[]
  for oi,p in enumerate(op):canonical.append(min(near(p,ou[oi])))
  choices=[near(p,uv) for p,uv in zip(np,nu)];assert all(choices)
  nc=[canonical[choices[ni][0]] for ni in range(len(np))]
  oldfans=[Counter() for _ in op];newfans=[Counter() for _ in np]
  for ids,fans,canon in [(a['indices'],oldfans,canonical),(z['indices'],newfans,nc)]:
   for t in range(0,len(ids),3):
    tri=ids[t:t+3]
    for k in range(3):fans[tri[k]][(canon[tri[(k+1)%3]],canon[tri[(k+2)%3]])]+=1
  mapping=[];ambiguous=0
  for ni,opts in enumerate(choices):
   valid=[oi for oi in opts if all(oldfans[oi][k]>=n for k,n in newfans[ni].items())]
   assert valid,('No incident-fan match',si,ni,opts)
   if len(valid)>1:ambiguous+=1
   best=min(valid,key=lambda oi:sum(abs(x-y) for x,y in zip(a['normals'][oi],z['normals'][ni])))
   mapping.append(best)
  def directed(ids,mapping=None):
   out=Counter()
   for at in range(0,len(ids),3):
    v=tuple(mapping[x] if mapping is not None else x for x in ids[at:at+3]);out[min(v,v[1:]+v[:1],v[2:]+v[:2])]+=1
   return out
  assert ambiguous == 0, ('Ambiguous topology mapping requires investigation',si,ambiguous)
  assert directed(a['indices'])==directed(z['indices'],mapping),('Directed triangle identities differ',si)
  assert len(set(mapping))==len(op),('Old vertices not represented',si,len(set(mapping)),len(op))
  label='Closed_body:'+si
  output[label]={'old_arrays_sha256':a['arrays_sha256'],'new_arrays_sha256':z['arrays_sha256'],'new_to_old':mapping}
  proof.append({'surface':int(si),'old_vertices':len(op),'new_vertices':len(np),'old_represented':len(set(mapping)),'directed_triangle_multiset_equal':True,'ambiguous_fan_matches':ambiguous})
 save(project/'repro/topology-mapping.json',output);shutil.copy2(project/'repro/topology-mapping.json',b/'repro/topology-mapping.json')
 save(b/'topology-mapping.validation.json',{'kind':'directed_triangle_fan_vertex_mapping','ok':True,'method':'Position/UV candidate groups; each new vertex incident directed fan must be a subset of the old fan. Final mapped full index triangle multiset must equal old actual indices, including winding and multiplicity. Runtime mapper rechecks full-array SHA, positions, UV, skin weights and normals.','surfaces':proof,'mapping_sha256':sha(b/'repro/topology-mapping.json')})
 text=transform((TEMPLATE/'vertex_map.gd').read_text(),sp)
 insert='''func _digest_arrays(value: Array) -> String:
	var h := HashingContext.new();h.start(HashingContext.HASH_SHA256);h.update(var_to_bytes(value));return h.finish().hex_encode()

func _topology_mapping(old_arrays: Array, node: MeshInstance3D, si: int) -> Dictionary:
	var label := String(node.name) + ":" + str(si)
	var rows: Dictionary = JSON.parse_string(FileAccess.get_file_as_string("res://repro/topology-mapping.json"))
	assert(rows.has(label));var proof: Dictionary = rows[label]
	var current := node.mesh.surface_get_arrays(si)
	assert(_digest_arrays(old_arrays) == proof.old_arrays_sha256 and _digest_arrays(current) == proof.new_arrays_sha256, "Mapping proof input changed")
	var op: PackedVector3Array = old_arrays[Mesh.ARRAY_VERTEX];var np: PackedVector3Array = current[Mesh.ARRAY_VERTEX]
	var ou: PackedVector2Array = old_arrays[Mesh.ARRAY_TEX_UV];var nu: PackedVector2Array = current[Mesh.ARRAY_TEX_UV]
	var on: PackedVector3Array = old_arrays[Mesh.ARRAY_NORMAL];var nn: PackedVector3Array = current[Mesh.ARRAY_NORMAL]
	var ow := _weight_map(old_arrays[Mesh.ARRAY_BONES],old_arrays[Mesh.ARRAY_WEIGHTS],op.size())
	var nw := _weight_map(current[Mesh.ARRAY_BONES],current[Mesh.ARRAY_WEIGHTS],np.size())
	var mapped := PackedInt32Array(proof.new_to_old);assert(mapped.size() == np.size())
	var reverse := PackedInt32Array();reverse.resize(op.size());reverse.fill(-1)
	var mp := 0.0;var mu := 0.0;var mw := 0.0;var mn := 0.0
	for ni in mapped.size():
		var oi := mapped[ni];assert(oi >= 0 and oi < op.size());reverse[oi] = ni
		mp=maxf(mp,maxf(absf(op[oi].x-np[ni].x),maxf(absf(op[oi].y-np[ni].y),absf(op[oi].z-np[ni].z))))
		mu=maxf(mu,maxf(absf(ou[oi].x-nu[ni].x),absf(ou[oi].y-nu[ni].y)))
		mw=maxf(mw,_weight_delta(ow[oi],nw[ni]));mn=maxf(mn,_normal_delta(on[oi],nn[ni]))
	assert(mp <= MATCH_POSITION and mu <= MATCH_UV and mw <= MATCH_WEIGHT and mn <= 0.001)
	assert(not reverse.has(-1))
	return {"new_to_old":mapped,"old_to_new":reverse,"equivalent_old_aliases":{},"old_count":op.size(),"new_count":np.size(),"old_represented":op.size(),"max_position":mp,"max_uv":mu,"max_weight":mw,"max_normal":mn}

'''
 # Keep the checked generic geometric matcher as a fallback for unrelated surfaces.
 text=text.replace('func _build_mapping(old_arrays: Array, node: MeshInstance3D, si: int) -> Dictionary:\n','func _build_mapping(old_arrays: Array, node: MeshInstance3D, si: int) -> Dictionary:\n\tif FileAccess.file_exists("res://repro/topology-mapping.json"):\n\t\treturn _topology_mapping(old_arrays,node,si)\n',1)
 text=text.replace('func _build_mapping',insert+'func _build_mapping',1)
 (b/'repro/vertex_map.gd').write_text(text);(project/'repro/vertex_map.gd').write_text(text)
 print(json.dumps({'species':sp,'topology_proof':proof}),flush=True)
if __name__=='__main__':build('peacock_bass')
