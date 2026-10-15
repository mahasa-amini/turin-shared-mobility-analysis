"""Data-independent checks for release input integrity failures."""
import contextlib
import csv
import hashlib
import importlib.util
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class RawInputPreflight(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'manifest.csv'
        rows = []
        for i in range(40):
            path = self.root / f'data/raw/SYNTHETIC-{i}.csv'
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(b'SYNTHETIC\n')
            rows.append({'path': str(path.relative_to(self.root)), 'bytes': 10,
                         'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
        with self.manifest.open('w') as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        spec = importlib.util.spec_from_file_location('raw_preflight', ROOT / 'scripts/check_raw_inputs.py')
        self.module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.module)
        self.module.MANIFEST = self.manifest

    def run_check(self, *extra):
        with patch.object(sys, 'argv', ['check', '--root', str(self.root), *extra]), contextlib.redirect_stdout(io.StringIO()):
            return self.module.main()

    def test_valid_inputs(self):
        self.assertEqual(self.run_check(), 0)

    def test_missing_input(self):
        (self.root / 'data/raw/SYNTHETIC-0.csv').unlink()
        self.assertEqual(self.run_check(), 2)

    def test_same_size_corruption(self):
        (self.root / 'data/raw/SYNTHETIC-0.csv').write_bytes(b'CORRUPTED\n')
        self.assertEqual(self.run_check(), 2)

    def test_changed_manifest_is_rejected(self):
        changed = self.root / 'changed.csv'
        changed.write_text(self.manifest.read_text().replace('SYNTHETIC-0', 'SYNTHETIC-X'))
        with self.assertRaisesRegex(ValueError, 'Manifest differs'):
            self.run_check('--manifest', str(changed))


if __name__ == '__main__':
    unittest.main()
