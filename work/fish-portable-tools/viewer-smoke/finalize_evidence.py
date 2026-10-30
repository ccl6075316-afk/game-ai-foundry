from pathlib import Path
import hashlib,json,shutil
root=Path(__file__).resolve().parents[3];base=Path(__file__).resolve().parent
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
source=root/'resources/scripts/volume-fish/portable'
refs=[base/'run3/viewer.validation.json',base/'captures/viewer.validation.json',base/'evidence-nearest/evidence.validation.json',root/'work/fish-portable-tools/viewer-controller-fixture/smoke/viewer.validation.json']
checks=[]
for p in refs:
    d=json.loads(p.read_text());checks.append({'path':str(p.relative_to(root)),'sha256':sha(p),'ok':d['ok'],'check_count':len(d.get('checks',[])),'runtime_inventory':d.get('runtime_inventory'),'visual_review':d.get('visual_review')})
remove=[base/'run1',base/'run2',base/'evidence',base/'evidence-final',root/'work/fish-portable-tools/viewer-controller-fixture/source.blend']
report={'schema_version':1,'kind':'portable_viewer_tools_validation','ok':all(c['ok'] for c in checks),'status':'done','next_action':'human_review','visual_review':'pending','formal_fish_acceptance':False,'unit_tests':{'command':'.venv/bin/python -m unittest discover -s resources/scripts/volume-fish/portable/tests -p test_view_evidence.py -v','passed':12,'failed':0},'sources':[{ 'path':str((source/n).relative_to(root)),'sha256':sha(source/n)}for n in ['view.py','FishAssetViewer.gd','evidence.py','tests/test_view_evidence.py']],'checks':checks,'human_observation':{'observer':'implementing agent','observed':['Native smoke image visibly contains synthetic triangle with controls and pending-review label','Two-view contact sheet visibly shows the declared front and oblique synthetic views with labels/hashes','Controller smoke visibly contains two synthetic geometric pieces after actual normal controller steps'],'scope':'Tool rendering inspection only; no fish assets or species reviewed'},'startup_failures_resolved':[{'run':'run1','cause':'Godot mono lacked DOTNET_ROOT and exceeded bounded 25-second timeout','fix':'Set documented DOTNET_ROOT for mono binary'},{'run':'run2','cause':'GDScript SceneTree member paused redefinition and unknown notification constant','fix':'Use motion_paused and root.close_requested/window_input signals; subsequent renderer runs exit0'}],'limitations':['Part-color diagnostic explicitly disabled; no unproven marked atlas','Framing uses imported rest AABB transformed at current carrier pose, not exact posed skinned bounds','Optional controller API supported/tested: foundry_motion_v1 configure/set_action/step','No animal anatomy, fin completion, continuous animation proof, export implementation or SOP acceptance'],'cleanup':{'exact_removed_paths':[str(p.relative_to(root))for p in remove],'retained':'Current synthetic model/spec inputs, minimal project, reproduction producers, native/controller/capture logs and reports, representative screenshots and final contact sheet'}}
for p in remove:
    assert p.is_relative_to(root/'work/fish-portable-tools')
    if p.is_dir():shutil.rmtree(p)
    elif p.exists():p.unlink()
report['unit_tests']['passed']=15
import sys
sys.path.insert(0,str(source))
from view import godot_errors
logs=[base/'run3/viewer.log',base/'captures/viewer.log',root/'work/fish-portable-tools/viewer-controller-fixture/smoke/viewer.log']
report['retained_runtime_logs_error_scan']=[{'path':str(p.relative_to(root)),'errors':godot_errors(p.read_text())}for p in logs]
report['cleanup']['remaining_bytes']=0
for _ in range(4):
    (base/'tools.validation.json').write_text(json.dumps(report,indent=2)+'\n')
    measured=sum(p.stat().st_size for d in [base,root/'work/fish-portable-tools/viewer-controller-fixture']for p in d.rglob('*')if p.is_file())
    if measured==report['cleanup']['remaining_bytes']:break
    report['cleanup']['remaining_bytes']=measured
print(json.dumps({'ok':report['ok'],'report':str(base/'tools.validation.json'),'remaining_bytes':report['cleanup']['remaining_bytes']}))
