"""Check Stage 5's manual costs before it runs; never rewrite model assumptions."""

import ast
import contextlib
import io
import json
from pathlib import Path
import runpy

ROOT = Path(__file__).resolve().parents[1]
PAIRS = [('private_car_cost', 'round_trip_total_eur', 2),
         ('private_bike_cost', 'bike_cost_per_university_day_eur', 3),
         ('private_scooter_cost', 'scooter_cost_per_university_day_eur', 3)]


def check(root=ROOT):
    values = {}
    for script in ['stage4_private_car.py', 'stage4_private_active_modes.py']:
        with contextlib.redirect_stdout(io.StringIO()):
            values.update(runpy.run_path(str(root / script)))
    tree = ast.parse((root / 'stage5_generalised_cost.py').read_text())
    names = {name for name, _, _ in PAIRS}
    embedded = {node.targets[0].id: ast.literal_eval(node.value)
                for node in tree.body if isinstance(node, ast.Assign)
                and isinstance(node.targets[0], ast.Name) and node.targets[0].id in names}
    return [dict(stage5_variable=name, stage4_value=values[key],
                 stage5_embedded=embedded[name], decimals=places,
                 consistent=round(values[key], places) == embedded[name])
            for name, key, places in PAIRS]


if __name__ == '__main__':
    results = check()
    print(json.dumps(results, indent=2))
    if not all(row['consistent'] for row in results):
        raise SystemExit('Manual Stage 4→5 handoff is inconsistent; calculations were not changed.')
