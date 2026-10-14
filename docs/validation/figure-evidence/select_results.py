from pathlib import Path
import pandas as pd,geopandas as gpd,numpy as np,json,shutil,hashlib
b=Path('/private/tmp/transport-showcase'); p=b/'project'; r=Path('/Users/mahasaamini/Documents/transport_exercise'); out=r/'docs/results'; out.mkdir(exist_ok=True)
manifest=[]
def copy(rel,name):
 f=p/rel; dest=out/name; shutil.copy2(f,dest); manifest.append(dict(path=str(dest.relative_to(r)),source=rel,method='byte-for-byte copy',sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
def table(df,name,source,method):
 dest=out/name;df.to_csv(dest,index=False); manifest.append(dict(path=str(dest.relative_to(r)),source=source,method=method,sha256=hashlib.sha256(dest.read_bytes()).hexdigest()))
copy('outputs/tables/exercise_1/hourly/system_hourly_weekday_2024_common.csv','temporal_hour_weekday_2024.csv')
copy('outputs/tables/exercise_1/hourly/system_hourly_profile_2024_common.csv','temporal_hourly_2024.csv')
copy('outputs/tables/exercise_1/temporal/temporal_coverage_registry.csv','temporal_coverage.csv')
copy('outputs/tables/exercise_4/parking_by_zone/parking_by_zone_system_pooled_2024.csv','parking_zone_pooled_2024.csv')
copy('audit/exercise_4/parking/final_parking_event_summary_2024.csv','parking_event_summary_2024.csv')
copy('outputs/tables/exercise_5/costs/base_case_profitability_2024.csv','economics_base_scenario_2024.csv')
copy('audit/exercise_3/route_overlap/direct_route_frequency_100m.csv','pt_route_mentions_100m.csv')
pt=pd.read_csv(p/'audit/exercise_3/route_overlap/route_aware_classification_summary.csv');pt=pt[pt.threshold_m==100].copy();table(pt,'pt_classes_100m.csv','audit/exercise_3/route_overlap/route_aware_classification_summary.csv','filter threshold_m == 100')
system=pt[pt.operator.isin(['bird','lime','voi'])].groupby(['season','interaction_class'],as_index=False).trips.sum(); totals=system.groupby('season').trips.sum();system['total_trips']=system.season.map(totals);system['share_pct']=100*system.trips/system.total_trips;table(system,'pt_system_100m.csv','audit/exercise_3/route_overlap/route_aware_classification_summary.csv','threshold 100 m; sum bird/lime/voi counts by season/class (exclude existing system rows); divide by season total')
f=p/'data/processed/exercise_2/gis/exercise2_od_layers.gpkg';print('LAYERS',gpd.list_layers(f).name.tolist())
flows=gpd.read_file(f,layer='flows_all_day');print(flows.columns.tolist())
core=flows.loc[flows.demand_core_25pct.fillna(False)].copy()
table(pd.DataFrame(core[['origin_zone_id','destination_zone_id','origin_zone_name','destination_zone_name','system_trips','flow_rank','cumulative_flow_share_pct']]),'od_displayed_core_2024.csv','data/processed/exercise_2/gis/exercise2_od_layers.gpkg:flows_all_day','filter demand_core_25pct; retain displayed directional zone pairs and counts')
copy('outputs/tables/exercise_2/od/od_structural_summary_2024.csv','od_structural_summary_2024.csv')
heat=pd.read_csv(out/'temporal_hour_weekday_2024.csv'); hourly=pd.read_csv(out/'temporal_hourly_2024.csv')
assert heat.system_trips.sum()==hourly.system_trips.sum()
expected=pt[pt.operator=='system'].set_index(['season','interaction_class']).sort_index()
actual=system.set_index(['season','interaction_class']).sort_index()
np.testing.assert_array_equal(actual.trips,expected.trips)
np.testing.assert_array_equal(actual.total_trips,expected.total_trips)
np.testing.assert_allclose(heat.mean_system_trips_per_weekday_occurrence_at_hour,heat.system_trips/heat.weekday_occurrences)
assert heat.groupby('weekday_number').weekday_occurrences.first().sum()==335
pe=pd.read_csv(out/'parking_event_summary_2024.csv'); zones=pd.read_csv(out/'parking_zone_pooled_2024.csv'); assert pe.valid_parking_events.sum()==zones.parking_events.sum()
np.testing.assert_allclose(zones.parking_events,zones[['bird_parking_events','lime_parking_events','voi_parking_events']].sum(axis=1))
np.testing.assert_allclose(zones.mean_parking_h,zones.mean_parking_min/60)
econ=pd.read_csv(out/'economics_base_scenario_2024.csv'); np.testing.assert_allclose(econ.operating_profit_proxy_eur,econ.estimated_gross_payg_revenue_eur-econ.primary_total_cost_eur)
np.testing.assert_allclose(econ.primary_total_cost_eur,econ.direct_vehicle_opex_eur+econ.market_overhead_including_insurance_eur+econ.annual_depreciation_eur)
np.testing.assert_allclose(system.groupby('season').share_pct.sum(),100)
od=pd.read_csv(p/'outputs/tables/exercise_2/od/od_system_2024_long.csv'); assert od.system_trips.sum()==1681927
assert core.system_trips.sum()/flows.system_trips.sum()>=.25
assert (core.system_trips.sum()-core.system_trips.min())/flows.system_trips.sum()<.25
summary=dict(temporal_trips=int(heat.system_trips.sum()),temporal_days=335,temporal_peak=heat.loc[heat.mean_system_trips_per_weekday_occurrence_at_hour.idxmax()].to_dict(),system_peak_hour=int(hourly.loc[hourly.system_trips.idxmax(),'hour']),od_valid_trips=int(od.system_trips.sum()),od_interzonal_trips=int(flows.system_trips.sum()),od_displayed_trips=int(core.system_trips.sum()),od_displayed_pairs=len(core),od_displayed_share_pct=100*float(core.system_trips.sum()/flows.system_trips.sum()),pt_direct=system[system.interaction_class=='Direct PT-route overlap candidate'].to_dict('records'),parking_candidates=int(pe.candidate_events.sum()),parking_valid=int(pe.valid_parking_events.sum()),parking_mean_h=float((zones.mean_parking_h*zones.parking_events).sum()/zones.parking_events.sum()),economics=econ[['operator','trips','estimated_gross_payg_revenue_eur','primary_total_cost_eur','operating_profit_proxy_eur','operating_margin_pct']].to_dict('records'))
(b/'headline-checks.json').write_text(json.dumps(summary,indent=2)+'\n');(b/'selected-tables.json').write_text(json.dumps(manifest,indent=2)+'\n'); print(json.dumps(summary,indent=2))
