"""New process source export and exact actual-entry measurements for two sparids."""
import subprocess,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];B=ROOT/'projects/fishing-2d/experiments/six-fish-database-20261104'
for s in ['red_seabream','black_seabream']:
 d=B/s;m=json.loads((d/'manifest.json').read_text(encoding='utf8'));calls=[]
 if not(d/'source-cold-export.validation.json').exists():calls.append(('source-export',['E:/blender/blender.exe','--background','--factory-startup','--python',str(ROOT/'resources/scripts/volume-fish/export_packed_fish_source.py'),'--','--blend',m['editable_source']['path'],'--output',str(d/'cold-fish.glb'),'--report',str(d/'source-cold-export.validation.json')]))
 calls.append(('canonical',['C:/Users/admin/.gamefactory/toolchain/godot/Godot_v4.7.1-stable_mono_win64/Godot_v4.7.1-stable_mono_win64_console.exe','--path',str(ROOT/'projects/fishing-2d/game'),'--rendering-method','gl_compatibility','--audio-driver','Dummy','--position','-3000,-3000','--script',str(ROOT/'resources/scripts/volume-fish/six_seabream_verify_entry.gd'),'--',d.as_posix(),s]))
 for name,args in calls:
  p=subprocess.run(args,cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=100);log=p.stdout.decode('utf8','replace');(d/(name+'.log')).write_text(log,encoding='utf8');assert p.returncode==0 and not any(x in log for x in ['SCRIPT ERROR','Parse Error','Assertion failed','Traceback','ERROR:']),log[:2000];print(s,name,'OK',flush=True)
 assert hashlib.sha256((d/'cold-fish.glb').read_bytes()).hexdigest()==m['model']['sha256']
