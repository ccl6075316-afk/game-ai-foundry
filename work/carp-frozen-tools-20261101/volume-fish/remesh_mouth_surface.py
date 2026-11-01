"""Parameterised remesh128 with optional sub-precision topology cleanup."""
import runpy
from pathlib import Path
import json
scripts=Path(__file__).resolve().parent
g=runpy.run_path(str(scripts/'remesh_head_trial128.py'))
if g['spec'].get('topology_weld_native'):
    helper=runpy.run_path(str(scripts/'clean_remesh_topology.py'))
    metrics=helper['clean'](g['obj'],g['spec']['topology_weld_native'])
    obj=g['obj'];np=g['np'];mesh=obj.data
    v=np.empty((len(mesh.vertices),3),np.float32);n=np.empty_like(v)
    mesh.vertices.foreach_get('co',v.ravel());mesh.vertices.foreach_get('normal',n.ravel());mesh.calc_loop_triangles()
    t=np.array([x.vertices[:] for x in mesh.loop_triangles],np.int32)[:,[0,2,1]]
    g['out'].write_text(json.dumps({'vertices':v.tolist(),'normals':n.tolist(),'triangles':t.ravel().tolist()},separators=(',',':')))
    report=g['report'];report['outputs'][0]['sha256']=g['sha'](g['out']);report['summary']['topology_cleanup']=metrics
    report['inputs']['wrapper_sha256']=g['sha'](__file__);report['inputs']['cleanup_sha256']=g['sha'](scripts/'clean_remesh_topology.py')
    (g['root']/'geometry.validation.json').write_text(json.dumps(report,indent=2))
