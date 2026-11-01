"""Capture actual installed resources, reject engine errors, then run077 gate."""
import argparse,hashlib,json,subprocess,sys
from pathlib import Path
def main():
    p=argparse.ArgumentParser(description=__doc__)
    for k in ['game','godot','output','candidate-plan']:p.add_argument('--'+k,type=Path,required=True)
    p.add_argument('--species',nargs='*',default=[]);a=p.parse_args();scripts=Path(__file__).resolve().parent
    a.output.mkdir(parents=True,exist_ok=False)
    args=[str(a.godot),'--path',str(a.game),'--rendering-method','gl_compatibility','--quit-after','24000','--script',str(scripts/'validate_mouth_runtime139.gd'),'--',str(a.output),*a.species]
    try:
        r=subprocess.run(args,capture_output=True,text=True,encoding='utf8',errors='replace',timeout=1800)
        log=a.output/'runtime.log';log.write_text(r.stdout+r.stderr,encoding='utf8')
        assert r.returncode==0 and 'ERROR:' not in r.stdout+r.stderr and 'Broken external resource' not in r.stdout+r.stderr,'Runtime failed; see log'
        receipt=a.output/'runtime.validation.json';assert receipt.exists() and json.loads(receipt.read_text())['ok']
        run=subprocess.run([sys.executable,'-X','utf8',str(scripts/'validate_body_integrity.py'),'--game',str(a.game),'--godot',str(a.godot),'--output',str(a.output/'body-integrity'),'--mouth-runtime-report',str(receipt),'--mouth-candidate-plan',str(a.candidate_plan)],capture_output=True,text=True,encoding='utf8',errors='replace',timeout=240)
        (a.output/'body-integrity.log').write_text(run.stdout+run.stderr,encoding='utf8');assert run.returncode==0,'Actual body077 gate failed'
        result={'ok':True,'runtime_report_sha256':hashlib.sha256(receipt.read_bytes()).hexdigest(),'body_report_sha256':hashlib.sha256((a.output/'body-integrity/completion.validation.json').read_bytes()).hexdigest(),'scope':'Actual resources and077 technical gate; fin gates and visual review remain separate.'}
    except Exception as e:result={'ok':False,'error':str(e)}
    (a.output/'completion.validation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result),flush=True);return 0 if result['ok'] else 1
if __name__=='__main__':sys.exit(main())
