"""Stage a private, split raw-to-results bundle; never upload or assign a license."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def sha256(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def verify_package(destination):
    """Stream archived payload bytes; never extract or print trip records."""
    with (destination / 'manifest.csv').open() as stream:
        records = list(csv.DictReader(stream))
    result = {}
    metadata = {'manifest.csv', 'SHA256SUMS', 'PROVENANCE.md'}
    for part in ('owner-scooter', 'external-review', 'runtime-config'):
        expected = {part + '/' + r['path']: r for r in records if r['part'] == part}
        with tarfile.open(destination / (part + '.tar.gz'), 'r:gz') as archive:
            files = [m for m in archive.getmembers() if m.isfile()]
            if len(files) != len(expected) + len(metadata) or {m.name for m in files} != set(expected) | metadata:
                raise RuntimeError(f'Unexpected archive contents: {part}')
            for member in files:
                with archive.extractfile(member) as stream:
                    h = hashlib.sha256()
                    for chunk in iter(lambda: stream.read(1024 * 1024), b''):
                        h.update(chunk)
                wanted = expected[member.name]['sha256'] if member.name in expected else sha256(destination / member.name)
                if h.hexdigest() != wanted:
                    raise RuntimeError(f'Archived checksum mismatch: {member.name}')
        result[part] = {'payload_files_verified': len(expected), 'metadata_files_verified': 3,
                        'unexpected_files': 0, 'all_checksums_match': True}
    (destination / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination', type=Path, required=True, help='New directory; keep outside Git')
    args = parser.parse_args()
    destination = args.destination.resolve()
    destination.mkdir(parents=True, exist_ok=False)
    records = []
    inputs = []
    for op, suffix in [('bird', '.csv'), ('lime', '.csv'), ('voi', '.xlsx')]:
        inputs.extend((p, 'owner-scooter', 'Owner-supplied operator export; owner publication authorization recorded in docs/data-and-reproduction.md; dataset license and acquisition date not recorded.')
                      for p in sorted((ROOT / 'data/raw' / op).glob('*' + suffix)))
    with (ROOT / 'config/input_manifest.csv').open() as stream:
        for row in csv.DictReader(stream):
            if row['path'].startswith('data/raw/external/'):
                inputs.append((ROOT / row['path'], 'external-review', row['provenance']))
            elif row['kind'] == 'tracked':
                inputs.append((ROOT / row['path'], 'runtime-config', row['provenance']))
    for source, part, provenance in inputs:
        relative = source.relative_to(ROOT)
        target = destination / part / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        checksum = sha256(source)
        if checksum != sha256(target):
            raise RuntimeError(f'Copy mismatch: {relative}')
        records.append({'part': part, 'path': str(relative), 'bytes': source.stat().st_size,
                        'sha256': checksum, 'provenance': provenance})
    with (destination / 'manifest.csv').open('w') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    (destination / 'SHA256SUMS').write_text(''.join(f"{r['sha256']}  {r['part']}/{r['path']}\n" for r in records))
    (destination / 'PROVENANCE.md').write_text('''# Private distribution staging — not published

This is a local staging copy, not a grant of public redistribution rights.
Owner publication authorization is recorded in docs/data-and-reproduction.md;
a dataset license is still undecided. owner-scooter contains 40 original operator exports; external-review contains
four Torino shapefile components and ten GTT GTFS tables; runtime-config contains
four tracked economic configuration/source registers. Overlay each part at the
repository root. Cleaned, interim, harmonized, row-level audits and results are
regenerated, not input dependencies. Use docs/validation/cleaning-reproduction.md
and docs/data-distribution.md in the source checkout for execution and release decisions.

GTT feed version 20260813 covers 2026-08-12 through 2027-01-31.
GTT current terms (checked 2026-10-14) require non-commercial use and attribution:
Data source: GTT S.p.A. – Gruppo Torinese Trasporti; https://www.gtt.to.it
https://www.gtt.to.it/gtt_gtfs_license.html
Applicability to this locally supplied snapshot must be established before release.
Torino source archive/version and applicable redistribution terms remain unverified.
Scooter exports contain precise endpoint/time records, persistent vehicle IDs,
and Voi rental IDs. No direct rider-contact columns appear in the expected schemas;
this is not anonymization certification. Decide access restrictions or an aggregate
public release after confirming release scope and privacy review. Do not place these bulk
files in ordinary Git. No dataset license is assigned by this package.
''')
    sizes = {}
    for part in ('owner-scooter', 'external-review', 'runtime-config'):
        with tarfile.open(destination / (part + '.tar.gz'), 'w:gz') as archive:
            archive.add(destination / part, arcname=part)
            for name in ('manifest.csv', 'SHA256SUMS', 'PROVENANCE.md'):
                archive.add(destination / name, arcname=name)
        subset = [r for r in records if r['part'] == part]
        sizes[part] = {'files': len(subset), 'payload_bytes': sum(r['bytes'] for r in subset),
                       'archive_bytes': (destination / (part + '.tar.gz')).stat().st_size,
                       'archive_sha256': sha256(destination / (part + '.tar.gz'))}
    sizes['total_payload_bytes'] = sum(r['bytes'] for r in records)
    sizes['local_staging_bytes'] = sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
    verify_package(destination)
    # Include the size report itself; repeat until its byte length stabilizes.
    for _ in range(3):
        (destination / 'sizes.json').write_text(json.dumps(sizes, indent=2) + '\n')
        sizes['local_staging_bytes'] = sum(p.stat().st_size for p in destination.rglob('*') if p.is_file())
    (destination / 'sizes.json').write_text(json.dumps(sizes, indent=2) + '\n')
    print(json.dumps(sizes, indent=2))


if __name__ == '__main__':
    main()
