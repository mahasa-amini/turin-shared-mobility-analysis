"""Inspect original scooter export schemas and cells without emitting trip values."""
import argparse
import ast
import csv
import hashlib
import json
from pathlib import Path
import re

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = {
    'email': r'(?i)[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}',
    'credential': (
        r'(?i)(?:-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY|'
        r'\b(?:password|passwd|api[_-]?key|client[_-]?secret|access[_-]?token)\s*[:=]|'
        r'\bBearer\s+[A-Za-z0-9._-]{12,}|'
        r'\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|AKIA[A-Z0-9]{16})\b|'
        r'https?://[^\s/:]+:[^\s/@]+@)'
    ),
    'phone_label': r'(?i)\b(?:tel(?:ephone)?|phone|cellulare|telefono)\s*[:=]\s*\+?[0-9 ()-]{7,}',
}
SENSITIVE_HEADER = re.compile(
    r'(?i)(?:email|e-mail|rider|customer|utente|cliente|cognome|nome|phone|telefono|'
    r'password|secret|token|credential|indirizzo|address|birth|nascita|fiscale|iban|card)')


def expected_columns(operator):
    script = {'bird': 'clean_bird.py', 'lime': 'audit_lime.py', 'voi': 'audit_voi.py'}[operator]
    tree = ast.parse((ROOT / 'src/cleaning' / script).read_text())
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == 'EXPECTED_COLUMNS' for target in node.targets):
            return ast.literal_eval(node.value)
    raise ValueError(f'No expected schema for {operator}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--staging', type=Path, default=ROOT / 'data/distribution-staging/2026-10-14')
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    with (args.staging / 'manifest.csv').open() as stream:
        records = [row for row in csv.DictReader(stream) if row['part'] == 'owner-scooter']
    report = {
        'scope': 'All 40 staged original scooter exports; all CSV cells and all workbook sheets inspected without emitting values.',
        'files': [], 'findings': [], 'schema_matches': True, 'raw_rows': 0, 'payload_bytes': 0,
    }
    for row in records:
        path = args.staging / 'owner-scooter' / row['path']
        operator = path.parent.name
        with path.open('rb') as stream:
            checksum = hashlib.file_digest(stream, 'sha256').hexdigest()
        if checksum != row['sha256'] or path.stat().st_size != int(row['bytes']):
            raise ValueError(f'Staged input mismatch: {row["path"]}')
        expected = expected_columns(operator)
        frames = (pd.read_excel(path, sheet_name=None, dtype=str, keep_default_na=False)
                  if operator == 'voi' else {'CSV': pd.read_csv(path, dtype=str, keep_default_na=False)})
        info = {'path': row['path'], 'sha256': row['sha256'], 'sheets': []}
        for sheet, frame in frames.items():
            columns = [str(column).strip() for column in frame.columns]
            schema_ok = columns == expected
            report['schema_matches'] &= schema_ok
            location = {'path': row['path'], 'sheet': sheet}
            if not schema_ok:
                report['findings'].append({**location, 'category': 'unexpected_schema', 'fields': columns})
            suspicious = [column for column in columns if SENSITIVE_HEADER.search(column)]
            if suspicious:
                report['findings'].append({**location, 'category': 'direct_identifier_or_credential_header', 'fields': suspicious})
            for column in frame:
                for category, pattern in PATTERNS.items():
                    count = int(frame[column].astype('string').str.contains(pattern, regex=True, na=False).sum())
                    if count:
                        report['findings'].append({**location, 'category': category,
                                                   'field': str(column), 'matching_cells': count})
            counts = {}
            if operator == 'bird':
                counts['nonplaceholder_route_cells'] = int((~frame['PERCORSO'].isin(['', 'N/A'])).sum())
                if counts['nonplaceholder_route_cells']:
                    report['findings'].append({**location, 'category': 'route_text_needs_review', 'field': 'PERCORSO'})
            info['sheets'].append({'sheet': sheet, 'rows': len(frame), 'columns': columns, **counts})
            report['raw_rows'] += len(frame)
        report['files'].append(info)
        report['payload_bytes'] += int(row['bytes'])
        print(f'Inspected {operator}: file {len(report["files"])}/40', flush=True)
    report['limitations'] = (
        'No direct rider/contact or credential fields or recognized email/credential/phone-label patterns found if findings is empty. '
        'This is a schema and heuristic full-cell scan, not anonymization certification or proof that unlabelled names/phone numbers cannot occur. '
        'Persistent vehicle IDs, Voi rental IDs, precise timestamps/endpoints and battery/reservation fields remain unchanged.')
    args.report.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({key: report[key] for key in ('raw_rows', 'payload_bytes', 'schema_matches', 'findings')}, indent=2))
    if len(records) != 40 or report['findings']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
