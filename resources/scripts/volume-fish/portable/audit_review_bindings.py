"""Read-only integrity audit of a production ledger and its frozen file inputs.

This verifies bytes and evidence bindings, never geometry or visual acceptance.
"""
import argparse,json
from pathlib import Path
from parts import read,sha

def audit(review,plans):
    ledger=read(review);failures=[];checked={}
    def check(path,digest):
        p=Path(path).resolve()
        if str(p) in checked:
            if checked[str(p)]!=digest:failures.append({'path':str(p),'error':'Conflicting expected hashes'})
            return
        checked[str(p)]=digest
        if not p.is_file()or sha(p)!=digest:failures.append({'path':str(p),'error':'Missing or changed'})
    for row in ledger['candidate_files'].values():check(row['path'],row['sha256'])
    bound={k:v['sha256']for k,v in ledger['candidate_files'].items()}
    for key,row in ledger['evidence'].items():
        check(row['path'],row['sha256'])
        if row['bound_inputs']!=bound:failures.append({'evidence':key,'error':'Stale candidate bindings'})
    def frozen(node):
        if isinstance(node,dict):
            for key,value in node.items():
                if key=='frozen_inputs':
                    for path,digest in value.items():check(path,digest)
                else:frozen(value)
        elif isinstance(node,list):
            for value in node:frozen(value)
    for plan in plans:frozen(read(plan))
    return {'ok':not failures,'kind':'production_review_byte_integrity','review':str(Path(review).resolve()),'review_sha256':sha(review),'evidence_count':len(ledger['evidence']),'checked_files':len(checked),'failures':failures,'scope':'Current candidate/evidence/frozen byte identity only; no new physical or visual acceptance.'}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--review',type=Path,required=True);p.add_argument('--plan',type=Path,action='append',default=[]);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    r=audit(a.review,a.plan);assert not a.output.exists();a.output.write_text(json.dumps(r,indent=2)+'\n',encoding='utf8');print(json.dumps(r));raise SystemExit(0 if r['ok']else 1)
