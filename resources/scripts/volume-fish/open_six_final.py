"""Open the six accepted fish with hash and static-freeze checks; no asset writes."""
import argparse,datetime,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).with_name('portable')))
from view import prepare,sha256
from check_frozen_fish_static import fingerprint

def catalog(output,mode):
    game=ROOT/'projects/fishing-2d';release=game/'plans/reviews/six-fish-release-20261104'
    entries=[];bindings={}
    for row in json.loads((release/'manifest.json').read_text(encoding='utf8'))['records']:
        s=row['species'];spec=release/s/'spec.json';viewer=prepare(spec,game=game/"game")
        freeze=json.loads((game/f'assets/source/fish/{s}/frozen-static.json').read_text(encoding='utf8'))
        assert fingerprint(Path(row['model']['path']))==freeze['static'],'Accepted static fish changed: '+s
        profile=json.loads(Path(viewer['controller']['profile']).read_text(encoding='utf8'))
        entries.append({'id':s,'label':row['name'],'status':'成品 · 静态已冻结','triangles':freeze['static']['triangles'],'length_cm':profile['real_length_cm'],'viewer':viewer})
        for p in viewer['input_paths']:bindings[p]=sha256(p)
    for name in ['SixDatabaseFishListViewer.gd','FishAssetViewer.gd']:
        p=Path(__file__).with_name('portable')/name;bindings[str(p)]=sha256(p)
    return {'kind':'existing_fish_review_list','entries':entries,'bindings':bindings,'mode':mode,'output':str(output)}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--godot',required=True,type=Path);p.add_argument('--smoke',action='store_true');a=p.parse_args();assert a.godot.is_file()
    out=ROOT/'output/six-final-viewer'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
    config=out/'catalog.json';config.write_text(json.dumps(catalog(out,'smoke' if a.smoke else 'interactive'),ensure_ascii=False,indent=2)+'\n',encoding='utf8')
    command=[str(a.godot),'--path',str(ROOT/'projects/fishing-2d/game'),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--script',str(Path(__file__).parent/'portable/SixDatabaseFishListViewer.gd'),'--','--catalog='+str(config)]
    with (out/'viewer.log').open('w',encoding='utf8')as log:
        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
        if a.smoke:
            assert child.wait(timeout=60)==0
            from view import godot_errors
            assert not godot_errors((out/'viewer.log').read_text(encoding='utf8'))
            report=json.loads((out/'viewer.validation.json').read_text(encoding='utf8'));assert report['ok']
    print(json.dumps({'pid':child.pid,'output':str(out),'accepted_static_unchanged':True,'smoke':a.smoke}))
if __name__=='__main__':main()
