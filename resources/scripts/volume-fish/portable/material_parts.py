"""Bind actual authored surface identities without changing source fin ownership."""
import copy

def from_author_report(original, packing, author, body, author_sha):
    assert author['ok'] and author['model_sha256']==author_sha, 'Stale author report'
    roles=author['body_surface_roles'];rows=[]
    assert roles and set(roles.values())<= {'body_skin','mouth'}
    source={(r['source_node'],r['source_surface']):r for r in original['parts']}
    old_fins={k for k,v in source.items()if v['role']=='fin'};new_fins=set();body_surfaces=set()
    for part in packing['parts']:
        node,surface=part['node'],part['surface']
        if node==body:
            body_surfaces.add(str(surface))
            rows.append({'name':node+'_'+str(surface),'logical_name':node,'role':roles[str(surface)],'source_node':node,'source_surface':surface})
        else:
            key=(node,surface);assert key in old_fins,'Undeclared fin or other mesh'
            new_fins.add(key);rows.append(copy.deepcopy(source[key]))
    assert new_fins==old_fins and new_fins, 'Missing source fin'
    assert body_surfaces==set(roles), 'Authored body surfaces differ from packing'
    result=copy.deepcopy(original);result['parts']=rows;return result
