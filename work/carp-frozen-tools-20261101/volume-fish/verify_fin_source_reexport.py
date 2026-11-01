"""Read-only guarded source verification: geometry/UV/skin/NORMAL, image bytes and clips.
Uses authored source float corner normals; never changes the input blend/model.
Existing exports are deliberately unsupported here. Only this invocation's own
new temporary export may be removed after a successful complete comparison.
"""
import argparse,json,runpy,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--model',type=Path,required=True);p.add_argument('--blend',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);inputs={a.model.resolve(),a.blend.resolve()};output=a.output.resolve();owned_temp=output.with_suffix('.glb');assert output not in inputs and owned_temp not in inputs,'Verifier output must not alias either input';assert not owned_temp.exists(),'Refuse existing temporary export'
sys.argv.append('--supported-export');state=runpy.run_path(str(Path(__file__).with_name('measure_fin_source_parity.py')),run_name='__main__');report=state['r'];assert report['ok'],'Actual source re-export parity failed; diagnostic output retained'
assert state['a'].existing_export is None and state['temp'].resolve()==owned_temp and owned_temp not in inputs,'Never delete an input or caller-owned export';owned_temp.unlink();report['temporary_export_removed']=True;state['a'].output.write_text(json.dumps(report,indent=2));print(json.dumps({'ok':True,'model_sha256':report['model_sha256'],'blend_sha256':report['blend_sha256'],'normal_max':max(v['max_component_error']for v in report['fin_normals'].values()),'all_embedded_material_pixels_exact':all(v['embedded_bytes_equal']for v in report['materials'].values()),'clips_exact':all(v['passes_1e_6']for v in report['clips'].values())}))
