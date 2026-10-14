import runpy,ast,json,contextlib
from pathlib import Path
b=Path('/private/tmp/transport-showcase'); p=b/'commuting'
vals={}
for name in ['stage4_private_car','stage4_private_active_modes']:
 with (b/(name+'.log')).open('w') as f,contextlib.redirect_stdout(f): vals.update(runpy.run_path(str(p/(name+'.py'))))
source=ast.parse((p/'stage5_generalised_cost.py').read_text())
embedded={n.targets[0].id:ast.literal_eval(n.value) for n in source.body if isinstance(n,ast.Assign) and isinstance(n.targets[0],ast.Name) and n.targets[0].id in ['private_car_cost','private_bike_cost','private_scooter_cost']}
records=[]
for name,key,dp in [('private_car_cost','round_trip_total_eur',2),('private_bike_cost','bike_cost_per_university_day_eur',3),('private_scooter_cost','scooter_cost_per_university_day_eur',3)]:
 v=vals[key]; records.append(dict(stage5_variable=name,stage4_variable=key,stage4_value=v,stage5_embedded=embedded[name],decimals=dp,rounded_stage4=round(v,dp),consistent=round(v,dp)==embedded[name]))
(b/'commuting-handoff.json').write_text(json.dumps(records,indent=2)); print(json.dumps(records,indent=2))
