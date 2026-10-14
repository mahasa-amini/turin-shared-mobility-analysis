"""Recheck recorded cleaning evidence against local originals and staged archives."""
import csv
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent
RUN = EVIDENCE / 'run'
spec = importlib.util.spec_from_file_location('reproduction', ROOT / 'scripts/reproduce_cleaning.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def main():
    comparisons = json.loads((RUN / 'comparisons.json').read_text())
    assert len(comparisons) == 14
    assert all(v['actual_sha256'] == v['reference_sha256'] for v in comparisons.values())
    assert all(c['actual_dtype'] == c['reference_dtype'] and c['null_masks_equal']
               and c['unequal_nonnull'] == 0 and c.get('max_abs_difference', 0) == 0
               for v in comparisons.values() for c in v['columns'].values())
    originals = json.loads((RUN / 'original-hashes.json').read_text())
    assert all(module.digest(ROOT / p) == v['sha256'] for p, v in originals.items())
    sources = json.loads((RUN / 'source-hashes.json').read_text())
    assert all(module.digest(ROOT / p) == v['sha256'] for p, v in sources.items())
    with (EVIDENCE / 'distribution-manifest.csv').open() as stream:
        package = list(csv.DictReader(stream))
    raw = json.loads((RUN / 'input-hashes.json').read_text())
    assert all(next(r['sha256'] for r in package if r['path'] == p) == v['sha256']
               for p, v in raw.items())
    assert len(package) == 58
    sizes = json.loads((EVIDENCE / 'distribution-sizes.json').read_text())
    staged = ROOT / 'data/distribution-staging/2026-10-14'
    assert all(module.digest(staged / (part + '.tar.gz')) == sizes[part]['archive_sha256']
               for part in ['owner-scooter', 'external-review', 'runtime-config'])
    def versions(text):
        return {name.lower().replace('_', '-'): version
                for line in text.splitlines() if '==' in line and not line.startswith('#')
                for name, version in [line.split('==', 1)]}
    installed = versions((RUN / 'environment.txt').read_text())
    locked = versions((ROOT / 'requirements-lock.txt').read_text())
    assert all(installed.get(k) == v for k, v in locked.items())
    report = {'parquet_files_byte_equal': 14,
              'columns_compared': sum(len(v['columns']) for v in comparisons.values()),
              'all_dtypes_and_values_exact': True,
              'original_files_rechecked_unchanged': len(originals),
              'executed_source_files_unchanged': len(sources),
              'raw_inputs_match_package': len(raw), 'package_payload_files': 58,
              'all_archive_checksums_match': True, 'installed_packages_match_lock': len(locked)}
    (EVIDENCE / 'final-checks.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
