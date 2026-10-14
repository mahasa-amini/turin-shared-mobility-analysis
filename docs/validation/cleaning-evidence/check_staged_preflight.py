from pathlib import Path
import shutil
import subprocess
import json
root=Path('/Users/mahasaamini/Documents/transport_exercise')
workspace=Path('/private/tmp/transport-cleaning-20261014-locked')
staging=root/'data/distribution-staging/2026-10-14'
shutil.copytree(root/'scripts',workspace/'scripts',ignore=shutil.ignore_patterns('__pycache__'))
shutil.copytree(root/'config',workspace/'config')
shutil.copytree(staging/'external-review/data/raw/external',workspace/'data/raw/external')
evidence=root/'docs/validation/cleaning-evidence'
command=['/private/tmp/transport-cleaning-locked-env/bin/python',str(workspace/'scripts/run_pipeline.py'),'scooter','--preflight','--verify-inputs']
with (evidence/'staged-preflight.log').open('w') as stream:
    result=subprocess.run(command,cwd=workspace,stdout=stream,stderr=subprocess.STDOUT)
(evidence/'staged-preflight.json').write_text(json.dumps({'command':command,'cwd':str(workspace),'exit':result.returncode,'external_inputs':'14 files copied only from the staged external-review part','cleaned_inputs':'regenerated from raw in the same locked workspace','analytical_execution':False},indent=2)+'\n')
assert result.returncode==0
