"""Apply the proven wall repair with explicit coincident source seam handling.

Anatomical wall-only mid-thickness vertices need not occur on either cap.
Resolve only exact source-q aliases whose cap UV addresses agree; never infer
an address from a nearby unrelated source point.
"""
from pathlib import Path
p=Path(__file__).with_name('repair_packed_fin_wall_uv.py')
s=p.read_text(encoding='utf8')
old=" sources[ob.name]={'positions':[tuple(v.co)for v in mesh.vertices],'q':q,'uv':cap_uv}"
new=""" aliases=[]
 for sid in range(len(mesh.vertices)):
  if sid in cap_uv:continue
  candidates=[i for i in cap_uv if np.max(np.abs(q[i]-q[sid]))<1e-7]
  if not candidates:continue
  options={cap_uv[i]for i in candidates};assert len(options)==1,(ob.name,sid,'Ambiguous source-q cap address')
  cap_uv[sid]=next(iter(options));aliases.append(sid)
 sources[ob.name]={'positions':[tuple(v.co)for v in mesh.vertices],'q':q,'uv':cap_uv,'coincident_cap_aliases':aliases}"""
assert old in s;s=s.replace(old,new)
s=s.replace("   assert sid in s['uv'],(name,'No adjacent cap UV',sid)", "   assert sid in s['uv'],(name,'No adjacent cap UV',sid,s['positions'][sid],s['q'][sid].tolist(),sorted([(float(np.linalg.norm(np.array(s['positions'][i])-np.array(s['positions'][sid]))),i,s['q'][i].tolist(),s['uv'][i])for i in s['uv']])[:5])")
s=s.replace("'cap_UV_exact':True,", "'cap_UV_exact':True,'coincident_cap_alias_source_ids':s['coincident_cap_aliases'],")
exec(compile(s,str(p),'exec'))
