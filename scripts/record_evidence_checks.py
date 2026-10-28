"""Capture actual validation output for the course report; never invent pass results."""
import json
import subprocess
import sys
import time
from pathlib import Path
from inspect_data import ROOT


def main():
    output=ROOT/'reports/evidence';output.mkdir(parents=True,exist_ok=True)
    commands=[([sys.executable,'-m','pytest','-q'],'python -m pytest -q'),
              ([sys.executable,'scripts/verify_artifacts.py'],'python scripts/verify_artifacts.py')]
    records=[]
    for command,display in commands:
        if command[-1]=='scripts/verify_artifacts.py' and not (ROOT/'frontend/dist/index.html').exists():
            records.append({'command':display,'exit_code':None,'status':'not_run','seconds':0,'stdout':'','stderr':'Frontend production build is absent. Run npm run build in frontend before the full artifact check.'})
            continue
        start=time.monotonic();result=subprocess.run(command,cwd=ROOT,text=True,capture_output=True)
        records.append({'command':display,'exit_code':result.returncode,'status':'passed' if result.returncode==0 else 'failed',
                        'seconds':round(time.monotonic()-start,3),'stdout':result.stdout,'stderr':result.stderr})
        print(display,'exit',result.returncode)
    (output/'12_verification_runs.json').write_text(json.dumps(records,ensure_ascii=False,indent=2))
    (output/'12_verification_runs.txt').write_text('\n\n'.join('$ '+record['command']+'\n'+record['stdout']+record['stderr']+'\nStatus: '+record['status']+'\nExit code: '+str(record['exit_code']) for record in records))
    if any(record['status']=='failed' for record in records):raise SystemExit('A validation command failed; inspect 12_verification_runs.txt')

if __name__=='__main__':main()
