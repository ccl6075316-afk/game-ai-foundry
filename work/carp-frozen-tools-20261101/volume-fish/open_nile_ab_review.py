"""Open original/A/B textured viewer using this host's configured Godot."""
from pathlib import Path
import json,sys,subprocess,os
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'cli'))
from toolchain_paths import resolve_godot
config=Path.home()/'.gamefactory/config.json'
godot=resolve_godot(json.loads(config.read_text(encoding='utf8')) if config.exists() else {})
if not godot:raise SystemExit('Godot missing: use Foundry setup/doctor to register this host.')
directory=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial/round4-ab-textured'
round_number=next((n for n in range(4,12) if '--round'+str(n) in sys.argv),11)
revision=[] if round_number==4 else ['--revision'+str(round_number)]
round_dirs={4:'round4-ab-textured',5:'round5-user-review-fixes',6:'round6-reference-repair',7:'round7-upper-lip-continuity',8:'round8-upper-lip-pixel-clusters',9:'round9-fin-clearance',10:'round10-material-performance',11:'round11-single-material-finalization'}
model_relative={9:'final-B-artifacts/fish.glb',10:'candidates-v2/merged-mask.glb',11:'final-artifacts/fish.glb'}.get(round_number,'B-artifacts/fish.glb')
model=directory.parent/round_dirs[round_number]/model_relative
if not model.is_file():raise SystemExit('Requested Nile B round '+str(round_number)+' model is missing: '+str(model))
command=[godot,'--path',str(repo/'projects/fishing-2d/game'),'--rendering-method','gl_compatibility','--script',str(Path(__file__).with_name('preview_nile_three_live.gd')),'--',str(directory),'--live',*revision,*(['--smoke'] if '--smoke' in sys.argv else [])]
child_env=os.environ.copy();env_overrides={}
dotnet=Path.home()/'.gamefactory/toolchain/dotnet'
if (dotnet/'dotnet').is_file():
 child_env['DOTNET_ROOT']=str(dotnet);child_env['PATH']=str(dotnet)+os.pathsep+child_env.get('PATH','');env_overrides={'DOTNET_ROOT':str(dotnet),'PATH_prepend':str(dotnet)}
if '--check' in sys.argv:
 print(json.dumps({'round':round_number,'model':str(model),'command':command,'child_env_overrides':env_overrides},ensure_ascii=False));raise SystemExit(0)
raise SystemExit(subprocess.call(command,env=child_env))
