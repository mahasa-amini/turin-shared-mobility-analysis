"""Fresh raw-only reproduction; compare every cleaned column before harmonization."""
import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
STEPS = ['clean_bird', 'finalize_bird', 'audit_lime', 'finalize_lime', 'audit_voi', 'finalize_voi']


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def inventory(paths, root):
    return {str(p.relative_to(root)): {'bytes': p.stat().st_size, 'sha256': digest(p)}
            for p in sorted(paths) if p.is_file() and p.name != '.DS_Store'}


def compare_frames(actual, reference):
    if actual.shape != reference.shape or list(actual.columns) != list(reference.columns):
        raise ValueError('Row/column shape or column order differs')
    result = {}
    for col in actual:
        a, b = actual[col], reference[col]
        nulls_equal = a.isna().equals(b.isna())
        item = {'actual_dtype': str(a.dtype), 'reference_dtype': str(b.dtype),
                'nulls_actual': int(a.isna().sum()), 'nulls_reference': int(b.isna().sum()),
                'null_masks_equal': nulls_equal}
        valid = a.notna() & b.notna()
        x, y = a[valid], b[valid]
        if pd.api.types.is_datetime64_any_dtype(a.dtype):
            # Same instants/naive clock values, independent of storage resolution.
            equal = (x.astype('int64') == y.astype('int64')) if a.dtype == b.dtype else (x == y)
            item['comparison'] = 'exact timestamps'
        elif pd.api.types.is_numeric_dtype(a.dtype) and not pd.api.types.is_bool_dtype(a.dtype):
            # Integer identities/counts are exact. Floats allow only roundoff.
            floating = pd.api.types.is_float_dtype(a.dtype) and pd.api.types.is_float_dtype(b.dtype)
            equal = np.isclose(x, y, rtol=1e-12, atol=1e-12, equal_nan=True) if floating else x == y
            item['comparison'] = 'float rtol=atol=1e-12' if floating else 'exact numeric'
            item['max_abs_difference'] = float(np.abs(x.to_numpy() - y.to_numpy()).max()) if len(x) else 0.0
        else:
            equal = x.astype('string') == y.astype('string')
            item['comparison'] = 'exact logical strings/booleans'
        item['unequal_nonnull'] = int((~np.asarray(equal, dtype=bool)).sum())
        result[col] = item
        if not nulls_equal or item['unequal_nonnull']:
            raise ValueError(f'Material discrepancy in {col}: {item}')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workspace', type=Path, required=True, help='Must not exist')
    parser.add_argument('--evidence', type=Path, required=True, help='Must not exist')
    args = parser.parse_args()
    # Refuse environment drift before any dataset processing.
    for line in (ROOT / 'requirements-lock.txt').read_text().splitlines():
        if '==' in line and not line.startswith('#'):
            name, expected = line.split('==', 1)
            installed = importlib.metadata.version(name)
            if installed != expected:
                raise RuntimeError(f'Environment drift: {name}=={installed}, expected {expected}')
    if sys.flags.optimize:
        raise RuntimeError('Quality assertions require Python without optimization')
    workspace, evidence = args.workspace.resolve(), args.evidence.resolve()
    workspace.mkdir(parents=True, exist_ok=False)
    evidence.mkdir(parents=True, exist_ok=False)
    protected = [p for folder in ('data/raw', 'data/interim', 'data/cleaned', 'data/processed', 'audit', 'outputs') for p in (ROOT / folder).rglob('*')
                 if p.is_file() and workspace not in p.parents]
    before = inventory(protected, ROOT)
    (evidence / 'original-hashes.json').write_text(json.dumps(before, indent=2) + '\n')
    shutil.copytree(ROOT / 'src', workspace / 'src', ignore=shutil.ignore_patterns('__pycache__'))
    for op in ('bird', 'lime', 'voi'):
        shutil.copytree(ROOT / 'data/raw' / op, workspace / 'data/raw' / op,
                        ignore=shutil.ignore_patterns('.DS_Store'))
    sources = inventory((workspace / 'src').rglob('*.py'), workspace)
    (evidence / 'source-hashes.json').write_text(json.dumps(sources, indent=2) + '\n')
    inputs = inventory((workspace / 'data/raw').rglob('*'), workspace)
    (evidence / 'input-hashes.json').write_text(json.dumps(inputs, indent=2) + '\n')
    execution = {'interpreter': sys.executable, 'workspace': str(workspace), 'steps': []}
    def run(script):
        command = [sys.executable, str(workspace / script)]
        start = time.time()
        with (evidence / (Path(script).stem + '.log')).open('w') as log:
            code = subprocess.call(command, cwd=workspace, stdout=log, stderr=subprocess.STDOUT)
        execution['steps'].append({'command': command, 'cwd': str(workspace),
                                   'exit': code, 'seconds': time.time() - start})
        (evidence / 'execution.json').write_text(json.dumps(execution, indent=2) + '\n')
        if code:
            raise RuntimeError(f'{script} exited {code}; see evidence log')
    run_environment = subprocess.run([sys.executable, '-m', 'pip', 'freeze'], capture_output=True, text=True, check=True)
    (evidence / 'environment.txt').write_text(sys.version + '\n' + run_environment.stdout)
    run('src/cleaning/clean_bird.py')
    for step in STEPS[1:]:
        run(f'src/cleaning/{step}.py')
    comparisons = {}
    for path in sorted((workspace / 'data/cleaned').rglob('*.parquet')):
        relative = path.relative_to(workspace)
        actual, reference = pd.read_parquet(path), pd.read_parquet(ROOT / relative)
        comparisons[str(relative)] = {'rows': len(actual), 'columns': compare_frames(actual, reference),
                                     'actual_sha256': digest(path), 'reference_sha256': digest(ROOT / relative)}
        (evidence / 'comparisons.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    if len(comparisons) != 6:
        raise ValueError('Expected six cleaned datasets')
    run('src/harmonization/harmonize_operators.py')
    for path in sorted((workspace / 'data/processed/harmonized').glob('*.parquet')):
        relative = path.relative_to(workspace)
        actual, reference = pd.read_parquet(path), pd.read_parquet(ROOT / relative)
        comparisons[str(relative)] = {'rows': len(actual), 'columns': compare_frames(actual, reference),
                                     'actual_sha256': digest(path), 'reference_sha256': digest(ROOT / relative)}
    (evidence / 'comparisons.json').write_text(json.dumps(comparisons, indent=2) + '\n')
    if len(comparisons) != 14:
        raise ValueError('Expected six cleaned and eight harmonized datasets')
    after = inventory(protected, ROOT)
    (evidence / 'preservation.json').write_text(json.dumps({'files': len(before), 'unchanged': before == after}, indent=2) + '\n')
    if before != after:
        raise RuntimeError('Original artifacts changed')
    # Only aggregate audits are eligible for Git; row-level anomaly exports stay local.
    for op in ('bird', 'lime', 'voi'):
        for p in (workspace / 'audit' / op).glob('*.csv'):
            if (('summary' in p.name and 'duplicate_trip_id' not in p.name)
                    or p.name.endswith('_raw_audit.csv')):
                shutil.copy2(p, evidence / p.name)
    shutil.copy2(workspace / 'audit/harmonization/harmonization_data_dictionary.csv', evidence / 'harmonized_data_dictionary.csv')
    summary_comparisons = {}
    for op in ('bird', 'lime', 'voi'):
        name = f'{op}_final_cleaning_summary.csv'
        summary_comparisons[name] = compare_frames(pd.read_csv(evidence / name), pd.read_csv(ROOT / 'audit' / op / name))
    (evidence / 'summary-comparisons.json').write_text(json.dumps(summary_comparisons, indent=2) + '\n')
    print(f'PASS: {len(comparisons)} all-column comparisons; originals unchanged')


if __name__ == '__main__':
    main()
