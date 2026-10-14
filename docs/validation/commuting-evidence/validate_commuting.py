from pathlib import Path
import pandas as pd,numpy as np,json,hashlib
b=Path('/private/tmp/transport-showcase'); p=b/'commuting'; t=p/'outputs/tables/generalised_cost'
a=pd.read_csv(t/'stage5_master_modes.csv').set_index('mode'); baseline=pd.read_csv(t/'stage5_baseline_generalised_cost.csv').set_index('mode'); s=pd.read_csv(t/'stage5_vot_sensitivity.csv'); w=pd.read_csv(t/'stage6_weighted_generalised_cost.csv').set_index('mode'); q=pd.read_csv(t/'stage6_pareto_efficiency.csv').set_index('mode'); pt=pd.read_csv(t/'stage6_pt_cost_sensitivity.csv')
checks=[]
def equal(x,y,label):
 np.testing.assert_allclose(x,y,rtol=1e-10,atol=1e-9); checks.append(label)
assert len(a)==9 and a.index.is_unique
assert (a.select_dtypes('number')>=0).all().all()
equal(a.total_time_min,a[['travel_min','access_egress_min','waiting_min']].sum(axis=1),'Stage 5 time components, 9 modes')
equal(a.time_cost_eur,a.total_time_min/6,'Stage 5 time valuation at EUR 10/h')
equal(a.generalised_cost_eur,a.monetary_cost_eur+a.total_time_min/6,'Stage 5 GC accounting')
equal(a.gc_rank,a.generalised_cost_eur.rank(method='min'),'Stage 5 ranks')
pd.testing.assert_frame_equal(a.sort_index(),baseline.sort_index()); checks.append('Stage 5 baseline equals master, sorted by GC')
assert baseline.generalised_cost_eur.is_monotonic_increasing
assert len(s)==27 and set(s.vot_eur_hour)=={5,10,20} and not s.duplicated(['mode','vot_eur_hour']).any()
for vot,g in s.groupby('vot_eur_hour'):
 g=g.set_index('mode').loc[a.index]; equal(g.generalised_cost_eur,a.monetary_cost_eur+a.total_time_min*vot/60,f'Stage 5 sensitivity EUR {vot}/h, all modes'); equal(g['rank'],g.generalised_cost_eur.rank(method='min'),f'Sensitivity ranks EUR {vot}/h')
w=w.loc[a.index]; equal(w.perceived_time_min,a.travel_min+1.5*a.access_egress_min+2*a.waiting_min,'Stage 6 perception weights 1/1.5/2')
equal(w.weighted_generalised_cost_eur,a.monetary_cost_eur+w.perceived_time_min/6,'Stage 6 weighted GC')
equal(w.weighted_gc_rank,w.weighted_generalised_cost_eur.rank(method='min'),'Stage 6 ranks')
x=a[['monetary_cost_eur','total_time_min']].to_numpy(); dominates=(x[:,None,:]<=x[None,:,:]).all(axis=2)&(x[:,None,:]<x[None,:,:]).any(axis=2)
assert np.array_equal(q.loc[a.index].pareto_efficient.to_numpy(),~dominates.any(axis=0)); checks.append('Stage 6 independent pairwise Pareto dominance, 81 pairs')
pr=a.loc['Public transport']; equal(pt.monetary_cost_eur,[190/150,0],'PT allocated/marginal scenarios'); equal(pt.standard_gc_eur,pt.monetary_cost_eur+pr.total_time_min/6,'PT standard GC scenarios'); equal(pt.weighted_gc_eur,pt.monetary_cost_eur+w.loc['Public transport'].perceived_time_min/6,'PT weighted GC scenarios')
from PIL import Image
figures=[]
for f in sorted((p/'outputs/figures').rglob('*.png')):
 with Image.open(f) as im: im.verify()
 with Image.open(f) as im: size=im.size
 figures.append(dict(path=str(f.relative_to(p)),size=size,sha256=hashlib.sha256(f.read_bytes()).hexdigest()))
assert len(figures)==3
result=dict(checks=checks,figures=figures,pareto_efficient=q[q.pareto_efficient].index.tolist(),baseline_winner=baseline.iloc[0].to_dict(),baseline_winner_mode=baseline.index[0])
(b/'commuting-checks.json').write_text(json.dumps(result,indent=2)); print(json.dumps(result,indent=2))
