"""Open original/A/B textured viewer using this host's configured Godot."""
from pathlib import Path
import json,sys,subprocess
repo=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(repo/'cli'))
from toolchain_paths import resolve_godot
config=Path.home()/'.gamefactory/config.json'
godot=resolve_godot(json.loads(config.read_text(encoding='utf8')) if config.exists() else {})
if not godot:raise SystemExit('Godot missing: use Foundry setup/doctor to register this host.')
directory=repo/'projects/fishing-2d/experiments/nile-dorsal-route-trial/round4-ab-textured'
revision=[] if '--round4' in sys.argv else ['--revision5'] if '--round5' in sys.argv else ['--revision6'] if '--round6' in sys.argv else ['--revision7']
raise SystemExit(subprocess.call([godot,'--path',str(repo/'projects/fishing-2d/game'),'--rendering-method','gl_compatibility','--script',str(Path(__file__).with_name('preview_nile_three_live.gd')),'--',str(directory),'--live',*revision,*(['--smoke'] if '--smoke' in sys.argv else [])]))
