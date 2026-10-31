"""Bind an operator's source-zone review; never infer material semantics."""
from pathlib import Path
from fish_asset_spec import ROOT,resolve_ref,require
from parts import read,sha

def check_reference_review(author_file):
    cfg=read(author_file)
    if 'material_reference_review' not in cfg:return None
    report_file=resolve_ref(cfg['material_reference_review']);report=read(report_file)
    require(report.get('kind')=='source_surface_material_review' and report.get('ok')is True and report.get('status')=='operator_reviewed','Material source-zone review is not complete')
    source=(ROOT/cfg['source']).resolve()
    require(sha(source)==cfg['source_sha256']==report.get('source_sha256'),'Material review source mismatch')
    reference=resolve_ref(cfg['front_color_image']);digest=sha(reference)
    require(digest==report.get('reference_sha256') and digest not in report.get('rejected_reference_sha256',[]),'Material reference is rejected or differs from reviewed image')
    if cfg.get('interocular_material'):
        require(sha(resolve_ref(cfg['interocular_material']['image']))==digest,'Central material differs from reviewed reference')
    zones=report.get('zones',[])
    require(bool(zones)and all(isinstance(z,dict)and z.get('source_observation','').strip()and z.get('reference_observation','').strip()and z.get('adopted_scope','').strip()for z in zones),'Actual source/reference material-zone observations required')
    evidence=report.get('comparison_evidence',[])
    require(bool(evidence),'Material source comparison evidence required')
    for ref in evidence:resolve_ref(ref)
    return {'ok':True,'report':{'path':str(report_file),'sha256':sha(report_file)},'reference_sha256':digest,'scope':'Binds a separately recorded actual source-zone review and rejects known bad references. Does not recognize scales or approve appearance automatically.'}
