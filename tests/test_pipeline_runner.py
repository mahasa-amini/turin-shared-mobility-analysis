"""Runner contracts exercised with tiny subprocesses, never research datasets."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runner', ROOT / 'scripts/run_pipeline.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class PipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stages = {
            'a': dict(workflow='scooter', scripts=['a.py'], requires=[], outputs=['generated.txt']),
            'b': dict(workflow='scooter', scripts=['b.py'], requires=['a'], outputs=[]),
            'f': dict(workflow='figures', scripts=['b.py'], requires=['a'], outputs=[]),
        }
        (self.root / 'a.py').write_text("from pathlib import Path\nPath('generated.txt').write_text('ok')\n")
        (self.root / 'b.py').write_text("from pathlib import Path\nprint(Path('generated.txt').read_text())\n")

    def test_order_deduplication_and_workflow_boundary(self):
        self.assertEqual(runner.select_stages(self.stages, 'scooter', ['b', 'a', 'a']), ['a', 'b'])
        with self.assertRaises(ValueError):
            runner.select_stages(self.stages, 'scooter', ['f'])

    def test_missing_inputs_size_and_hash(self):
        item = dict(stage='a', path='input.txt', bytes='2', sha256=hashlib.sha256(b'ok').hexdigest())
        self.assertIn('missing input', runner.preflight(self.root, self.stages, [item], ['a'])[0])
        (self.root / 'input.txt').write_text('wrong')
        self.assertIn('size mismatch', runner.preflight(self.root, self.stages, [item], ['a'])[0])
        (self.root / 'input.txt').write_text('no')
        self.assertIn('SHA-256 mismatch', runner.preflight(self.root, self.stages, [item], ['a'], True)[0])
        (self.root / 'input.txt').write_text('ok')
        self.assertEqual(runner.preflight(self.root, self.stages, [item], ['a'], True), [])

    def test_unscheduled_dependency_required_but_planned_deferred(self):
        self.assertIn('run a first', runner.preflight(self.root, self.stages, [], ['b'])[0])
        self.assertEqual(runner.preflight(self.root, self.stages, [], ['a', 'b']), [])
        (self.root / 'generated.txt').touch()
        self.assertTrue(runner.preflight(self.root, self.stages, [], ['b']))

    def test_success_logs_interpreter_and_cwd(self):
        logs = self.root / 'logs'
        self.assertEqual(runner.execute(self.root, self.stages, [], ['a', 'b'], logs), 0)
        report = json.loads((logs / 'run.json').read_text())
        self.assertEqual(report['status'], 'passed')
        self.assertEqual(report['commands'][0]['command'][0], sys.executable)
        self.assertEqual(report['cwd'], str(self.root))
        self.assertIn('ok', (logs / '02-b.log').read_text())

    def test_stop_on_failure(self):
        (self.root / 'a.py').write_text("print('expected failure')\nraise SystemExit(7)\n")
        logs = self.root / 'logs'
        self.assertEqual(runner.execute(self.root, self.stages, [], ['a', 'b'], logs), 7)
        report = json.loads((logs / 'run.json').read_text())
        self.assertEqual(len(report['commands']), 1)
        self.assertEqual(report['status'], 'failed')
        self.assertFalse((logs / '02-b.log').exists())

    def test_missing_produced_output_stops(self):
        (self.root / 'a.py').write_text('pass\n')
        logs = self.root / 'logs'
        self.assertEqual(runner.execute(self.root, self.stages, [], ['a', 'b'], logs), 1)
        self.assertEqual(json.loads((logs / 'run.json').read_text())['status'], 'outputs_missing')

    def test_stage_boundary_rechecks_dependencies(self):
        logs = self.root / 'logs'
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(runner.execute(self.root, self.stages, [], ['b'], logs), 2)
        self.assertEqual(json.loads((logs / 'run.json').read_text())['commands'], [])

    def test_dry_run_does_not_execute_or_write(self):
        with patch.object(runner, 'ROOT', self.root), patch.object(runner, 'load_config', return_value=(self.stages, [])), patch.object(runner, 'execute') as execute, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(runner.main(['scooter', '--dry-run']), 0)
            execute.assert_not_called()
        self.assertEqual(sorted(x.name for x in self.root.iterdir()), ['a.py', 'b.py'])

    def test_catalog_matches_validated_execution_order(self):
        stages, inputs = runner.load_config()
        records = json.loads((ROOT / 'docs/validation/figure-evidence/execution.json').read_text())
        for workflow, kind in [('scooter', 'prerequisite'), ('figures', 'figure')]:
            actual = [s for spec in stages.values() if spec['workflow'] == workflow for s in spec['scripts']]
            self.assertEqual(actual, [x['script'] for x in records if x['kind'] == kind])
        for name, spec in stages.items():
            for path in spec['scripts'] + spec['outputs']:
                self.assertFalse(Path(path).is_absolute())
                self.assertNotIn('..', Path(path).parts)
            self.assertTrue(all(dep in stages for dep in spec['requires']))
        self.assertEqual(len(inputs), 27)

    def test_manual_handoff_mismatch_fails_without_running_stage5(self):
        script = ROOT / 'scripts/check_commuting_handoff.py'
        spec = importlib.util.spec_from_file_location('handoff', script)
        handoff = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(handoff)
        (self.root / 'stage4_private_car.py').write_text('round_trip_total_eur = 19.1759\n')
        (self.root / 'stage4_private_active_modes.py').write_text('bike_cost_per_university_day_eur = .77499\nscooter_cost_per_university_day_eur = 1.66304\n')
        target = self.root / 'stage5_generalised_cost.py'
        target.write_text("private_car_cost = 19.18\nprivate_bike_cost = .775\nprivate_scooter_cost = 1.663\nraise RuntimeError('must not execute')\n")
        self.assertTrue(all(x['consistent'] for x in handoff.check(self.root)))
        target.write_text(target.read_text().replace('19.18', '20.00'))
        self.assertFalse(handoff.check(self.root)[0]['consistent'])
