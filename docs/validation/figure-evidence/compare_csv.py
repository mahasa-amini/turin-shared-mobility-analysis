from pathlib import Path
import pandas as pd,json
r=Path('/Users/mahasaamini/Documents/transport_exercise'); b=Path('/private/tmp/transport-showcase'); p=b/'project'; results=[]
for folder in ['audit','outputs/tables']:
 for f in sorted((p/folder).rglob('*.csv')):
  if str(f.relative_to(p)) in {x['path'] for x in json.loads((b/'input-manifest.json').read_text())}: continue
  ref=r/f.relative_to(p)
  if not ref.exists(): results.append(dict(path=str(f.relative_to(p)),status='no historical reference')); continue
  a=pd.read_csv(f); c=pd.read_csv(ref)
  try:
   pd.testing.assert_frame_equal(a,c,check_exact=False,rtol=1e-10,atol=1e-9)
   status='match'
  except AssertionError as e: status=str(e)
  results.append(dict(path=str(f.relative_to(p)),rows=len(a),columns=len(a.columns),status=status))
(b/'csv-comparisons.json').write_text(json.dumps(results,indent=2)+'\n')
print('Compared',len(results),'tables'); print([x for x in results if x['status']!='match'])
