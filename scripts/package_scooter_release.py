"""Build and verify a scooter-only release from the existing private staging copy."""
import argparse
import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'turin-scooter-inputs-2024-2025-v1.tar.gz'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staging', type=Path, default=ROOT / 'data/distribution-staging/2026-10-14')
    parser.add_argument('--destination', type=Path, required=True, help='New local directory, outside ordinary Git')
    args = parser.parse_args()
    evidence = ROOT / 'docs/validation/scooter-release-evidence'
    inspection = json.loads((evidence / 'column-inspection.json').read_text())
    if inspection['findings'] or not inspection['schema_matches']:
        raise ValueError('Inspection requires review before packaging')
    with (args.staging / 'manifest.csv').open() as stream:
        records = [r for r in csv.DictReader(stream) if r['part'] == 'owner-scooter']
    if len(records) != 40 or {r['path']: r['sha256'] for r in records} != {
            r['path']: r['sha256'] for r in inspection['files']}:
        raise ValueError('Inspection does not cover precisely these 40 input hashes')
    for row in records:
        path = args.staging / 'owner-scooter' / row['path']
        if path.stat().st_size != int(row['bytes']) or digest(path) != row['sha256']:
            raise ValueError(f'Staged input mismatch: {row["path"]}')
    args.destination.mkdir(parents=True, exist_ok=False)
    manifest = io.StringIO(newline='')
    writer = csv.DictWriter(manifest, fieldnames=list(records[0]), lineterminator='\n')
    writer.writeheader()
    writer.writerows(records)
    metadata = {
        'manifest.csv': manifest.getvalue().encode(),
        'SHA256SUMS': ''.join(f"{r['sha256']}  {r['path']}\n" for r in records).encode(),
        'README.md': (evidence / 'package-README.md').read_bytes(),
        'PROVENANCE.md': (evidence / 'package-PROVENANCE.md').read_bytes(),
    }
    archive = args.destination / NAME
    with tarfile.open(archive, 'w:gz') as tar:
        for row in records:
            tar.add(args.staging / 'owner-scooter' / row['path'], arcname=row['path'], recursive=False)
        for name, value in metadata.items():
            info = tarfile.TarInfo('scooter-dataset/' + name)
            info.size = len(value)
            info.mode = 0o644
            tar.addfile(info, io.BytesIO(value))
    with tempfile.TemporaryDirectory(prefix='scooter-release-integrity-') as temp:
        with tarfile.open(archive, 'r:gz') as tar:
            members = tar.getmembers()
            expected = {r['path'] for r in records} | {'scooter-dataset/' + n for n in metadata}
            if len(members) != 44 or {m.name for m in members} != expected or not all(m.isfile() for m in members):
                raise ValueError('Unexpected archive contents or member types')
            tar.extractall(temp, filter='data')
        for row in records:
            if digest(Path(temp) / row['path']) != row['sha256']:
                raise ValueError(f'Extracted checksum mismatch: {row["path"]}')
        for name, value in metadata.items():
            if (Path(temp) / 'scooter-dataset' / name).read_bytes() != value:
                raise ValueError(f'Extracted metadata mismatch: {name}')
    checksum = digest(archive)
    sums = args.destination / 'SHA256SUMS'
    sums.write_text(f'{checksum}  {NAME}\n')
    (evidence / 'manifest.csv').write_text(manifest.getvalue())
    result = {'archive': NAME, 'archive_bytes': archive.stat().st_size, 'archive_sha256': checksum,
              'checksum_asset_bytes': sums.stat().st_size, 'payload_files': 40,
              'payload_bytes': sum(int(r['bytes']) for r in records), 'metadata_files': 4,
              'all_extracted_hashes_match': True, 'unexpected_files': 0,
              'source_staging': 'data/distribution-staging/2026-10-14/owner-scooter',
              'excluded': ['Torino shapefile', 'GTT GTFS', 'generated records/results', 'runtime configuration (tracked in Git)']}
    (evidence / 'package-verification.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
