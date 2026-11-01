"""Read-only counts of explicitly provided public reference FBX.

No scene/code executes from the asset; factory-startup Blender imports geometry.
Keep the download URL/archive SHA in a separate validation report.
"""
import sys,json,hashlib,re
from pathlib import Path
arguments=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
source=Path(arguments[0]).resolve();output=Path(arguments[1]).resolve()
assert source.suffix.lower()=='.fbx' and source.is_file()
assert output.parent.is_relative_to(Path(__file__).resolve().parents[3]/'projects/fishing-2d/plans/reviews')
rows=[]
data=source.read_bytes()
if data.startswith(b'; FBX'):
    text=data.decode('utf-8-sig')
    starts=list(re.finditer(r'Geometry:\s*(\d+),\s*"([^"]*)",\s*"Mesh"\s*\{',text))
    for start in starts:
        depth=1;at=start.end();quoted=False;escaped=False
        while depth:
            char=text[at];at+=1
            if escaped:escaped=False;continue
            if quoted and char=='\\':escaped=True;continue
            if char=='"':quoted=not quoted
            if not quoted:depth+=(char=='{')-(char=='}')
        block=text[start.end():at-1]
        def values(name,cast):
            match=re.search(r'\b'+name+r':\s*\*(\d+)\s*\{\s*a:\s*([^}]+)\}',block)
            assert match,name
            result=[cast(x) for x in re.split(r'[,\s]+',match[2].strip()) if x]
            assert len(result)==int(match[1])
            return result
        vertices=values('Vertices',float);indices=values('PolygonVertexIndex',int)
        assert len(vertices)%3==0
        sizes=[];length=0
        for value in indices:
            index=value if value>=0 else -value-1
            assert 0<=index<len(vertices)//3
            length+=1
            if value<0:assert length>=3;sizes.append(length);length=0
        assert length==0 and sizes
        histogram={str(size):sizes.count(size) for size in sorted(set(sizes))}
        rows.append({'geometry_id':start[1],'geometry_name':start[2],'vertices':len(vertices)//3,'polygons':len(sizes),
                     'triangles':sum(n-2 for n in sizes),'polygon_size_histogram':histogram,'already_all_triangles':all(n==3 for n in sizes)})
    assert rows,'No geometry meshes found'
    version=None
    method='Parse FBX ASCII Geometry Mesh arrays; verify counts/indices/end markers; sum polygon(n-2), exact when already triangles.'
else:
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.fbx(filepath=str(source))
    for obj in bpy.context.scene.objects:
        if obj.type!='MESH':continue
        mesh=obj.data;mesh.calc_loop_triangles()
        rows.append({'object':obj.name,'geometry_datablock':mesh.name,'vertices':len(mesh.vertices),
            'polygons':len(mesh.polygons),'triangles':len(mesh.loop_triangles),
            'materials':len(mesh.materials),'hidden_render':obj.hide_render,
            'modifiers':[{'name':m.name,'type':m.type}for m in obj.modifiers]})
    version=bpy.app.version_string
    method='Import binary FBX in factory-startup Blender, calc_loop_triangles per mesh object.'
result={'schema_version':1,'source':str(source),'sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
    'blender_version':version,'counter_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'method':method,
    'mesh_objects':rows,'total_triangles_by_object':sum(r['triangles']for r in rows),
    'scope':'Reference source-model measurement; not an official runtime LOD budget or proof of current shipped model.'}
output.write_text(json.dumps(result,indent=2)+'\n',encoding='utf8')
print('REFERENCE_FBX_COUNT',json.dumps(result),flush=True)
