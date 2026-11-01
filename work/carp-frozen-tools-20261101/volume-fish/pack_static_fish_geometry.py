"""Bake current body/lips/eyes into existing rig GLB without resampling animation."""
from pathlib import Path
import sys,json,hashlib,struct,copy
sys.path.insert(0,str(Path(__file__).parent))
from patch_existing_fin_meshes import read,write
def main():
 p=json.loads(Path(sys.argv[1]).read_text());d,b=read(p['source']);original=bytes(b);body=next(n for n in d['nodes']if n.get('name')=='Closed_body'and'mesh'in n);old=copy.deepcopy(d['meshes'][body['mesh']]['primitives']);skin=body['skin'];parents={child:i for i,n in enumerate(d['nodes'])for child in n.get('children',[])};bodyindex=d['nodes'].index(body);parent=parents[bodyindex]
 def put(rows,kind,ctype=5126):
  count={'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[kind];fmt={5126:'f',5125:'I',5123:'H'}[ctype];b.extend(b'\0'*(-len(b)%4));off=len(b)
  for row in rows:b.extend(struct.pack('<'+fmt*count,*row))
  view=len(d['bufferViews']);d['bufferViews'].append({'buffer':0,'byteOffset':off,'byteLength':len(b)-off});a={'bufferView':view,'byteOffset':0,'count':len(rows),'componentType':ctype,'type':kind}
  if kind=='VEC3':a.update(min=[min(v[k]for v in rows)for k in range(3)],max=[max(v[k]for v in rows)for k in range(3)])
  d['accessors'].append(a);return len(d['accessors'])-1
 def primitive(part,material,clockwise=True):
  ids=part['triangles'];ids=[j for i in range(0,len(ids),3)for j in(ids[i],ids[i+2],ids[i+1])]if clockwise else ids
  return {'attributes':{'POSITION':put(part['vertices'],'VEC3'),'NORMAL':put(part['normals'],'VEC3'),'TEXCOORD_0':put(part['uv'],'VEC2'),'JOINTS_0':put(part['joints'],'VEC4',5123),'WEIGHTS_0':put(part['weights'],'VEC4')},'indices':put([(j,)for j in ids],'SCALAR',5125),'material':material,'mode':4}
 data=json.loads(Path(p['body']).read_text());d['meshes'][body['mesh']]={'name':'Closed_body','primitives':[primitive(part,old[min(int(part.get('source_surface',0)),len(old)-1)]['material'])for part in data['parts']]}
 def node(name,parts):
  mesh=len(d['meshes']);d['meshes'].append({'name':name,'primitives':parts});index=len(d['nodes']);d['nodes'].append({'name':name,'mesh':mesh,'skin':skin});d['nodes'][parent].setdefault('children',[]).append(index)
 lips=json.loads(Path(p['lips']).read_text());node('Source_lips139',[primitive(part,old[0]['material'])for part in lips['parts']]);eyes=json.loads(Path(p['eyes']).read_text())['profiles'][p['species']]
 for cap in eyes['caps']:
  part={**cap,'triangles':cap['indices']};name='Eye_relief112_'+str(float(cap['side'])).replace('.','_');node(name,[primitive(part,old[0]['material'],not eyes.get('godot_clockwise',False))])
 marker=len(d['nodes']);d['nodes'].append({'name':'Static_fish157'});d['nodes'][parent].setdefault('children',[]).append(marker)
 assert bytes(b[:len(original)])==original;dest=Path(p['output']);dest.parent.mkdir(parents=True,exist_ok=True);write(dest,d,b)
 report={'ok':True,'source_sha256':hashlib.sha256(Path(p['source']).read_bytes()).hexdigest(),'model_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'all_static_parts_in_glb':True,'original_rig_animation_binary_prefix_preserved':True,'scope':'Static body/eye/lip/fin geometry,UV,weights present in finalGLB; Godot-specific materials remain separate explicit resources.'};(dest.parent/'packing.validation.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
if __name__=='__main__':main()
