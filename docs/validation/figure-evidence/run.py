from pathlib import Path
import subprocess,os,json,time
b=Path('/private/tmp/transport-showcase'); p=b/'project'; py='/private/tmp/transport-showcase-env/bin/python'
seq=['src/harmonization/harmonize_operators.py']
groups={1:'cleaning_impact temporal_coverage daily_trends weekly_trends monthly_trends yearly_comparison usage_patterns hourly_weekday vehicle_utilization',2:'zoning_audit assign_zones build_od temporal_od temporal_flow_contrasts prepare_gis',3:'prepare_pt_reference pt_proximity route_overlap temporal_adduction prepare_gis',4:'parking_interval_audit parking_definition_sensitivity finalize_parking_events zone_parking_statistics temporal_parking_statistics od_parking_relationship',5:'cost_assumption_audit revenue_engine fleet_exposure_audit revenue_diagnostics cost_profitability_engine robustness_vat_sensitivity'}
for n,names in groups.items(): seq += [f'src/analysis/exercise{n}_{s}.py' for s in names.split()]
figs=sorted([str(f.relative_to(p)) for f in (p/'src/analysis').glob('*.py') if 'figures' in f.name or 'map' in f.name])+sorted(str(f.relative_to(p)) for f in (p/'src/visualization').glob('*.py'))
(b/'figure-scripts.json').write_text(json.dumps(figs,indent=2))
env=dict(os.environ,MPLBACKEND='Agg',MPLCONFIGDIR=str(b/'mplcache'))
records=[]
for kind,scripts in [('prerequisite',seq),('figure',figs)]:
 for script in scripts:
  log=b/(Path(script).stem+'.log'); command=[py,'-I','-B','-u',str(p/script)]; t=time.time()
  with log.open('w') as out:r=subprocess.run(command,cwd=p,env=env,stdout=out,stderr=subprocess.STDOUT)
  records.append(dict(kind=kind,script=script,command=command,exit=r.returncode,seconds=round(time.time()-t,2),log=log.name))
  (b/'execution.json').write_text(json.dumps(records,indent=2))
  print(kind,script,r.returncode,round(time.time()-t,1),flush=True)
  if r.returncode and kind=='prerequisite': raise SystemExit(r.returncode)
