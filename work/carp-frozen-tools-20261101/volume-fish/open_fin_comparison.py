"""Open the saved Nile experiment; --check only prints the portable command."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--godot',help='Existing Godot executable; never downloads tools')
    parser.add_argument('--round2',action='store_true')
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[3]
    trial=root/'projects/fishing-2d/experiments/nile-dorsal-route-trial'
    supplied=args.godot or os.environ.get('GAMEFACTORY_GODOT')
    candidates=[supplied,shutil.which('godot'),shutil.which('godot4'),
                str(Path.home()/'.gamefactory/toolchain/godot/Godot_mono.app/Contents/MacOS/Godot')]
    executable=next((Path(p).expanduser().resolve() for p in candidates if p and Path(p).expanduser().is_file()),None)
    if executable is None:
        parser.error('Existing Godot not located. Use --godot with its path; inspect docs/TOOLS.md before installing anything.')
    required=[trial/'round2/fins.glb'] if args.round2 else [trial/m/'fin.glb' for m in ['route-a-600','route-b-600']]
    for path in required:
        if not path.is_file() or path.open('rb').read(4)!=b'glTF':
            parser.error(f'Missing GLB or Git LFS pointer instead of contents: {path}. Pull the retained LFS assets first.')
    folder=trial/'round2' if args.round2 else trial
    command=[str(executable),'--path',str(root/'projects/fishing-2d/game'),
             '--log-file',str(folder/'live-window-engine.log'),'--script',
             str(root/'resources/scripts/volume-fish/preview_fin_routes.gd'),'--',str(trial),'--live']
    if args.round2:command.append('--round2')
    if args.check:
        print(json.dumps({'command':command,'cwd':str(folder),'starts_process':False},ensure_ascii=False));return
    env=os.environ.copy();dotnet=Path.home()/'.gamefactory/toolchain/dotnet'
    if dotnet.is_dir():env['PATH']=str(dotnet)+os.pathsep+env.get('PATH','')
    with (folder/'live-window.log').open('w') as log:
        process=subprocess.Popen(command,cwd=folder,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps({'pid':process.pid,'log':str(folder/'live-window.log'),'formal_acceptance':False}))

if __name__=='__main__':main()
