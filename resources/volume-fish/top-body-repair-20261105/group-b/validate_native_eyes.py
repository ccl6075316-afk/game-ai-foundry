"""Portable077 unchanged body/opaque/GPU nucleus with native ordinary eyes."""
import sys,hashlib
from pathlib import Path
ROOT=next(p for p in Path(__file__).resolve().parents if(p/'cli/gamefactory.py').exists());PORTABLE=ROOT/'resources/scripts/volume-fish/portable';SCRIPTS=PORTABLE.parent;BASE_CHECKER_PATH=PORTABLE/'validate_standalone_body.py';GUARD=Path(__file__).with_name('native_eye_support_guard.py');sys.path[:0]=[str(PORTABLE),str(SCRIPTS),str(Path(__file__).parent)]
source=BASE_CHECKER_PATH.read_text();start=source.index('    overlay_proofs=[]');end=source.index('    bodies=[n for n in mesh_nodes');kernel=source[end:source.index('\n\ndef missing_pixels')];source=source[:start]+'''    from native_eye_support_guard import verify
    overlay_proofs=[]
    for name,definition in overlays.items():
        node=next(n for n in mesh_nodes if n['name']==name)
        assert 'skin'in node
        overlay_proofs.append(verify(doc,blob,plan,node,definition))
'''+source[end:]
source=source.replace("capture=Path(__file__).with_name('capture_standalone_body.gd')","capture=PORTABLE/'capture_standalone_body.gd'").replace("Path(__file__).parent.parent/'freeze_surface_ownership.py'","SCRIPTS/'freeze_surface_ownership.py'").replace("Path(__file__).parent.parent/'validate_body_integrity.py'","SCRIPTS/'validate_body_integrity.py'").replace("Path(__file__).with_name('logical_document.py')","PORTABLE/'logical_document.py'").replace("Path(__file__).with_name('PackedFishParts.gd')","PORTABLE/'PackedFishParts.gd'").replace("for p in [Path(__file__),capture,","for p in [Path(__file__),BASE_CHECKER_PATH,GUARD,capture,")
source=source.replace("result.update(plan_sha256=sha(plan_path),checker_sha256=sha(__file__),","result.update(base_checker_sha256=sha(BASE_CHECKER_PATH),body_kernel_sha256=hashlib.sha256(kernel.encode()).hexdigest(),adapter_scope='Unchanged portable077 body/opaque/GPU; ordinary native physical eye identity, open/closed inventory and actual finite-body mixed skin',plan_sha256=sha(plan_path),checker_sha256=sha(__file__),")
assert source[source.index('    bodies=[n for n in mesh_nodes'):source.index('\n\ndef missing_pixels')]==kernel
exec(compile(source,str(Path(__file__).resolve()),'exec'))
