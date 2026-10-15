"""Run production preparation on exclusively SYNTHETIC fixtures in a disposable root."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import pandas as pd
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / 'examples/synthetic'
STEPS = [
    'cleaning/clean_bird.py', 'cleaning/finalize_bird.py',
    'cleaning/audit_lime.py', 'cleaning/finalize_lime.py',
    'cleaning/audit_voi.py', 'cleaning/finalize_voi.py',
    'harmonization/harmonize_operators.py',
]
INPUTS = {
    'bird_2024.csv': 'bird/Bird Torino - 2024 - Sheet1.csv',
    'bird_2025.csv': 'bird/Bird Torino - 2025 (fino il 18_11_2025) - Sheet1.csv',
    'lime_2024-03.csv': 'lime/Torino_Corse24-25_2024-03_senza_percorso.csv',
    'lime_2024-10.csv': 'lime/Torino_Corse24-25_2024-10_senza_percorso.csv',
    'lime_2025-07.csv': 'lime/Torino_Corse24-25_2025-07_senza_percorso.csv',
    'voi_2024-01.csv': 'voi/SYNTHETIC_DATINOLEGGI_202401.xlsx',
    'voi_2025-07.csv': 'voi/SYNTHETIC_DATINOLEGGI_202507.xlsx',
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_cells(frame, key, cases, label):
    require(frame[key].is_unique, f'{label}: duplicate case keys')
    indexed = frame.set_index(key)
    for case, fields in cases.items():
        require(case in indexed.index, f'{label}: missing {case}')
        for field, expected in fields.items():
            value = indexed.loc[case, field]
            if expected is None:
                equal = pd.isna(value)
            elif isinstance(expected, str) and isinstance(value, pd.Timestamp):
                equal = value == pd.Timestamp(expected)
            else:
                equal = pd.notna(value) and value == expected
            require(equal, f'{label}/{case}/{field}: {value!r} != {expected!r}')


def verify(workspace):
    expected = json.loads((FIXTURES / 'expected.json').read_text())
    spec = importlib.util.spec_from_file_location(
        'synthetic_harmonization', workspace / 'src/harmonization/harmonize_operators.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    harmonized = workspace / 'data/processed/harmonized'
    for name, checks in expected.items():
        operator, year = name.split('_')
        raw_rows = 0
        for relative in INPUTS.values():
            if not relative.startswith(operator + '/'):
                continue
            path = workspace / 'data/raw' / relative
            # The production filename conventions identify annual/monthly fixtures.
            if year not in path.name:
                continue
            raw = pd.read_excel(path) if path.suffix == '.xlsx' else pd.read_csv(path)
            raw_rows += len(raw)
        require(raw_rows == checks['raw_rows'], f'{name}: raw count')
        clean = pd.read_parquet(workspace / f'data/cleaned/{operator}/{name}_clean.parquet')
        require(len(clean) == checks['rows'], f'{name}: cleaned count')
        key = 'Targa veicolo' if operator == 'voi' else 'ID_VEICOLO'
        require(set(clean[key]) == set(checks['clean']), f'{name}: retained case identities')
        check_cells(clean, key, checks['clean'], name + '/clean')
        path = harmonized / f'{name}_harmonized.parquet'
        h = pd.read_parquet(path)
        require(len(h) == len(clean), f'{name}: harmonized count')
        require(pq.read_schema(path).equals(module.CANONICAL_ARROW_SCHEMA), f'{name}: Arrow schema')
        require(h.trip_uid.is_unique and h.trip_uid.notna().all(), f'{name}: trip identity')
        require(set(h.vehicle_id) == set(checks['clean']), f'{name}: harmonized identities')
        require(h.source_file.notna().all() and (h.source_row > 0).all(), f'{name}: lineage')
        if operator in ('bird', 'lime'):
            require(h.start_time_utc.isna().all() and h.end_time_utc.isna().all(), f'{name}: UTC invented')
        check_cells(h, 'vehicle_id', checks['harmonized'], name + '/harmonized')
        print(f'  {name}: {checks["raw_rows"]} raw -> {len(clean)} cleaned -> {len(h)} harmonized')
    for year in (2024, 2025):
        path = harmonized / f'all_operators_{year}_harmonized.parquet'
        combined = pd.read_parquet(path)
        parts = pd.concat([pd.read_parquet(harmonized / f'{op}_{year}_harmonized.parquet')
                           for op in ('bird', 'lime', 'voi')], ignore_index=True)
        require(pq.read_schema(path).equals(module.CANONICAL_ARROW_SCHEMA), f'{year}: pooled schema')
        pd.testing.assert_frame_equal(combined.reset_index(drop=True), parts.reset_index(drop=True))
        require(combined.trip_uid.is_unique, f'{year}: pooled identities')
    require(len(list((workspace / 'data/cleaned').rglob('*.parquet'))) == 6, 'Six cleaned outputs required')
    require(len(list(harmonized.glob('*.parquet'))) == 8, 'Eight harmonized outputs required')


def main():
    if sys.flags.optimize:
        raise RuntimeError('Run without -O: production quality assertions must remain enabled')
    print('SYNTHETIC preparation demo — no real trip inputs', flush=True)
    with tempfile.TemporaryDirectory(prefix='transport-SYNTHETIC-') as temp:
        workspace = Path(temp)
        for step in STEPS:
            target = workspace / 'src' / step
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / 'src' / step, target)
        for source, relative in INPUTS.items():
            target = workspace / 'data/raw' / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.suffix == '.xlsx':
                # Human-readable synthetic CSV -> native provider input format.
                frame = pd.read_csv(FIXTURES / source, dtype=str, keep_default_na=False)
                frame.to_excel(target, index=False, engine='openpyxl')
            else:
                shutil.copy2(FIXTURES / source, target)
        for step in STEPS:
            result = subprocess.run([sys.executable, str(workspace / 'src' / step)],
                                    cwd=workspace, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(f'{step} failed:\n{result.stdout}\n{result.stderr}')
            print(f'  PASS {step}', flush=True)
        verify(workspace)
    print('PASS: expected cases, counts, masks, times, lineage and 45-field schema; temporary outputs removed')


if __name__ == '__main__':
    main()
