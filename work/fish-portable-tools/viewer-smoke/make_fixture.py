from pathlib import Path
import json, struct, hashlib
base=Path(__file__).resolve().parent
binary=struct.pack('<9f',-1,0,0,1,0,0,0,1,0)+struct.pack('<3H',0,1,2)+b'\0\0'+struct.pack('<2f',0,1)+struct.pack('<6f',0,0,0,0,.3,0)
doc={'asset':{'version':'2.0'},'scene':0,'scenes':[{'nodes':[0]}],'nodes':[{'name':'SyntheticAnimatedTriangle','mesh':0}],'meshes':[{'primitives':[{'attributes':{'POSITION':0},'indices':1,'material':0}]}],'materials':[{'doubleSided':True,'pbrMetallicRoughness':{'baseColorFactor':[.2,.7,.6,1],'metallicFactor':0,'roughnessFactor':1}}],'buffers':[{'byteLength':len(binary)}],'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':36},{'buffer':0,'byteOffset':36,'byteLength':6},{'buffer':0,'byteOffset':44,'byteLength':8},{'buffer':0,'byteOffset':52,'byteLength':24}],'accessors':[{'bufferView':0,'componentType':5126,'count':3,'type':'VEC3','min':[-1,0,0],'max':[1,1,0]},{'bufferView':1,'componentType':5123,'count':3,'type':'SCALAR'},{'bufferView':2,'componentType':5126,'count':2,'type':'SCALAR','min':[0],'max':[1]},{'bufferView':3,'componentType':5126,'count':2,'type':'VEC3'}],'animations':[{'name':'SyntheticTranslate','channels':[{'sampler':0,'target':{'node':0,'path':'translation'}}],'samplers':[{'input':2,'output':3}]}]}
j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);binary+=b'\0'*((-len(binary))%4)
glb=struct.pack('<4sII',b'glTF',2,28+len(j)+len(binary))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(binary),0x004e4942)+binary
(base/'synthetic.glb').write_bytes(glb)
(base/'game').mkdir(exist_ok=True)
(base/'game'/'project.godot').write_text('config_version=5\n[application]\nconfig/name="Portable synthetic fixture"\n[rendering]\nrenderer/rendering_method="gl_compatibility"\n')
spec={'kind':'fish_asset_finalization_spec','version':1,'species':'synthetic_fixture','model':{'path':str(base/'synthetic.glb'),'sha256':hashlib.sha256(glb).hexdigest()},'game':str(base/'game'),'viewer':{'native_clip':'SyntheticTranslate','focuses':{'head':{'mode':'bbox_relative','position':[.75,.5,.5]}},'captures':[{'name':'front','time_seconds':0},{'name':'oblique','yaw_degrees':35,'pitch_degrees':20,'time_seconds':.5}]}}
(base/'spec.json').write_text(json.dumps(spec,indent=2)+'\n')
