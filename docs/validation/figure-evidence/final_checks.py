from pathlib import Path
import json,hashlib,ast
r=Path('/Users/mahasaamini/Documents/transport_exercise'); d=r/'docs/validation/figure-evidence'
for name in ['selected-figures.json','selected-tables.json']:
 for x in json.loads((d/name).read_text()):assert hashlib.sha256((r/x['path']).read_bytes()).hexdigest()==x['sha256'],x['path']
for name,digest in json.loads((d/'source-hashes.json').read_text()).items():assert hashlib.sha256((r/name).read_bytes()).hexdigest()==digest,name
for x in json.loads((d/'csv-comparisons.json').read_text()):assert x['status']=='match',x
for p in [*r.glob('stage*.py'),*r.glob('src/**/*.py')]:ast.parse(p.read_text())
print('Selected artifact hashes, all executed source hashes, CSV matches, and Python syntax passed.')
