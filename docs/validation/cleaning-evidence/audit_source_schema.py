"""Record source headers and route-placeholder counts without exporting trip rows."""
import ast
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
EVIDENCE = Path(__file__).resolve().parent


def main():
    result = {}
    for operator, entry, suffix in [('bird', 'clean_bird', '.csv'), ('lime', 'audit_lime', '.csv'),
                                    ('voi', 'audit_voi', '.xlsx')]:
        tree = ast.parse((ROOT / f'src/cleaning/{entry}.py').read_text())
        expected = next(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == 'EXPECTED_COLUMNS' for t in node.targets))
        for path in sorted((ROOT / 'data/raw' / operator).glob('*' + suffix)):
            header = pd.read_excel(path, nrows=0, engine='openpyxl') if suffix == '.xlsx' else pd.read_csv(path, nrows=0)
            columns = list(header.columns)
            normalized = [str(c).strip() for c in columns] if operator == 'voi' else columns
            record = {'raw_columns': columns, 'expected_columns': len(expected),
                      'missing_columns': sorted(set(expected) - set(normalized)),
                      'unexpected_columns': sorted(set(normalized) - set(expected))}
            assert not record['missing_columns'] and not record['unexpected_columns']
            if operator == 'bird':
                route = pd.read_csv(path, usecols=['PERCORSO'], keep_default_na=False)['PERCORSO']
                record.update({'rows': len(route), 'route_nonplaceholder_rows': int((~route.isin(['', 'N/A'])).sum())})
            result[str(path.relative_to(ROOT))] = record
    (EVIDENCE / 'source-column-checks.json').write_text(json.dumps(result, indent=2) + '\n')
    print(f'Checked headers in {len(result)} source files; no schema extras or omissions')


if __name__ == '__main__':
    main()
