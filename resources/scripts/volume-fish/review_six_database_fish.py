"""Open the six hash-bound library/SOP candidates without changing game assets."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];G=ROOT/'projects/fishing-2d'
HERE=Path(__file__).resolve().parent;sys.path.insert(0,str(HERE/'portable'))
from view import prepare,sha256,godot_errors
read=lambda p:json.loads(Path(p).read_text(encoding='utf8'))
def verified(value):
    p=Path(value['path']);p=(ROOT/p).resolve()if not p.is_absolute()else p.resolve()
    assert p.is_file()and sha256(p)==value['sha256'],'Missing/stale review input: '+str(p)
    return p
def build(output,smoke):
    batch=G/'plans/reviews/six-fish-database-20261104/manifest.json';rows=read(batch)['records'];entries=[];bindings={str(batch):sha256(batch)}
    for row in rows:
        folder=G/f'experiments/six-fish-database-20261104/{row["species"]}';state=folder/'manifest.json';m=read(state)
        assert m['status']=='done'and m['next_action']=='human_review','Species is not ready: '+row['species']
        model=verified(m['model']);verified(m['editable_source']);spec=verified(m['final_spec']);sop=read(verified(m['sop_report']));review=verified(m['production_review'])
        assert sop['ok']and sop['review_sha256']==sha256(review),'Current SOP receipt differs'
        config=prepare(spec);assert config['model_sha256']==sha256(model)
        motion=read(config['controller']['profile']);source_spec=read(spec)
        entries.append({'id':row['species'],'label':row['name'],'status':'资料库复核 · 保留现版'if m.get('static_changed')is False else'资料库修订 · 待整鱼复看','triangles':source_spec['expected']['triangles'],'length_cm':motion['real_length_cm'],'viewer':config})
        bindings[str(state)]=sha256(state)
        for p in config['input_paths']:bindings[p]=sha256(p)
    for filename in ['SixDatabaseFishListViewer.gd','FishAssetViewer.gd']:
        p=HERE/'portable'/filename;bindings[str(p)]=sha256(p)
    return {'kind':'existing_fish_review_list','entries':entries,'bindings':bindings,'mode':'smoke'if smoke else'interactive','output':str(output)}
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--godot',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args();assert a.godot.is_file()
    out=ROOT/'output/six-fish-review-20261104'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    config=out/'catalog.json';config.write_text(json.dumps(build(out,a.smoke),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    command=[str(a.godot),'--path',str(G/'game'),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--script',str(HERE/'portable/SixDatabaseFishListViewer.gd'),'--','--catalog='+str(config)]
    with(out/'viewer.log').open('w',encoding='utf8')as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        if a.smoke:
            assert child.wait(timeout=90)==0
            assert not godot_errors((out/'viewer.log').read_text(encoding='utf8'))
            assert read(out/'viewer.validation.json')['ok']
    print(json.dumps({'ok':True,'pid':child.pid,'output':str(out),'smoke':a.smoke,'asset_writes':False}))
if __name__=='__main__':
    if (G/'plans/reviews/six-fish-release-20261104/manifest.json').exists():
        from open_six_final import main as final_main
        final_main()
    else:main()
