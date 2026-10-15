"""Preflight original scooter inputs against the published snapshot manifest."""
import argparse
import csv
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / 'docs/validation/scooter-release-evidence/manifest.csv'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Extraction/repository root')
    parser.add_argument('--manifest', type=Path, default=MANIFEST)
    args = parser.parse_args()
    with args.manifest.open() as stream:
        rows = list(csv.DictReader(stream))
    with MANIFEST.open() as stream:
        expected = list(csv.DictReader(stream))
    if rows != expected or len(rows) != 40:
        raise ValueError('Manifest differs from the published 40-file scooter snapshot')
    errors = []
    for row in rows:
        path = args.root / row['path']
        if not path.is_file():
            errors.append(f'Missing: {row["path"]}')
        elif path.stat().st_size != int(row['bytes']):
            errors.append(f'Size mismatch: {row["path"]}')
        else:
            with path.open('rb') as stream:
                actual = hashlib.file_digest(stream, 'sha256').hexdigest()
            if actual != row['sha256']:
                errors.append(f'SHA-256 mismatch: {row["path"]}')
    for error in errors:
        print(error)
    if errors:
        return 2
    print(f'PASS: {len(rows)} original scooter inputs; {sum(int(r["bytes"]) for r in rows):,} bytes; all SHA-256 match')
    print('Torino/GTT excluded: this raw-input preflight does not validate downstream external dependencies.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
