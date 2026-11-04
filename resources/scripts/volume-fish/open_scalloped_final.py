"""Open the accepted scalloped hammerhead fish, checking its static freeze before display."""
from pathlib import Path
import argparse,sys,json,subprocess,datetime
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(Path(__file__).with_name('portable')))
from view import prepare
from check_frozen_fish_static import fingerprint

def main():
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--godot',type=Path,default=Path.home()/'.gamefactory/toolchain/godot/Godot_mono.app/Contents/MacOS/Godot')
 args=parser.parse_args();assert args.godot.is_file(),'Pass --godot pointing to the Godot executable'
 game=ROOT/'projects/fishing-2d';release=game/'plans/reviews/scalloped-hammerhead-release-20261104'
 config=prepare(release/'viewer-spec.json');freeze=json.loads((game/'assets/source/fish/scalloped_hammerhead/frozen-static.json').read_text(encoding='utf8'))
 assert fingerprint(game/'game/assets/models/fish/scalloped_hammerhead.glb')==freeze['static'],'Accepted static fish changed; inspect before displaying'
 out=ROOT/'output/scalloped-final-viewer'/datetime.datetime.now().strftime('%Y%m%d-%H%M%S-%f');out.mkdir(parents=True)
 config.update(output=str(out),mode='interactive');config_path=out/'viewer-config.json';config_path.write_text(json.dumps(config,indent=2),encoding='utf8')
 command=[str(args.godot),'--path',str(game/'game'),'--rendering-method','gl_compatibility','--script',str(Path(__file__).with_name('ScallopedFinalReview.gd')),'--','--config='+str(config_path)]
 with (out/'viewer.log').open('w',encoding='utf8') as log:child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT)
 print(json.dumps({'pid':child.pid,'log':str(out/'viewer.log'),'accepted_static_unchanged':True}))
if __name__=='__main__':main()
